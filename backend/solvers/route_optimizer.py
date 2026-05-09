import math
from dataclasses import dataclass, field

from backend.models.client import Client
from backend.models.zone import Depot


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def avg_speed_kmh(current_time_min: int) -> float:
    h = current_time_min / 60
    if 7 <= h < 9:
        return 15.0   # morning rush
    if 9 <= h < 13:
        return 25.0   # normal
    if 13 <= h < 15:
        return 20.0   # lunch
    return 30.0


def travel_time_min(lat1, lon1, lat2, lon2, current_time_min: int) -> float:
    dist = haversine_km(lat1, lon1, lat2, lon2)
    speed = avg_speed_kmh(current_time_min)
    return (dist / speed) * 60


@dataclass
class RouteStop:
    client: Client
    arrival_min: int
    wait_min: int
    departure_min: int
    status: str   # "OK" | "TIME_WINDOW_VIOLATED"

    def to_dict(self):
        def fmt(m):
            return f"{m // 60:02d}:{m % 60:02d}"
        return {
            "client": self.client.to_dict(),
            "arrival_time": fmt(self.arrival_min),
            "arrival_min": self.arrival_min,
            "wait_min": self.wait_min,
            "departure_time": fmt(self.departure_min),
            "status": self.status,
        }


@dataclass
class RouteResult:
    route_id: str
    stops: list = field(default_factory=list)
    total_distance_km: float = 0.0
    total_time_min: int = 0
    co2_kg: float = 0.0
    explanations: list = field(default_factory=list)

    def to_dict(self):
        return {
            "route_id": self.route_id,
            "stops": [s.to_dict() for s in self.stops],
            "total_distance_km": round(self.total_distance_km, 2),
            "total_time_min": self.total_time_min,
            "co2_kg": round(self.co2_kg, 2),
            "explanations": self.explanations,
        }


def _route_distance(stops: list, depot: Depot) -> float:
    if not stops:
        return 0.0
    total = haversine_km(depot.lat, depot.lon, stops[0].client.lat, stops[0].client.lon)
    for i in range(len(stops) - 1):
        a, b = stops[i].client, stops[i + 1].client
        total += haversine_km(a.lat, a.lon, b.lat, b.lon)
    total += haversine_km(stops[-1].client.lat, stops[-1].client.lon, depot.lat, depot.lon)
    return total


def _simulate_times(client_order: list, depot: Depot, start_min: int = 480) -> list:
    """Re-simulate arrival/wait/departure times for a given client ordering."""
    stops = []
    cur_lat, cur_lon = depot.lat, depot.lon
    cur_time = start_min

    for client in client_order:
        tt = travel_time_min(cur_lat, cur_lon, client.lat, client.lon, cur_time)
        arrival = int(cur_time + tt)
        if arrival > client.time_window.close_min:
            wait = 0
            status = "TIME_WINDOW_VIOLATED"
        else:
            wait = max(0, client.time_window.open_min - arrival)
            status = "OK"
        departure = arrival + wait + client.unload_time_min
        stops.append(RouteStop(client, arrival, wait, departure, status))
        cur_lat, cur_lon = client.lat, client.lon
        cur_time = departure

    return stops


def _time_windows_feasible(client_order: list, depot: Depot, start_min: int = 480) -> bool:
    stops = _simulate_times(client_order, depot, start_min)
    return all(s.status == "OK" for s in stops)


def nearest_neighbor(clients: list, depot: Depot, start_min: int = 480) -> list:
    unvisited = list(clients)
    ordered = []
    cur_lat, cur_lon = depot.lat, depot.lon
    cur_time = start_min

    while unvisited:
        best = None
        best_score = float("inf")

        for client in unvisited:
            tt = travel_time_min(cur_lat, cur_lon, client.lat, client.lon, cur_time)
            arrival = cur_time + tt
            if arrival > client.time_window.close_min:
                continue
            wait = max(0, client.time_window.open_min - arrival)
            dist = haversine_km(cur_lat, cur_lon, client.lat, client.lon)
            priority_weight = {1: 0.5, 2: 1.0, 3: 1.5}[client.priority]
            score = dist * priority_weight
            if score < best_score:
                best_score = score
                best = client

        if best is None:
            # No feasible client in time window — pick nearest by priority then distance
            best = min(
                unvisited,
                key=lambda c: (c.priority, haversine_km(cur_lat, cur_lon, c.lat, c.lon)),
            )

        ordered.append(best)
        unvisited.remove(best)
        tt = travel_time_min(cur_lat, cur_lon, best.lat, best.lon, cur_time)
        arrival = cur_time + tt
        wait = max(0, best.time_window.open_min - arrival)
        cur_time = arrival + wait + best.unload_time_min
        cur_lat, cur_lon = best.lat, best.lon

    return ordered


def two_opt(client_order: list, depot: Depot, start_min: int = 480) -> list:
    best = list(client_order)
    best_dist = _route_distance(_simulate_times(best, depot, start_min), depot)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if not _time_windows_feasible(candidate, depot, start_min):
                    continue
                dist = _route_distance(_simulate_times(candidate, depot, start_min), depot)
                if dist < best_dist - 1e-6:
                    best = candidate
                    best_dist = dist
                    improved = True

    return best


def _explain_stop(stop: RouteStop, position: int) -> str:
    reasons = []
    if stop.client.priority == 1:
        reasons.append("cliente prioritario (entrega obligatoria)")
    window_min = stop.client.time_window.close_min - stop.client.time_window.open_min
    if window_min <= 90:
        reasons.append(f"ventana horaria muy ajustada ({window_min} min)")
    if stop.wait_min > 0:
        def fmt(m): return f"{m//60:02d}:{m%60:02d}"
        reasons.append(f"llegada anticipada, espera {stop.wait_min} min hasta apertura {fmt(stop.client.time_window.open_min)}")
    if stop.status == "TIME_WINDOW_VIOLATED":
        reasons.append("AVISO: ventana horaria no cumplida")
    if stop.client.expected_returnables > 0:
        reasons.append(f"recogida de ~{stop.client.expected_returnables} cajas retornables")
    return f"Parada {position}: {stop.client.name} — {', '.join(reasons) or 'posición óptima por distancia'}"


def optimize_route(route_id: str, clients: list, depot: Depot, start_min: int = 480) -> RouteResult:
    if not clients:
        return RouteResult(route_id=route_id)

    ordered = nearest_neighbor(clients, depot, start_min)
    ordered = two_opt(ordered, depot, start_min)

    stops = _simulate_times(ordered, depot, start_min)
    dist = _route_distance(stops, depot)
    total_time = stops[-1].departure_min - start_min if stops else 0
    co2 = dist * 0.27

    explanations = [_explain_stop(s, i + 1) for i, s in enumerate(stops)]

    return RouteResult(
        route_id=route_id,
        stops=stops,
        total_distance_km=dist,
        total_time_min=total_time,
        co2_kg=co2,
        explanations=explanations,
    )
