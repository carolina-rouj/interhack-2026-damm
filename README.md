# Damm Smart Truck

Logistics optimization tool for last-mile routing and truck-loading planning, built for **Interhack BCN 2026**. It simulates an Estrella Damm truck's distribution across Barcelona, optimizing route order, pallet loading, and returnable container pickup.

The system has three layers: a Python **backend** that runs the optimization algorithms, a **web dashboard** for managers that visualizes the resulting routes, and a **mobile app** for the driver with real-time GPS navigation.

---

## Tech stack

| Layer | Technology |
|------|-----------|
| Backend | Python, FastAPI, OR-Tools (Google) |
| Web dashboard | HTML + CSS + vanilla JavaScript |
| Mobile app | React Native, Expo, react-native-maps, Three.js |
| Maps (mobile) | Google Maps Directions API, expo-location |

---

## Project structure

```
interhack-2026-damm/
├── backend/
│   ├── main.py                    # FastAPI — REST endpoints
│   ├── pipeline.py                # Full pipeline orchestrator
│   ├── models/                    # Domain models
│   │   ├── zona.py                # Zone with stores + distance matrix
│   │   ├── tienda.py              # Delivery point (bar, restaurant, supermarket...)
│   │   ├── pedido.py              # Order with product lines
│   │   ├── product.py             # SKU definition
│   │   ├── ruta.py                # Route with ordered stops
│   │   ├── palet.py               # Physical pallet
│   │   └── truck.py               # Truck type and loading plan
│   ├── solvers/
│   │   ├── orchestrator.py        # run_pipeline() — entry point
│   │   ├── vrptw_solver.py        # VRPTW solver with OR-Tools
│   │   └── palletizer.py          # Palletizing, returnables, truck loading
│   └── data/
│       ├── loader.py              # load_zona() — loads the JSON files
│       ├── tienda.json            # ~1500 stores in Granollers
│       ├── pedido.json            # Orders per store
│       ├── producto.json          # SKU catalog
│       └── zona.json              # Zone definitions
│
├── frontend/
│   └── index.html                 # Web dashboard (single-page app)
│
├── mobile/
│   ├── App.js                     # App root — tab navigation
│   ├── metro.config.js            # Metro bundler configuration
│   └── src/
│       ├── api.js                 # HTTP client to the backend
│       ├── constants.js           # Colors, truck configs, MOCK_DEPOT
│       ├── screens/
│       │   ├── RouteScreen.js     # Map + stops + GPS navigation
│       │   └── LoadScreen.js      # 3D truck visualization
│       ├── components/
│       │   ├── TruckGrid3D.js     # 3D truck model (Three.js)
│       │   ├── TruckGrid.js       # 2D pallet grid view
│       │   ├── ReportPreviewModal.js  # Report preview modal
│       │   ├── MetricsBar.js      # KPI bar
│       │   └── StopsList.js       # Stops list
│       ├── services/
│       │   └── directionsService.js   # Google Directions API
│       └── utils/
│           ├── transform.js       # Backend JSON → internal objects
│           └── reportGenerator.js # PDF report generation and download
│
└── output/
    └── routes/                    # Generated route JSON files
```

---

## Data flow — overview

```
┌───────────────────────────────────────────────────────┐
│                  WEB DASHBOARD (manager)               │
│  1. Selects zone                                       │
│  2. Adjusts boxes/pallet                                │
│  3. Clicks "Optimize"  ──── POST /api/solve ──────►    │
│                                                         │
│  ◄── routes + metrics ───────────────────────────────  │
│  4. Views routes, stops, metrics                        │
└───────────────────────────────────────────────────────┘
                          │
               Backend runs pipeline
                          │
┌───────────────────────────────────────────────────────┐
│                MOBILE APP (driver)                      │
│  1. Loads assigned route                                │
│  2. "Route" tab: map + GPS navigation                    │
│  3. Marks stops as delivered                             │
│  4. "Load" tab: 3D truck visualization                   │
│  5. Generates a PDF report on completion                 │
└───────────────────────────────────────────────────────┘
```

---

## Backend

### REST API — `backend/main.py`

FastAPI running on port 8000. It also serves the web dashboard as static files.

| Method | Route | Description |
|--------|------|-------------|
| `GET` | `/api/zona/list` | List of available zones |
| `GET` | `/api/zona/{zona_id}` | Metadata for a zone |
| `POST` | `/api/solve` | Runs the full optimization pipeline |
| `GET` | `/health` | Health check |

**`POST /api/solve`**
```json
// Request
{ "zona_id": "granollers-center-01", "cajas_por_palet": 60 }

// Response
{
  "zona_id": "granollers-center-01",
  "num_rutas": 3,
  "metrics": { "num_rutas": 3, "total_palets": 8, "coste_total": 450.75, ... },
  "routes": [
    {
      "route": {
        "tipo_camion": "grande",
        "paradas": [
          {
            "orden": 1,
            "llegada_min": 510,
            "coordenadas": { "lat": 41.405, "lon": 2.160 },
            "clientes": [
              {
                "nombre": "Bar Central",
                "total_cajas": 24,
                "productos": [{ "sku": "DAMM-LATA-33", "cantidad_cajas": 12, "tipo_envase": "caja" }]
              }
            ]
          }
        ]
      }
    }
  ]
}
```

### Optimization pipeline — `backend/solvers/orchestrator.py`

`run_pipeline(zona_id)` runs these stages in order:

1. **Data loading** — `load_zona()` hydrates the Zona, Tienda, and Pedido objects from the JSON files
2. **Distance matrix** — Euclidean distance between stores (or Google Maps if available)
3. **Clustering** — groups nearby stores into Stops (a stop can include several stores)
4. **VRPTW** — OR-Tools assigns stops to trucks while respecting time windows and capacity
5. **Palletizing** — assigns each stop's boxes to physical pallets
6. **Returnables** — calculates empty containers to pick up, reserves rear slots
7. **Loading plan** — maps pallets to truck slots respecting LIFO constraints

**Traffic model:**

| Time slot | Speed |
|----------------|-----------|
| 07:00–09:00 | 15 km/h (rush hour) |
| 09:00–13:00 | 25 km/h |
| 13:00–15:00 | 20 km/h (midday) |
| Rest of day | 30 km/h |

**Truck types:**

| Type | Pallet slots |
|------|--------------|
| Van | 3 |
| Medium | 6 |
| Large | 8 |

**Truck geometry (top-down view):**
```
[REAR DOOR]
[ P1 | P2 ]  row 1  ← unloaded first  (rear access + tarp)
[ P3 | P4 ]  row 2                     (tarp access)
[ P5 | P6 ]  row 3  ← unloaded last    (tarp access)
[CAB]
```

---

## Web dashboard

**Single file:** `frontend/index.html` — HTML + CSS + vanilla JavaScript, no framework or build step.

**Usage flow:**
1. On page load → `GET /api/zona/list` → renders zone cards
2. The manager selects a zone and adjusts the boxes/pallet slider
3. Clicking "Optimize" → `POST /api/solve` → shows a spinner with loading messages
4. On response, renders: overall metrics, products by SKU, and route cards with stops

---

## Mobile app

React Native + Expo with two main tabs.

### Route tab — `RouteScreen.js`

Manages the driver's navigation from departure to the final delivery.

**Screen states:**

| State | Description |
|--------|-------------|
| `preview` | Full route view on the map, before departing |
| `navigating` | Active navigation: map centered on the driver, distance to next stop |
| `completed` | All stops delivered, option to generate a report |

**On tapping "Start Route":**
1. Requests location permissions
2. Gets the driver's current GPS position (`getCurrentPositionAsync`)
3. Recalculates route legs from that real position (Google Directions API)
4. Starts continuous tracking (`watchPositionAsync`) — the map follows the driver

**GPS tracking:**
- Updates every 2 seconds or every 10 meters of movement
- `haversineM()` calculates the real-time distance to the next stop

### Load tab — `LoadScreen.js`

Shows the truck's loading plan and the delivery list.

- **TruckGrid3D** (Three.js): 3D truck model with pallets color-coded by stop; completed deliveries are dimmed
- **Delivery list** (slide-out panel): splits stops into "To deliver" and "Delivered", with box and keg counts per customer

### Report generation — `reportGenerator.js`

On completing the route, the driver can generate a PDF with a delivery summary (stops, boxes, kegs per SKU) and share it via the device's native share sheet.

---

## Running it

**Backend:**
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Web dashboard:** open `frontend/index.html` directly in the browser (or serve it from FastAPI at `localhost:8000`).

**Mobile app:**
```bash
cd mobile
npm install
npx expo start --clear
```

Edit `mobile/src/constants.js` → `BASE_URL` with the backend server's local IP.
