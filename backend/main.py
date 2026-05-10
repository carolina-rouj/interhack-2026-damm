import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.data.loader import load_zona, DATA_DIR
from backend.models.zona import TipoMatriz

import json

app = FastAPI(title="Damm Smart Truck API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory zone cache (enough for hackathon demo)
_zonas: dict = {}


def _get_zona(zona_id: str):
    if zona_id not in _zonas:
        try:
            _zonas[zona_id] = load_zona(zona_id)
        except KeyError:
            raise HTTPException(404, f"Zona {zona_id!r} not found. Check /api/zona/list.")
    return _zonas[zona_id]


@app.get("/api/zona/list")
def list_zonas():
    """List all available zone IDs from the checked-in data."""
    with open(DATA_DIR / "zona.json", encoding="utf-8-sig") as f:
        zones = json.load(f)
    return {"zonas": [z["zona_id"] for z in zones]}


@app.get("/api/zona/{zona_id}")
def get_zona(zona_id: str):
    """Load a real zone by ID and return its stores and demand summary."""
    data = _get_zona(zona_id)
    zona = data["zona"]
    return {
        "zona_id": zona.zona_id,
        "nombre": zona.nombre,
        "num_tiendas": zona.num_tiendas,
        "demanda_total_cajas": zona.demanda_total_cajas,
        "demanda_total_peso_kg": zona.demanda_total_peso,
        "tiendas": [t.to_dict() for t in zona.tiendas],
    }


class ClusterRequest(BaseModel):
    zona_id: str
    cajas_por_palet: int = 60
    distancia_max: float | None = None
    usar_google: bool = False


@app.post("/api/cluster")
def cluster(req: ClusterRequest):
    """
    Group the stores in a zone into delivery stops (one pallet per stop).

    Set usar_google=true to use real driving distances via Google Maps
    (requires GOOGLE_MAPS_API_KEY in backend/distance/.env).
    Falls back to Euclidean distance automatically.
    distancia_max is in cost units (1–10) when usar_google=true, degrees otherwise.
    """
    data = _get_zona(req.zona_id)
    zona = data["zona"]
    zona._matriz = None  # Rebuild matrix on every call so params take effect

    if req.usar_google:
        tipo = zona.cargar_mejor_matriz()
    else:
        zona.generar_matriz(TipoMatriz.EUCLIDEA)
        tipo = TipoMatriz.EUCLIDEA

    paradas = zona.agrupar_tiendas(
        cajas_por_palet=req.cajas_por_palet,
        distancia_max=req.distancia_max,
    )

    return {
        "zona_id": req.zona_id,
        "matriz_tipo": tipo.value,
        "cajas_por_palet": req.cajas_por_palet,
        "num_paradas": len(paradas),
        "paradas": [
            {
                "parada_id": p.parada_id,
                "orden": p.orden,
                "representante_id": p.representante_id,
                "cajas_total": sum(t.num_cajas_total for t in p.tiendas),
                "num_tiendas": p.num_tiendas,
                "tiendas": [
                    {
                        "tienda_id": t.tienda_id,
                        "nombre": t.nombre,
                        "lat": t.x,
                        "lon": t.y,
                        "cajas": t.num_cajas_total,
                        "es_representante": t.tienda_id == p.representante_id,
                    }
                    for t in p.tiendas
                ],
            }
            for p in paradas
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


class SolveRequest(BaseModel):
    zona_id: str
    cajas_por_palet: int = 60
    distancia_max: float | None = None
    usar_google: bool = False
    output_dir: str = "output/routes"


@app.post("/api/solve")
def solve(req: SolveRequest):
    """
    Run the full pipeline (load → zone → route → palletize) and write
    one JSON file per route to *output_dir*.  Returns the formatted routes.
    """
    from backend.pipeline import export_routes_json

    results = export_routes_json(
        req.zona_id,
        output_dir=req.output_dir,
        usar_google=req.usar_google,
        cajas_por_palet=req.cajas_por_palet,
        distancia_max=req.distancia_max,
    )
    return {
        "zona_id": req.zona_id,
        "num_rutas": len(results),
        "routes": [
            {"file": str(r["path"]), "route": r["route"]}
            for r in results
        ],
    }


# ── terminal entry point ──────────────────────────────────────────────────────
# Run with:  python3 backend/main.py [zona_id] [--output DIR] [--google]

if __name__ == "__main__":
    from backend.pipeline import export_routes_json

    import argparse

    parser = argparse.ArgumentParser(
        description="Damm Smart Truck — solve a zone and export route JSONs"
    )
    parser.add_argument(
        "zona_id",
        nargs="?",
        default="granollers-center-01",
        help="Zone ID (default: granollers-center-01)",
    )
    parser.add_argument(
        "--output", default="output/routes", metavar="DIR",
        help="Output directory for route JSON files (default: output/routes)",
    )
    parser.add_argument(
        "--google", action="store_true",
        help="Use Google Maps Distance Matrix (requires API key)",
    )
    args = parser.parse_args()

    print(f"Zone   : {args.zona_id}")
    print(f"Output : {args.output}")
    print(f"Google : {'yes' if args.google else 'no (Euclidean fallback)'}")
    print()

    results = export_routes_json(
        args.zona_id,
        output_dir=args.output,
        usar_google=args.google,
    )

    print(f"{len(results)} route(s) written:")
    sep = "─" * 56
    print(sep)
    for r in results:
        route = r["route"]
        path = r["path"]
        num_stops = len(route["paradas"])
        print(
            f"  {path.name}"
            f"  |  {route['tipo_camion']}"
            f"  |  {route['num_palets']} palets"
            f"  |  {num_stops} paradas"
        )
    print(sep)
