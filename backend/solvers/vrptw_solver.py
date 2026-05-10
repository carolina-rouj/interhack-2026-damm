"""
OR-Tools VRPTW solver with heterogeneous truck fleet.

Receives pre-clustered Parada stops from agrupar_tiendas() and routes them
across a fleet of Furgoneta / CamionMediano / CamionGrande vehicles, letting
the solver choose how many trucks and which types to use.

Falls back to a nearest-neighbour greedy heuristic when OR-Tools is
unavailable.

Usage
-----
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas)
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional

from backend.models.ruta import Parada, Ruta
from backend.models.truck import CamionFactory, TipoCamion
from backend.solvers.base import VRPSolver

if TYPE_CHECKING:
    from backend.models.zona import Zona
    from backend.models.truck import Camion

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    _ORTOOLS_OK = True
except ImportError:
    _ORTOOLS_OK = False

# ── constants ─────────────────────────────────────────────────────────────────

DEPOT_LAT = 41.3985   # Fábrica Damm — Barcelona
DEPOT_LON = 2.1620

BOXES_PER_PALLET = 60

# (TipoCamion, pallet_slots, fixed_cost_units)
FLEET_SPEC = [
    (TipoCamion.FURGONETA, 3,  100),
    (TipoCamion.MEDIANO,   6,  200),
    (TipoCamion.GRANDE,    8,  300),
]
MAX_PER_TYPE = 3   # upper bound on vehicles of each type offered to solver


# ── helpers ───────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _speed_kmh(time_min: int) -> float:
    h = time_min / 60
    if 7 <= h < 9:   return 15.0
    if 9 <= h < 13:  return 25.0
    if 13 <= h < 15: return 20.0
    return 30.0


def _travel_min(lat1: float, lon1: float, lat2: float, lon2: float,
                current_min: int = 480) -> int:
    dist = _haversine_km(lat1, lon1, lat2, lon2)
    return max(1, int(dist / _speed_kmh(current_min) * 60))


def _rep_coords(parada: Parada) -> tuple[float, float]:
    rep = next(
        (t for t in parada.tiendas if t.tienda_id == parada.representante_id),
        parada.tiendas[0],
    )
    return rep.x, rep.y


def _fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ── solver ────────────────────────────────────────────────────────────────────

class ORToolsVRPTWSolver(VRPSolver):
    """
    Heterogeneous-fleet VRPTW.

    Time windows are hard: trucks must arrive within [open_min, close_min].
    The solver chooses vehicle types via fixed-cost penalties.
    Pass paradas=<list[Parada]> as a keyword argument to solve().
    """

    def solve(
        self,
        zona: Zona,
        camiones: list[Camion],
        *,
        paradas: list[Parada],
        depot_lat: float = DEPOT_LAT,
        depot_lon: float = DEPOT_LON,
        start_min: int = 480,
        service_time_min: int = 15,
        solver_time_limit_sec: int = 30,
        **kwargs: Any,
    ) -> list[Ruta]:
        if not paradas:
            return []

        if _ORTOOLS_OK:
            return self._solve_ortools(
                zona, paradas, depot_lat, depot_lon,
                start_min, service_time_min, solver_time_limit_sec,
            )
        return self._solve_greedy(
            zona, paradas, depot_lat, depot_lon, start_min, service_time_min,
        )

    # ── matrix builders ───────────────────────────────────────────────────

    def _build_matrices(
        self,
        paradas: list[Parada],
        depot_lat: float,
        depot_lon: float,
        start_min: int,
    ) -> tuple[list[list[int]], list[list[int]]]:
        """
        Return (cost_matrix, time_matrix) both (n+1)×(n+1), depot at index 0.
        Cost units: km×100 (integer). Time units: minutes (integer).
        """
        n = len(paradas)
        coords = [(depot_lat, depot_lon)] + [_rep_coords(p) for p in paradas]

        cost: list[list[int]] = [[0] * (n + 1) for _ in range(n + 1)]
        time: list[list[int]] = [[0] * (n + 1) for _ in range(n + 1)]

        for i in range(n + 1):
            for j in range(n + 1):
                if i == j:
                    continue
                km = _haversine_km(*coords[i], *coords[j])
                cost[i][j] = int(km * 100)
                time[i][j] = _travel_min(*coords[i], *coords[j], start_min)

        return cost, time

    # ── OR-Tools path ─────────────────────────────────────────────────────

    def _solve_ortools(
        self,
        zona: Zona,
        paradas: list[Parada],
        depot_lat: float,
        depot_lon: float,
        start_min: int,
        service_time_min: int,
        time_limit_sec: int,
    ) -> list[Ruta]:
        n = len(paradas)
        cost_matrix, time_matrix = self._build_matrices(
            paradas, depot_lat, depot_lon, start_min,
        )

        # Build fleet
        vehicles: list[dict] = []
        for tipo, slots, fixed_cost in FLEET_SPEC:
            cap = slots * BOXES_PER_PALLET
            for k in range(MAX_PER_TYPE):
                vehicles.append({
                    "tipo": tipo,
                    "capacity": cap,
                    "fixed_cost": fixed_cost * 1000,
                    "vid": f"{tipo.value}-{k}",
                })
        nv = len(vehicles)

        manager = pywrapcp.RoutingIndexManager(n + 1, nv, 0)
        routing = pywrapcp.RoutingModel(manager)

        # Arc cost
        def arc_cost(fi, ti):
            return cost_matrix[manager.IndexToNode(fi)][manager.IndexToNode(ti)]
        arc_cb = routing.RegisterTransitCallback(arc_cost)
        routing.SetArcCostEvaluatorOfAllVehicles(arc_cb)

        # Fixed cost per vehicle
        for vi, v in enumerate(vehicles):
            routing.SetFixedCostOfVehicle(v["fixed_cost"], vi)

        # Capacity dimension
        def demand(idx):
            node = manager.IndexToNode(idx)
            return 0 if node == 0 else paradas[node - 1].num_cajas_total
        demand_cb = routing.RegisterUnaryTransitCallback(demand)
        routing.AddDimensionWithVehicleCapacity(
            demand_cb, 0, [v["capacity"] for v in vehicles], True, "Capacity"
        )

        # Time dimension (transit includes service time at the FROM node)
        def arc_time(fi, ti):
            f = manager.IndexToNode(fi)
            t = manager.IndexToNode(ti)
            svc = service_time_min if f != 0 else 0
            return time_matrix[f][t] + svc
        time_cb = routing.RegisterTransitCallback(arc_time)
        # Allow up to 2 h waiting so narrow windows don't force infeasibility
        routing.AddDimension(time_cb, 120, 24 * 60, False, "Time")
        tdim = routing.GetDimensionOrDie("Time")

        # Depot: all vehicles depart at start_min
        for vi in range(nv):
            tdim.CumulVar(routing.Start(vi)).SetRange(start_min, start_min)

        # Customer time windows
        for i, p in enumerate(paradas):
            idx = manager.NodeToIndex(i + 1)
            tdim.CumulVar(idx).SetRange(p.horario_inicio_min, p.horario_fin_min)

        # Penalise long overall routes
        tdim.SetGlobalSpanCostCoefficient(1)

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.FromSeconds(time_limit_sec)

        sol = routing.SolveWithParameters(params)
        if not sol:
            return self._solve_greedy(
                zona, paradas, depot_lat, depot_lon, start_min, service_time_min,
            )

        return self._extract_routes(zona, routing, manager, sol, paradas, vehicles, tdim)

    def _extract_routes(
        self, zona, routing, manager, solution, paradas, vehicles, tdim
    ) -> list[Ruta]:
        rutas: list[Ruta] = []
        for vi in range(routing.vehicles()):
            if not routing.IsVehicleUsed(solution, vi):
                continue

            stops: list[Parada] = []
            idx = routing.Start(vi)
            while not routing.IsEnd(idx):
                node = manager.IndexToNode(idx)
                if node != 0:
                    p = paradas[node - 1]
                    p.llegada_min = solution.Value(tdim.CumulVar(idx))
                    stops.append(p)
                idx = solution.Value(routing.NextVar(idx))

            if not stops:
                continue

            v = vehicles[vi]
            for k, p in enumerate(stops):
                p.orden = k

            rutas.append(Ruta(
                ruta_id=f"ruta-{vi}",
                zona_id=zona.zona_id,
                camion_id=v["vid"],
                paradas=stops,
                coste_total=round(solution.ObjectiveValue() / 100, 2),
            ))
        return rutas

    # ── greedy fallback ───────────────────────────────────────────────────

    def _solve_greedy(
        self,
        zona: Zona,
        paradas: list[Parada],
        depot_lat: float,
        depot_lon: float,
        start_min: int,
        service_time_min: int,
    ) -> list[Ruta]:
        """Nearest-neighbour greedy; packs stops by CamionGrande capacity."""
        rutas: list[Ruta] = []
        remaining = list(paradas)
        route_idx = 0

        # Always offer the largest truck first so one route fits as much as possible
        tipo_default, slots_default, _ = FLEET_SPEC[-1]
        capacity_default = slots_default * BOXES_PER_PALLET

        while remaining:
            stops: list[Parada] = []
            total_boxes = 0
            cur_lat, cur_lon = depot_lat, depot_lon
            cur_time = start_min
            pool = list(remaining)

            while pool:
                best: Optional[Parada] = None
                best_dist = float("inf")
                best_arrival = 0

                for p in pool:
                    if total_boxes + p.num_cajas_total > capacity_default:
                        continue
                    lat, lon = _rep_coords(p)
                    tt = _travel_min(cur_lat, cur_lon, lat, lon, cur_time)
                    arrival = cur_time + tt
                    if arrival > p.horario_fin_min:
                        continue
                    dist = _haversine_km(cur_lat, cur_lon, lat, lon)
                    if dist < best_dist:
                        best_dist = dist
                        best = p
                        best_arrival = max(arrival, p.horario_inicio_min)

                if best is None:
                    break

                best.llegada_min = best_arrival
                stops.append(best)
                total_boxes += best.num_cajas_total
                cur_lat, cur_lon = _rep_coords(best)
                cur_time = best_arrival + service_time_min
                remaining.remove(best)
                pool.remove(best)

            if not stops:
                # Fallback: force one unschedulable stop into its own route
                p = remaining.pop(0)
                p.llegada_min = start_min
                stops = [p]

            for k, p in enumerate(stops):
                p.orden = k

            camion = CamionFactory.crear(tipo_default, f"{tipo_default.value}-{route_idx}")
            rutas.append(Ruta(
                ruta_id=f"ruta-{route_idx}",
                zona_id=zona.zona_id,
                camion_id=camion.camion_id,
                paradas=stops,
            ))
            route_idx += 1

        return rutas
