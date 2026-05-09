"""
Generate producto.json and pedido.json from tienda.json.

Usage (from repo root):
    python -m backend.data.generate_pedidos
    python -m backend.data.generate_pedidos --seed 42 --n 50
    python -m backend.data.generate_pedidos --n 100 --out-dir backend/data
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from backend.models.product import OrderLine, Product
from backend.models.pedido import Pedido

DATA_DIR = Path(__file__).parent

# ── Damm product catalogue ────────────────────────────────────────────────────

PRODUCTS: list[Product] = [
    Product("ED33",  "Estrella Damm 33cl x24",  False,  9.12, tipo="cerveza",       tamano=7.92),
    Product("ED50",  "Estrella Damm 50cl x12",  False,  6.60, tipo="cerveza",       tamano=6.00),
    Product("VD33",  "Voll-Damm 33cl x24",      False,  9.40, tipo="cerveza",       tamano=7.92),
    Product("BAR20", "Barril Damm 20L",          True,  20.00, tipo="barril",        tamano=20.00),
    Product("FR33",  "Free Damm 33cl x24",       False,  8.64, tipo="cerveza_sinal", tamano=7.92),
    Product("LD33",  "Lemon Damm 33cl x24",      False,  9.00, tipo="refresco",      tamano=7.92),
]

_SKU_MAP: dict[str, Product] = {p.sku: p for p in PRODUCTS}

# ── Venue archetypes ──────────────────────────────────────────────────────────

_ARCHETYPES: dict[str, dict] = {
    "bar": {
        "boxes":           (24, 72),
        "products":        ["ED33", "ED50", "BAR20"],
        "returnable_prob": 0.40,
        "max_envases":     12,
    },
    "restaurante": {
        "boxes":           (60, 150),
        "products":        ["ED33", "VD33", "BAR20", "FR33"],
        "returnable_prob": 0.50,
        "max_envases":     24,
    },
    "supermercado": {
        "boxes":           (90, 240),
        "products":        ["ED33", "ED50", "VD33", "LD33"],
        "returnable_prob": 0.10,
        "max_envases":     6,
    },
    "hotel": {
        "boxes":           (60, 120),
        "products":        ["ED33", "VD33", "BAR20", "FR33"],
        "returnable_prob": 0.30,
        "max_envases":     18,
    },
    "kiosco": {
        "boxes":           (12, 48),
        "products":        ["ED33", "LD33"],
        "returnable_prob": 0.10,
        "max_envases":     6,
    },
}

_HOTEL_WORDS = {"hotel", "hostal", "pension", "hostes"}
_SUPER_WORDS = {"supermercat", "mercadona", "caprabo", "bonpreu", "carrefour", "lidl", "aldi", "corte"}
_REST_WORDS  = {"restaurant", "restaurante", "pizzeria", "braseria", "grill", "tapes", "tapas"}
_KIOSK_WORDS = {"kiosc", "kiosco", "kiosko"}


def _infer_archetype(nombre: str) -> str:
    n = nombre.lower()
    if any(w in n for w in _HOTEL_WORDS):
        return "hotel"
    if any(w in n for w in _SUPER_WORDS):
        return "supermercado"
    if any(w in n for w in _REST_WORDS):
        return "restaurante"
    if any(w in n for w in _KIOSK_WORDS):
        return "kiosco"
    return "bar"


# ── Core generator ────────────────────────────────────────────────────────────

def generate(
    seed: int = 42,
    n: int = 50,
    out_dir: Path = DATA_DIR,
) -> list[dict]:
    """
    Generate producto.json and pedido.json.

    Parameters
    ----------
    seed:    RNG seed for reproducibility.
    n:       Number of tiendas to include (sampled from tienda.json).
    out_dir: Directory where the JSON files are written.

    Returns
    -------
    List of serialised Pedido dicts (same content as pedido.json).
    """
    rng = random.Random(seed)

    tienda_path = DATA_DIR / "tienda.json"
    tiendas: list[dict] = json.loads(tienda_path.read_text(encoding="utf-8"))
    selected = rng.sample(tiendas, min(n, len(tiendas)))

    pedidos: list[dict] = []
    for i, tienda in enumerate(selected):
        arch = _ARCHETYPES[_infer_archetype(tienda["nombre"])]

        # Total boxes for this order, rounded to nearest pallet row (6 boxes)
        target_boxes = rng.randint(*arch["boxes"])
        target_boxes = max(6, (target_boxes // 6) * 6)

        chosen_skus = rng.sample(
            arch["products"],
            rng.randint(1, min(3, len(arch["products"]))),
        )
        chosen_products = [_SKU_MAP[sku] for sku in chosen_skus]

        lineas: list[OrderLine] = []
        remaining = target_boxes
        for j, prod in enumerate(chosen_products):
            if j == len(chosen_products) - 1:
                qty = max(6, remaining)
            else:
                qty = max(6, rng.randint(remaining // 3, remaining // 2))
                remaining -= qty
            qty = max(6, (qty // 6) * 6)
            lineas.append(OrderLine(product=prod, quantity_boxes=qty))

        es_retornable = rng.random() < arch["returnable_prob"]
        num_envases = rng.randint(0, arch["max_envases"]) if es_retornable else 0

        pedido = Pedido(
            pedido_id=f"PED-{i + 1:04d}",
            tienda_id=tienda["tienda_id"],
            lineas=lineas,
            es_retornable=es_retornable,
            num_envases_recogida=num_envases,
        )
        pedidos.append(pedido.to_dict())

    out_dir = Path(out_dir)

    producto_path = out_dir / "producto.json"
    producto_path.write_text(
        json.dumps([p.to_dict() for p in PRODUCTS], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(PRODUCTS)} products → {producto_path}")

    pedido_path = out_dir / "pedido.json"
    pedido_path.write_text(
        json.dumps(pedidos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(pedidos)} pedidos → {pedido_path}")

    return pedidos


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate pedido.json and producto.json")
    parser.add_argument("--seed",    type=int,  default=42,       help="RNG seed (default: 42)")
    parser.add_argument("--n",       type=int,  default=50,       help="Number of tiendas (default: 50)")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR, help="Output directory")
    args = parser.parse_args()

    generate(seed=args.seed, n=args.n, out_dir=args.out_dir)
