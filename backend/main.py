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


# ── terminal probe ────────────────────────────────────────────────────────────
# Run with:  python3 backend/main.py

if __name__ == "__main__":
    from backend.models.zona import TipoMatriz

    ZONA_ID = "granollers-center-01"
    data = load_zona(ZONA_ID)
    zona = data["zona"]

    print(f"\nZona : {zona.nombre}  ({zona.num_tiendas} tiendas, {zona.demanda_total_cajas} cajas)")
    print("Cargando matriz de distancias…")
    tipo = zona.cargar_mejor_matriz()

    unit = "coste 1-10 (Google Maps)" if tipo == TipoMatriz.GOOGLE else "grados Euclídeos (fallback)"
    print(f"  → {tipo.value}  |  unidades: {unit}\n")

    PALET = 60
    paradas = zona.agrupar_tiendas(cajas_por_palet=PALET)

    sep = "─" * 58
    print(f"Resultado: {len(paradas)} parada(s)\n{sep}")
    for p in paradas:
        total = sum(t.num_cajas_total for t in p.tiendas)
        print(f"\nParada {p.orden + 1}  [{p.parada_id}]  {total}/{PALET} cajas")
        for t in p.tiendas:
            tag = "  ← medoid" if t.tienda_id == p.representante_id else ""
            print(f"    • {t.nombre:<30} {t.num_cajas_total:3d} cajas{tag}")
    print(f"\n{sep}\n")
