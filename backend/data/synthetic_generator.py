import random
from backend.models.client import Client, TimeWindow, AccessRestriction
from backend.models.order import Order, OrderLine, Product
from backend.models.zone import Zone, Depot

# Damm factory Barcelona
DEPOT_LAT = 41.3985
DEPOT_LON = 2.1620

PRODUCTS = [
    Product("ED33", "Estrella Damm 33cl x24", False, 0.38),
    Product("ED50", "Estrella Damm 50cl x12", False, 0.55),
    Product("VD33", "Voll-Damm 33cl x24", False, 0.40),
    Product("BAR20", "Barril Damm 20L", False, 20.0),
    Product("CAJA", "Caja vacía retornable", True, 2.0),
]

CLIENT_ARCHETYPES = [
    {
        "type": "Bar",
        "unload": (8, 15),
        "window": ("09:00", "13:00"),
        "boxes": (30, 90),
        "priority": 2,
        "returnable_prob": 0.7,
    },
    {
        "type": "Restaurante",
        "unload": (10, 20),
        "window": ("08:00", "11:00"),
        "boxes": (60, 150),
        "priority": 1,
        "returnable_prob": 0.6,
    },
    {
        "type": "Supermercado",
        "unload": (20, 35),
        "window": ("07:00", "10:00"),
        "boxes": (90, 240),
        "priority": 1,
        "returnable_prob": 0.5,
    },
    {
        "type": "Hotel",
        "unload": (15, 25),
        "window": ("09:00", "12:00"),
        "boxes": (60, 120),
        "priority": 2,
        "returnable_prob": 0.4,
    },
    {
        "type": "Kiosco",
        "unload": (5, 10),
        "window": ("10:00", "14:00"),
        "boxes": (24, 60),
        "priority": 3,
        "returnable_prob": 0.6,
    },
]

VENUE_NAMES = [
    "Bar El Xampanyet", "Restaurante La Mar", "Supermercats Bonpreu", "Hotel Arts",
    "Bar Marsella", "Restaurante Tickets", "El Corte Inglés Diagonal", "Hotel Miramar",
    "Bar Calders", "Restaurante Bodega 1900", "Condis Eixample", "Hotel Majestic",
    "Bar Muy Buenas", "Restaurante Pakta", "Supermercats Caprabo", "Hotel W Barcelona",
    "Bar Almiral", "Restaurante Disfrutar", "Mercadona Gracia", "Hotel Barceló Raval",
]


def generate_scenario(seed: int = 42, n_clients: int = 16) -> dict:
    rng = random.Random(seed)

    zone = Zone(
        zone_id="BCN-EIXAMPLE",
        name="Barcelona Eixample",
        city="Barcelona",
        depot=Depot("Fábrica Damm", DEPOT_LAT, DEPOT_LON),
    )

    names = rng.sample(VENUE_NAMES, min(n_clients, len(VENUE_NAMES)))

    clients = []
    orders = {}

    for i, name in enumerate(names):
        archetype = rng.choice(CLIENT_ARCHETYPES)

        # Scatter clients around depot (±0.025 degrees ≈ 2.5 km)
        lat = DEPOT_LAT + rng.uniform(-0.025, 0.025)
        lon = DEPOT_LON + rng.uniform(-0.025, 0.025)

        tw = TimeWindow.from_hhmm(*archetype["window"])

        restriction = AccessRestriction.NONE
        r = rng.random()
        if r < 0.15:
            restriction = AccessRestriction.TIME_RESTRICTED
        elif r < 0.20:
            restriction = AccessRestriction.PEDESTRIAN_ZONE

        returnables = 0
        if rng.random() < archetype["returnable_prob"]:
            returnables = rng.randint(20, 60)

        client = Client(
            client_id=f"C{i+1:02d}",
            name=name,
            lat=round(lat, 6),
            lon=round(lon, 6),
            unload_time_min=rng.randint(*archetype["unload"]),
            time_window=tw,
            restriction=restriction,
            priority=archetype["priority"],
            expected_returnables=returnables,
        )
        clients.append(client)

        # Build order: 1-2 products, total boxes within archetype range
        target_boxes = rng.randint(*archetype["boxes"])
        order_lines = []
        remaining = target_boxes
        chosen_products = rng.sample(PRODUCTS[:4], rng.randint(1, 2))  # no empty crates in deliveries
        for j, prod in enumerate(chosen_products):
            if j == len(chosen_products) - 1:
                qty = max(6, remaining)
            else:
                qty = max(6, rng.randint(remaining // 3, remaining // 2))
                remaining -= qty
            # Round to multiples of 6 (standard packaging unit)
            qty = max(6, (qty // 6) * 6)
            order_lines.append(OrderLine(prod, qty))

        orders[client.client_id] = Order(
            order_id=f"ORD-{i+1:03d}",
            client_id=client.client_id,
            lines=order_lines,
        )

    return {
        "zone": zone,
        "clients": clients,
        "orders": orders,
        "products": PRODUCTS,
    }
