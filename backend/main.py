import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.data.synthetic_generator import generate_scenario
from backend.solvers.route_optimizer import optimize_route
from backend.solvers.load_optimizer import optimize_load
from backend.solvers.inverse_logistics import plan_returnables

app = FastAPI(title="Damm Smart Truck API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory scenario store (enough for hackathon demo)
_scenarios: dict = {}


@app.get("/api/scenario/generate")
def generate(seed: int = 42, n_clients: int = 16):
    """Generate a fresh synthetic delivery scenario."""
    data = generate_scenario(seed=seed, n_clients=n_clients)
    scenario_id = f"scenario-{seed}-{n_clients}"
    _scenarios[scenario_id] = data
    return {
        "scenario_id": scenario_id,
        "zone": data["zone"].to_dict(),
        "clients": [c.to_dict() for c in data["clients"]],
        "orders": {cid: o.to_dict() for cid, o in data["orders"].items()},
        "products": [p.to_dict() for p in data["products"]],
    }


@app.get("/api/scenario/{scenario_id}")
def get_scenario(scenario_id: str):
    if scenario_id not in _scenarios:
        raise HTTPException(404, "Scenario not found. Generate one first via /api/scenario/generate")
    data = _scenarios[scenario_id]
    return {
        "scenario_id": scenario_id,
        "zone": data["zone"].to_dict(),
        "clients": [c.to_dict() for c in data["clients"]],
        "orders": {cid: o.to_dict() for cid, o in data["orders"].items()},
        "products": [p.to_dict() for p in data["products"]],
    }


class OptimizeRequest(BaseModel):
    scenario_id: str
    start_time: str = "08:00"   # HH:MM


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    """Run route + load optimization on a stored scenario."""
    if req.scenario_id not in _scenarios:
        raise HTTPException(404, "Scenario not found. Generate one first via /api/scenario/generate")

    data = _scenarios[req.scenario_id]
    clients = data["clients"]
    orders = data["orders"]
    depot = data["zone"].depot

    h, m = req.start_time.split(":")
    start_min = int(h) * 60 + int(m)

    # 1. Route optimization
    route_result = optimize_route(
        route_id=req.scenario_id,
        clients=clients,
        depot=depot,
        start_min=start_min,
    )

    # 2. Inverse logistics planning
    returnables_plan = plan_returnables(clients)

    # 3. Load optimization (uses delivery order from route)
    delivery_sequence = [
        (stop.client.client_id, stop.client.name)
        for stop in route_result.stops
    ]
    load_plan = optimize_load(
        route_id=req.scenario_id,
        delivery_sequence=delivery_sequence,
        orders=orders,
        returnables_plan=returnables_plan,
    )

    # 4. Metrics summary
    n_violations = sum(1 for s in route_result.stops if s.status == "TIME_WINDOW_VIOLATED")
    n_priority1 = sum(1 for c in clients if c.priority == 1)
    n_priority1_served = sum(
        1 for s in route_result.stops if s.client.priority == 1 and s.status == "OK"
    )

    metrics = {
        "total_distance_km": route_result.total_distance_km,
        "total_time_min": route_result.total_time_min,
        "co2_kg": route_result.co2_kg,
        "truck_utilization_pct": load_plan.utilization_pct,
        "stops_total": len(route_result.stops),
        "time_window_violations": n_violations,
        "priority1_served": f"{n_priority1_served}/{n_priority1}",
        "returnables_pallets_reserved": returnables_plan.pallets_reserved,
        "returnables_boxes_expected": returnables_plan.total_expected_boxes,
        "load_warnings": len(load_plan.warnings),
    }

    return {
        "route": route_result.to_dict(),
        "load_plan": load_plan.to_dict(),
        "returnables_plan": returnables_plan.to_dict(),
        "metrics": metrics,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
