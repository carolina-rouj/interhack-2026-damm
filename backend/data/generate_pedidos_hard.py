"""
Generate harder pedido.json, producto.json, and tienda.json for difficulty=hard.

Differences from normal:
  - ALL tiendas in the dataset (no sampling cap)
  - ~2x box quantities per order
  - Higher returnable probability and more envases
  - More SKUs per order (minimum 2 product lines)
  - Tight 4-hour delivery windows (vs open 0:00–23:59 in normal)

Writes to backend/data/hard/ (created automatically).

Usage (from repo root):
    python -m backend.data.generate_pedidos_hard
    python -m backend.data.generate_pedidos_hard --seed 99
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.product import OrderLine, Product
from backend.models.pedido import Pedido

DATA_DIR = Path(__file__).parent
HARD_DIR = DATA_DIR / "hard"

# ── Same product catalogue ─────────────────────────────────────────────────────

PRODUCTS: list[Product] = [
    Product("ED33",  "Estrella Damm 33cl x24",  False,  9.12, tipo="cerveza",       tamano=7.92),
    Product("ED50",  "Estrella Damm 50cl x12",  False,  6.60, tipo="cerveza",       tamano=6.00),
    Product("VD33",  "Voll-Damm 33cl x24",      False,  9.40, tipo="cerveza",       tamano=7.92),
    Product("BAR20", "Barril Damm 20L",          True,  20.00, tipo="barril",        tamano=20.00),
    Product("FR33",  "Free Damm 33cl x24",       False,  8.64, tipo="cerveza_sinal", tamano=7.92),
    Product("LD33",  "Lemon Damm 33cl x24",      False,  9.00, tipo="refresco",      tamano=7.92),
]

_SKU_MAP: dict[str, Product] = {p.sku: p for p in PRODUCTS}

# ── Hard archetypes — ~2x quantities, higher returnables ──────────────────────

_HARD_ARCHETYPES: dict[str, dict] = {
    "bar": {
        "boxes":           (48, 144),
        "products":        ["ED33", "ED50", "BAR20"],
        "returnable_prob": 0.70,
        "max_envases":     24,
        "min_skus":        2,
    },
    "restaurante": {
        "boxes":           (120, 300),
        "products":        ["ED33", "VD33", "BAR20", "FR33"],
        "returnable_prob": 0.80,
        "max_envases":     48,
        "min_skus":        2,
    },
    "supermercado": {
        "boxes":           (180, 480),
        "products":        ["ED33", "ED50", "VD33", "LD33"],
        "returnable_prob": 0.30,
        "max_envases":     12,
        "min_skus":        3,
    },
    "hotel": {
        "boxes":           (120, 240),
        "products":        ["ED33", "VD33", "BAR20", "FR33"],
        "returnable_prob": 0.60,
        "max_envases":     36,
        "min_skus":        2,
    },
    "kiosco": {
        "boxes":           (24, 96),
        "products":        ["ED33", "LD33"],
        "returnable_prob": 0.25,
        "max_envases":     12,
        "min_skus":        1,
    },
}

# Tight 4-hour delivery windows (open_min, close_min)
_TIME_WINDOWS: list[tuple[int, int]] = [
    (480, 720),    # 08:00 – 12:00  early morning
    (540, 780),    # 09:00 – 13:00  late morning
    (600, 840),    # 10:00 – 14:00  midday
    (660, 900),    # 11:00 – 15:00  noon
    (720, 960),    # 12:00 – 16:00  afternoon
    (780, 1020),   # 13:00 – 17:00  early afternoon
    (840, 1080),   # 14:00 – 18:00  late afternoon
    (900, 1140),   # 15:00 – 19:00  evening
]

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


def _minutes_to_hms(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}:00"


# ── Hard generator ─────────────────────────────────────────────────────────────

def generate_hard(
    seed: int = 99,
    out_dir: Path = HARD_DIR,
) -> list[dict]:
    """
    Generate hard-difficulty pedido.json, producto.json, and tienda.json.

    Uses ALL tiendas (no n cap), doubles box quantities, increases returnables,
    and assigns tight 4-hour delivery windows to every store.
    """
    rng = random.Random(seed)

    tienda_path = DATA_DIR / "tienda.json"
    tiendas: list[dict] = json.loads(tienda_path.read_text(encoding="utf-8-sig"))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pedidos: list[dict] = []
    hard_tiendas: list[dict] = []

    for i, tienda in enumerate(tiendas):
        arch = _HARD_ARCHETYPES[_infer_archetype(tienda["nombre"])]

        # Assign a random tight 4-hour window
        win_open, win_close = rng.choice(_TIME_WINDOWS)

        # Record override tienda entry with tight window
        hard_tiendas.append({
            **tienda,
            "horario_inicio": _minutes_to_hms(win_open),
            "horario_fin":    _minutes_to_hms(win_close),
        })

        # Big order
        target_boxes = rng.randint(*arch["boxes"])
        target_boxes = max(6, (target_boxes // 6) * 6)

        min_skus = arch["min_skus"]
        max_skus = min(len(arch["products"]), max(min_skus, 4))
        n_skus = rng.randint(min_skus, max_skus)
        chosen_skus = rng.sample(arch["products"], n_skus)
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
        num_envases = rng.randint(1, arch["max_envases"]) if es_retornable else 0

        pedido = Pedido(
            pedido_id=f"PED-{i + 1:04d}",
            tienda_id=tienda["tienda_id"],
            lineas=lineas,
            es_retornable=es_retornable,
            num_envases_recogida=num_envases,
        )
        pedidos.append(pedido.to_dict())

    # Write producto.json
    producto_path = out_dir / "producto.json"
    producto_path.write_text(
        json.dumps([p.to_dict() for p in PRODUCTS], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(PRODUCTS)} products → {producto_path}")

    # Write pedido.json
    pedido_path = out_dir / "pedido.json"
    pedido_path.write_text(
        json.dumps(pedidos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(pedidos)} pedidos → {pedido_path}")

    # Write tienda.json with tight windows
    tienda_out = out_dir / "tienda.json"
    tienda_out.write_text(
        json.dumps(hard_tiendas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(hard_tiendas)} tiendas (tight windows) → {tienda_out}")

    return pedidos


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate hard-difficulty pedido/tienda JSON")
    parser.add_argument("--seed",    type=int,  default=99,       help="RNG seed (default: 99)")
    parser.add_argument("--out-dir", type=Path, default=HARD_DIR, help="Output directory")
    args = parser.parse_args()

    generate_hard(seed=args.seed, out_dir=args.out_dir)
