import random

from backend.models.product import OrderLine, Product
from backend.models.pedido import Pedido
from backend.models.tienda import Tienda
from backend.models.zona import Zona

# Fábrica Damm — Barcelona
DEPOT_LAT = 41.3985
DEPOT_LON = 2.1620

PRODUCTS = [
    Product("ED33", "Estrella Damm 33cl x24", False, 0.38),
    Product("ED50", "Estrella Damm 50cl x12", False, 0.55),
    Product("VD33", "Voll-Damm 33cl x24",     False, 0.40),
    Product("BAR20", "Barril Damm 20L",        False, 20.0),
]

ARCHETYPES = [
    {"tipo": "Bar",          "boxes": (30,  90)},
    {"tipo": "Restaurante",  "boxes": (60, 150)},
    {"tipo": "Supermercado", "boxes": (90, 240)},
    {"tipo": "Hotel",        "boxes": (60, 120)},
    {"tipo": "Kiosco",       "boxes": (24,  60)},
]

VENUE_NAMES = [
    "Bar El Xampanyet", "Restaurante La Mar", "Supermercats Bonpreu", "Hotel Arts",
    "Bar Marsella", "Restaurante Tickets", "El Corte Inglés Diagonal", "Hotel Miramar",
    "Bar Calders", "Restaurante Bodega 1900", "Condis Eixample", "Hotel Majestic",
    "Bar Muy Buenas", "Restaurante Pakta", "Supermercats Caprabo", "Hotel W Barcelona",
    "Bar Almiral", "Restaurante Disfrutar", "Mercadona Gracia", "Hotel Barceló Raval",
]


def generate_scenario(seed: int = 42, n_tiendas: int = 16) -> dict:
    """
    Generate a synthetic delivery scenario around the Damm factory.

    Returns
    -------
    {
        "zona":      Zona  — zone with Tiendas and Pedidos attached,
        "depot_lat": float,
        "depot_lon": float,
    }
    """
    rng = random.Random(seed)
    zona = Zona(zona_id="BCN-EIXAMPLE", nombre="Barcelona Eixample")

    names = rng.sample(VENUE_NAMES, min(n_tiendas, len(VENUE_NAMES)))

    for i, name in enumerate(names):
        archetype = rng.choice(ARCHETYPES)
        lat = round(DEPOT_LAT + rng.uniform(-0.025, 0.025), 6)
        lon = round(DEPOT_LON + rng.uniform(-0.025, 0.025), 6)

        tienda = Tienda(tienda_id=f"T{i+1:02d}", nombre=name, x=lat, y=lon)

        target_boxes = rng.randint(*archetype["boxes"])
        chosen = rng.sample(PRODUCTS, rng.randint(1, 2))
        lineas = []
        remaining = target_boxes
        for j, prod in enumerate(chosen):
            if j == len(chosen) - 1:
                qty = max(6, remaining)
            else:
                qty = max(6, rng.randint(remaining // 3, remaining // 2))
                remaining -= qty
            qty = max(6, (qty // 6) * 6)
            lineas.append(OrderLine(product=prod, quantity_boxes=qty))

        pedido = Pedido(
            pedido_id=f"P{i+1:03d}",
            tienda_id=tienda.tienda_id,
            lineas=lineas,
        )
        tienda.añadir_pedido(pedido)
        zona.añadir_tienda(tienda)

    return {
        "zona": zona,
        "depot_lat": DEPOT_LAT,
        "depot_lon": DEPOT_LON,
    }
