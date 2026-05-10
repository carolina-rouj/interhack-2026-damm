# Damm Smart Truck - Basic Structure

This project is a logistics optimization demo for Interhack BCN 2026. It simulates a Damm distribution truck in Barcelona and focuses on three main problems: route planning, truck loading, and returnable container collection.

## What Was Built

- A FastAPI backend that generates synthetic delivery scenarios and exposes optimization endpoints.
- A synthetic data generator that creates realistic Barcelona clients, orders, products, and zones.
- Three optimization solvers for route order, pallet loading, and inverse logistics.
- A React + Vite frontend that visualizes the route, metrics, truck layout, and delivery table.
- A shared domain model for clients, products, orders, zones, trucks, and pallet assignments.

## Repository Structure

```text
interhack-2026-damm/
├── README.md
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── data/
│   │   └── synthetic_generator.py
│   ├── models/
│   │   ├── client.py
│   │   ├── product.py
│   │   ├── truck.py
│   │   └── zone.py
│   └── solvers/
│       ├── route_optimizer.py
│       ├── load_optimizer.py
│       └── inverse_logistics.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── api.js
        ├── App.jsx
        ├── index.css
        └── components/
            ├── MetricsPanel.jsx
            ├── RouteMap.jsx
            ├── TruckDiagram.jsx
            └── ClientTable.jsx
```

## Backend

### `backend/main.py`

This is the API entry point. It runs FastAPI with CORS enabled and keeps scenarios in memory for the duration of the server process.

Main endpoints:

- `GET /api/scenario/generate` creates a new synthetic scenario.
- `GET /api/scenario/{scenario_id}` retrieves a stored scenario.
- `POST /api/optimize` runs route optimization, returnable planning, and load optimization.
- `GET /health` returns a simple status check.

### `backend/data/synthetic_generator.py`

This file builds reproducible delivery scenarios from a random seed. It creates:

- A Barcelona zone and depot at the Damm factory.
- Clients with time windows, access restrictions, priorities, and expected returnables.
- Orders with boxes grouped into realistic product mixes.
- A product catalog including beer SKUs and returnable crates.

The generator uses client archetypes such as bars, restaurants, supermarkets, hotels, and kiosks.

### `backend/models/`

The model layer defines the domain objects used by the solver and API.

- `client.py` defines `Client`, `TimeWindow`, and `AccessRestriction`.
- `product.py` defines `Product`, `OrderLine`, and `Order`.
- `truck.py` defines pallet slots, pallet assignments, the load plan, and truck geometry.
- `zone.py` defines `Depot` and `Zone`.

The truck model is based on 6 pallet slots, with rear slots unloaded first and front slots reserved for returnables when needed.

### `backend/solvers/`

The solver layer contains the optimization logic.

- `route_optimizer.py` computes the delivery order using a nearest-neighbor heuristic plus 2-opt improvement. It simulates travel times, applies traffic-dependent speeds, respects time windows when possible, and estimates CO2 emissions.
- `load_optimizer.py` assigns orders to pallet slots using a LIFO-style rule so early deliveries are loaded in more accessible positions. It also emits warnings when loading conflicts or overloads appear.
- `inverse_logistics.py` estimates how many returnable boxes are expected and reserves front pallet slots for them.

## Frontend

### `frontend/src/App.jsx`

This is the main UI controller. It stores the current scenario, optimization result, loading state, error state, and active tab. It also provides the user actions to generate a scenario and run the optimization.

### `frontend/src/api.js`

A small fetch wrapper that talks to the backend API.

- `generateScenario(seed, nClients)` calls `GET /api/scenario/generate`.
- `optimizeScenario(scenarioId, startTime)` calls `POST /api/optimize`.

### `frontend/src/components/`

The UI is split into four display components:

- `MetricsPanel.jsx` shows key KPIs such as distance, time, utilization, CO2, violations, and returnable pallets.
- `RouteMap.jsx` renders the route on a Leaflet map with depot and stop markers.
- `TruckDiagram.jsx` visualizes the 6-slot truck load and warns about conflicts.
- `ClientTable.jsx` lists each stop with its time window, arrival, waiting time, priority, boxes, and status.

## Main Data Flow

1. The user sets a seed, number of clients, and route start time.
2. The frontend requests a synthetic scenario from the backend.
3. The backend stores that scenario in memory and returns the generated data.
4. The user triggers optimization.
5. The backend runs route optimization, returnable planning, and load optimization.
6. The frontend displays metrics, map, truck layout, delivery table, and explanation text.

## What Makes The Project Useful

- It combines route optimization, warehouse loading, and reverse logistics in one demo.
- It uses realistic business rules such as time windows, priorities, and access restrictions.
- It provides a visual dashboard so the optimization result is easy to inspect.
- It is self-contained and does not require a database.

## How To Run

Backend:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to the backend during development.
