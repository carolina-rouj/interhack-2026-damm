# Damm Smart Truck

Logistics optimization tool for last-mile delivery routing and truck load planning, built for **Interhack BCN 2026**. Simulates a Estrella Damm distribution truck making deliveries across Barcelona, optimizing route order, pallet loading, and returnable container collection.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| Data validation | Pydantic v2 |
| Frontend | React 18, Vite 5 |
| Maps | Leaflet + React-Leaflet |
| Numerics | NumPy, Pandas |

---

## Directory Structure

```
interhack-2026-damm/
├── requirements.txt              # Python dependencies
├── backend/
│   ├── main.py                   # FastAPI app and all API endpoints
│   ├── data/
│   │   └── synthetic_generator.py  # Generates synthetic delivery scenarios
│   ├── models/
│   │   ├── client.py             # Client, TimeWindow, AccessRestriction
│   │   ├── order.py              # Product, OrderLine, Order
│   │   ├── truck.py              # PalletSlot, PalletAssignment, LoadPlan
│   │   └── zone.py               # Zone, Depot
│   └── solvers/
│       ├── route_optimizer.py    # Nearest-neighbor + 2-opt TSP solver
│       ├── load_optimizer.py     # LIFO pallet assignment
│       └── inverse_logistics.py  # Returnable container planning
└── frontend/
    ├── package.json
    ├── vite.config.js            # Dev proxy: /api → localhost:8000
    └── src/
        ├── main.jsx              # React entry point
        ├── App.jsx               # Root component, state, layout
        ├── api.js                # HTTP client for backend API
        ├── index.css             # Global styles and theme variables
        └── components/
            ├── MetricsPanel.jsx  # KPI dashboard
            ├── RouteMap.jsx      # Leaflet map with delivery stops
            ├── TruckDiagram.jsx  # Visual pallet layout
            └── ClientTable.jsx   # Delivery stops table with timestamps
```

---

## Backend Architecture

### Entry Point — `backend/main.py`

FastAPI application with in-memory scenario storage (`_scenarios` dict). No database — data lives in memory for the duration of the server process.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/scenario/generate` | Generate a new synthetic scenario |
| `GET` | `/api/scenario/{scenario_id}` | Retrieve a stored scenario |
| `POST` | `/api/optimize` | Run route + load optimization |
| `GET` | `/health` | Health check |

**`GET /api/scenario/generate`**
- Query params: `seed` (int, default 42), `n_clients` (int, default 16)
- Returns: `{ scenario_id, zone, clients[], orders{}, products[] }`
- `scenario_id` is deterministic: `"scenario-{seed}-{n_clients}"`

**`POST /api/optimize`**
- Body: `{ scenario_id: string, start_time: "HH:MM" }`
- Runs the three solvers in sequence, then aggregates metrics
- Returns: `{ route, load_plan, returnables_plan, metrics }`

---

### Models — `backend/models/`

**`client.py`**
- `TimeWindow` — `open_min`, `close_min` (minutes since midnight)
- `AccessRestriction` — enum: `NONE`, `PEDESTRIAN_ZONE`, `RESTRICTED_HOURS`
- `Client` — delivery location with `lat/lon`, `time_window`, `priority` (1–3), `unload_time_min`, `expected_returnables`

**`order.py`**
- `Product` — SKU with `weight_kg`, `returnable` flag
- `OrderLine` — product + quantity
- `Order` — list of `OrderLine`s for one client

**`truck.py`**
- `PalletSlot` — one of 6 slots defined by `row` (1=rear, 3=front) and `col` (1=left, 2=right), with a list of sides it is `accessible_from`
- `PalletAssignment` — maps a slot to a client delivery or returnable buffer
- `LoadPlan` — full set of assignments, warnings, and `utilization_pct` (out of 6 slots × 60 boxes each = 360 boxes total)

Truck geometry (viewed from above):
```
[REAR DOOR]
[ P1 | P2 ]  row=1  <- first to unload  (rear + lona access)
[ P3 | P4 ]  row=2                       (lona access only)
[ P5 | P6 ]  row=3  <- last to unload   (lona access only)
[CABIN]
```

**`zone.py`**
- `Depot` — warehouse coordinates (Damm factory: 41.3985 N, 2.1620 E)
- `Zone` — named area containing a `Depot`

---

### Solvers — `backend/solvers/`

#### `route_optimizer.py` — TSP Solver

Finds an efficient delivery order respecting time windows and client priorities.

**Key functions:**

| Function | Description |
|----------|-------------|
| `haversine_km()` | Real-world geodesic distance between two lat/lon points |
| `avg_speed_kmh(time_min)` | Time-dependent traffic speed |
| `nearest_neighbor()` | Greedy initial route; scores candidates by `distance x priority_weight` |
| `two_opt()` | Local search: swaps route segments if they reduce distance without violating time windows |
| `_simulate_times()` | Simulates arrival, wait, and departure times for a given stop order |
| `optimize_route()` | Orchestrates nearest-neighbor -> 2-opt -> time simulation -> CO2 calculation |

**Traffic model:**

| Time window | Speed |
|-------------|-------|
| 07:00–09:00 | 15 km/h (rush hour) |
| 09:00–13:00 | 25 km/h (normal) |
| 13:00–15:00 | 20 km/h (lunch) |
| Other | 30 km/h |

**Priority weights** (used in nearest-neighbor scoring):
- Priority 1 (restaurants, supermarkets) — 0.5x distance (served first)
- Priority 2 (bars, hotels) — 1.0x
- Priority 3 (kiosks) — 1.5x (served last)

**CO2:** `total_distance_km x 0.27 kg/km` (diesel truck factor)

---

#### `load_optimizer.py` — LIFO Pallet Assignment

Assigns client deliveries to the 6 pallet slots so that the first delivery is loaded last (rear door = first unloaded). Validates LIFO constraints and emits warnings when a client's pallet would be blocked by a later delivery.

---

#### `inverse_logistics.py` — Returnable Container Planning

Calculates expected empty boxes/cases to collect from each client (`expected_returnables` field on `Client`). Reserves front pallet slots (row 3) as a returnable buffer before load optimization runs.

---

### Data Generator — `backend/data/synthetic_generator.py`

`generate_scenario(seed, n_clients)` produces a reproducible Barcelona delivery scenario with randomized-but-realistic clients drawn from five archetypes:

| Archetype | Order size | Time window | Priority |
|-----------|-----------|-------------|---------|
| Bar | 30–90 boxes | 09:00–13:00 | 2 |
| Restaurante | 60–150 boxes | 08:00–11:00 | 1 |
| Supermercado | 90–240 boxes | 07:00–10:00 | 1 |
| Hotel | 60–120 boxes | 09:00–12:00 | 2 |
| Kiosco | 24–60 boxes | 10:00–14:00 | 3 |

---

## Frontend Architecture

### State & Layout — `App.jsx`

Holds all application state: current scenario, optimization results, active tab. Calls `api.js` functions and passes data down to the four display components via props.

### API Layer — `api.js`

Thin HTTP client wrapping `fetch`. Exports:
- `generateScenario(seed, nClients)` — `GET /api/scenario/generate`
- `optimizeScenario(scenarioId, startTime)` — `POST /api/optimize`

Vite proxies `/api/*` to `localhost:8000` in development (`vite.config.js`).

### Components — `src/components/`

| Component | What it shows |
|-----------|--------------|
| `MetricsPanel` | KPI cards: distance, time, CO2, utilization %, violations, priority served |
| `RouteMap` | Leaflet map with depot marker, numbered stop markers, polyline route |
| `TruckDiagram` | 6-slot grid coloured by client, shows LIFO warnings |
| `ClientTable` | Stop-by-stop table: name, arrival time, wait, departure, status badge |

---

## Data Flow

```
User fills sidebar (seed, n_clients, start_time)
        |
        v
GET /api/scenario/generate
        |
        +-- synthetic_generator.generate_scenario()
        |       Creates Zone, Clients, Orders, Products
        |
        +-- Returns scenario_id + full data
               Frontend renders zone + client list
        |
User clicks "Optimizar"
        |
        v
POST /api/optimize { scenario_id, start_time }
        |
        +-- 1. optimize_route()       -> RouteResult (stops, distance, CO2)
        +-- 2. plan_returnables()     -> ReturnablesPlan (reserved slots)
        +-- 3. optimize_load()        -> LoadPlan (assignments, warnings)
        +-- 4. metrics aggregation
        |
        +-- Returns { route, load_plan, returnables_plan, metrics }
               Frontend renders MetricsPanel, RouteMap, ClientTable, TruckDiagram
```

---

## Running the App

**Backend:**
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # starts on http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so no CORS configuration is needed during development.
