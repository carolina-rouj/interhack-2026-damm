import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.data.synthetic_generator import generate_scenario
from backend.models.zona import TipoMatriz

app = FastAPI(title="Damm Smart Truck API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory scenario store (enough for hackathon demo)
_scenarios: dict = {}


@app.get("/api/scenario/generate")
def generate(seed: int = 42, n_tiendas: int = 16):
    """Generate a fresh synthetic delivery scenario."""
    data = generate_scenario(seed=seed, n_tiendas=n_tiendas)
    scenario_id = f"scenario-{seed}-{n_tiendas}"
    _scenarios[scenario_id] = data
    zona = data["zona"]
    return {
        "scenario_id": scenario_id,
        "depot": {"lat": data["depot_lat"], "lon": data["depot_lon"]},
        "zona": {
            "zona_id": zona.zona_id,
            "nombre": zona.nombre,
            "num_tiendas": zona.num_tiendas,
            "demanda_total_cajas": zona.demanda_total_cajas,
            "demanda_total_peso_kg": zona.demanda_total_peso,
        },
        "tiendas": [t.to_dict() for t in zona.tiendas],
    }


@app.get("/api/scenario/{scenario_id}")
def get_scenario(scenario_id: str):
    if scenario_id not in _scenarios:
        raise HTTPException(404, "Scenario not found. Generate one first via /api/scenario/generate")
    data = _scenarios[scenario_id]
    zona = data["zona"]
    return {
        "scenario_id": scenario_id,
        "depot": {"lat": data["depot_lat"], "lon": data["depot_lon"]},
        "zona": {
            "zona_id": zona.zona_id,
            "nombre": zona.nombre,
            "num_tiendas": zona.num_tiendas,
            "demanda_total_cajas": zona.demanda_total_cajas,
        },
        "tiendas": [t.to_dict() for t in zona.tiendas],
    }


class ClusterRequest(BaseModel):
    scenario_id: str
    cajas_por_palet: int = 60
    distancia_max: float | None = None
    usar_google: bool = False


@app.post("/api/cluster")
def cluster(req: ClusterRequest):
    """
    Group the stores in a scenario into delivery stops (one pallet per stop).

    Set usar_google=true to load real driving distances via Google Maps
    (requires GOOGLE_MAPS_API_KEY in backend/distance/.env).
    Falls back to Euclidean distance automatically.
    """
    if req.scenario_id not in _scenarios:
        raise HTTPException(404, "Scenario not found. Generate one first via /api/scenario/generate")

    zona = _scenarios[req.scenario_id]["zona"]
    # Always rebuild the matrix so repeated calls with different params work
    zona._matriz = None

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
        "scenario_id": req.scenario_id,
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


# ── clustering probe ──────────────────────────────────────────────────────────
# Run with:  python3 backend/main.py

if __name__ == "__main__":
    from backend.models.tienda import Tienda
    from backend.models.pedido import Pedido
    from backend.models.product import Product, OrderLine
    from backend.models.zona import Zona, TipoMatriz

    ESTRELLA = Product(sku="ED33", name="Estrella Damm 33cl", is_returnable=False, weight_kg_per_box=0.38)
    VOLL     = Product(sku="VD33", name="Voll-Damm 33cl",    is_returnable=False, weight_kg_per_box=0.40)

    def _t(tid, name, lat, lng, ed, vd=0):
        t = Tienda(tienda_id=tid, nombre=name, x=lat, y=lng)
        lineas = [OrderLine(product=ESTRELLA, quantity_boxes=ed)]
        if vd:
            lineas.append(OrderLine(product=VOLL, quantity_boxes=vd))
        t.añadir_pedido(Pedido(pedido_id=f"p-{tid}", tienda_id=tid, lineas=lineas))
        return t

    # Three bars clustered in Poblenou + one restaurant in Barceloneta (far)
    stores = [
        _t("T01", "Bar Biciclot",   41.3975, 2.1885, ed=15),
        _t("T02", "Bar Balboa",     41.3978, 2.1890, ed=18, vd=2),
        _t("T03", "Bar Ke33",       41.3972, 2.1888, ed=12, vd=6),
        _t("T04", "La Mar Salada",  41.3764, 2.1873, ed=25, vd=5),
    ]

    zona = Zona(zona_id="BCN-DEMO", nombre="Barcelona Demo")
    for s in stores:
        zona.añadir_tienda(s)

    print("\nCargando matriz de distancias…")
    tipo = zona.cargar_mejor_matriz()

    unit = "metros (Google Maps)" if tipo == TipoMatriz.GOOGLE else "grados Euclídeos (fallback sin API)"
    print(f"  → {tipo.value}  |  unidades: {unit}\n")

    PALET = 60
    paradas = zona.agrupar_tiendas(cajas_por_palet=PALET)

    sep = "─" * 58
    print(f"Zona : {zona.nombre}  ({zona.num_tiendas} tiendas, {zona.demanda_total_cajas} cajas total)")
    print(f"Palé : {PALET} cajas/palé")
    print(f"Resultado: {len(paradas)} parada(s)\n{sep}")

    for p in paradas:
        total = sum(t.num_cajas_total for t in p.tiendas)
        print(f"\nParada {p.orden + 1}  [{p.parada_id}]")
        print(f"  Representante : {p.representante_id}")
        print(f"  Cajas totales : {total}/{PALET}")
        print(f"  Tiendas ({p.num_tiendas}):")
        for t in p.tiendas:
            tag = "  ← medoid" if t.tienda_id == p.representante_id else ""
            print(f"    • {t.nombre:<22} {t.num_cajas_total:3d} cajas  ({t.x:.4f}, {t.y:.4f}){tag}")

    print(f"\n{sep}")

    # Show the raw distance sub-matrix for the first cluster
    first = paradas[0]
    if first.num_tiendas > 1:
        m = zona.matriz
        ids = [t.tienda_id for t in zona.tiendas]
        print(f"\nSub-matriz de distancias — Parada 1 ({unit.split()[0]}):")
        cluster_ids = [t.tienda_id for t in first.tiendas]
        ci = [ids.index(tid) for tid in cluster_ids]
        header = "         " + "".join(f"{tid:>12}" for tid in cluster_ids)
        print(header)
        for i in ci:
            row = f"  {ids[i]:<6} " + "".join(
                f"{'—':>12}" if i == j else f"{m[i][j]:>12.5g}"
                for j in ci
            )
            print(row)
    print()
