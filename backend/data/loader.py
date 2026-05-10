"""
Load real Zona / Tienda / Pedido objects from the checked-in JSON files.

Usage
-----
    from backend.data.loader import load_zona
    data = load_zona("granollers-center-01")
    zona     = data["zona"]       # Zona with Tiendas attached
    tiendas  = data["tiendas"]    # {tienda_id: Tienda}
    pedidos  = data["pedidos"]    # {tienda_id: [Pedido, ...]}
    skus     = data["skus"]       # {sku: Product}
"""
from __future__ import annotations
import json
from pathlib import Path
import sys


# Allow direct execution with `python3 backend/data/generate_pedidos.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.product import Product, OrderLine
from backend.models.pedido import Pedido
from backend.models.tienda import Tienda
from backend.models.zona import Zona

DATA_DIR = Path(__file__).parent


def load_zona(zona_id: str) -> dict:
    """
    Hydrate one zone from the four JSON files in backend/data/.

    Only tiendas that appear in zona.json AND have at least one matching
    pedido are attached to the returned Zona (so the matrix stays non-trivial
    and solver input is always populated).
    """
    with open(DATA_DIR / "tienda.json", encoding="utf-8-sig") as f:
        raw_tiendas: dict[str, dict] = {t["tienda_id"]: t for t in json.load(f)}

    with open(DATA_DIR / "producto.json", encoding="utf-8-sig") as f:
        skus: dict[str, Product] = {
            p["sku"]: Product(
                sku=p["sku"],
                name=p["name"],
                is_returnable=p["is_returnable"],
                weight_kg_per_box=p["weight_kg_per_box"],
                tipo=p.get("tipo", "generico"),
                tamano=p.get("tamano", 0.0),
            )
            for p in json.load(f)
        }

    with open(DATA_DIR / "pedido.json", encoding="utf-8-sig") as f:
        raw_pedidos: list[dict] = json.load(f)

    with open(DATA_DIR / "zona.json", encoding="utf-8-sig") as f:
        raw_zonas: dict[str, dict] = {z["zona_id"]: z for z in json.load(f)}

    if zona_id not in raw_zonas:
        raise KeyError(f"Zona {zona_id!r} not found in zona.json")

    zona_raw = raw_zonas[zona_id]
    zona = Zona(zona_id=zona_id, nombre=zona_raw["nombre"])

    # Build Tienda objects for IDs that exist in tienda.json
    tiendas: dict[str, Tienda] = {}
    for ref in zona_raw["tiendas"]:
        tid = ref["tienda_id"]
        if tid not in raw_tiendas:
            continue
        raw = raw_tiendas[tid]
        tiendas[tid] = Tienda(
            tienda_id=tid,
            nombre=raw["nombre"],
            x=raw["lat"],
            y=raw["lon"],
        )

    # Attach Pedidos
    pedidos: dict[str, list[Pedido]] = {}
    for raw in raw_pedidos:
        tid = raw["tienda_id"]
        if tid not in tiendas:
            continue
        pedido = Pedido.from_dict(raw)
        tiendas[tid].añadir_pedido(pedido)
        pedidos.setdefault(tid, []).append(pedido)

    # Add to Zona only stores that have at least one pedido
    for t in tiendas.values():
        if t.pedidos:
            zona.añadir_tienda(t)

    return {"zona": zona, "tiendas": tiendas, "pedidos": pedidos, "skus": skus}
