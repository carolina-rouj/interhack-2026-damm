from dataclasses import dataclass, field


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


# Matrices are (n+1)×(n+1): index 0 = depot, indices 1..n = clients.
# dist_matrix[i][j]  → km between node i and node j
# time_matrix[i][j]  → minutes between node i and node j (from Google Maps)


def _route_distance(order: list, dist_matrix: list) -> float:
    """Total distance depot → order[0] → … → order[-1] → depot."""
    if not order:
        return 0.0
    total = dist_matrix[0][order[0]]
    for i in range(len(order) - 1):
        total += dist_matrix[order[i]][order[i + 1]]
    total += dist_matrix[order[-1]][0]
    return total


def _simulate_times(
    order: list,
    clients: list,
    time_matrix: list,
    start_min: int = 480,
) -> list:
    stops = []
    cur_node = 0
    cur_time = start_min

    for idx in order:
        client = clients[idx - 1]
        arrival = int(cur_time + time_matrix[cur_node][idx])
        if arrival > client.time_window.close_min:
            wait, status = 0, "TIME_WINDOW_VIOLATED"
        else:
            wait, status = max(0, client.time_window.open_min - arrival), "OK"
        departure = arrival + wait + client.unload_time_min
        stops.append(RouteStop(client, arrival, wait, departure, status))
        cur_node = idx
        cur_time = departure

    return stops


def _feasible(order: list, clients: list, time_matrix: list, start_min: int) -> bool:
    return all(
        s.status == "OK"
        for s in _simulate_times(order, clients, time_matrix, start_min)
    )


def nearest_neighbor(
    clients: list,
    dist_matrix: list,
    time_matrix: list,
    start_min: int = 480,
) -> list:
    unvisited = set(range(1, len(clients) + 1))
    order = []
    cur_node = 0
    cur_time = start_min

    while unvisited:
        best_idx, best_score = None, float("inf")

        for idx in unvisited:
            client = clients[idx - 1]
            arrival = cur_time + time_matrix[cur_node][idx]
            if arrival > client.time_window.close_min:
                continue
            wait = max(0, client.time_window.open_min - arrival)
            score = dist_matrix[cur_node][idx] * {1: 0.5, 2: 1.0, 3: 1.5}[client.priority]
            if score < best_score:
                best_score, best_idx = score, idx

        if best_idx is None:
            best_idx = min(
                unvisited,
                key=lambda i: (clients[i - 1].priority, dist_matrix[cur_node][i]),
            )

        order.append(best_idx)
        unvisited.remove(best_idx)
        client = clients[best_idx - 1]
        arrival = cur_time + time_matrix[cur_node][best_idx]
        wait = max(0, client.time_window.open_min - arrival)
        cur_time = arrival + wait + client.unload_time_min
        cur_node = best_idx

    return order


def two_opt(
    order: list,
    clients: list,
    dist_matrix: list,
    time_matrix: list,
    start_min: int = 480,
) -> list:
    best = list(order)
    best_dist = _route_distance(best, dist_matrix)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                if not _feasible(candidate, clients, time_matrix, start_min):
                    continue
                dist = _route_distance(candidate, dist_matrix)
                if dist < best_dist - 1e-6:
                    best, best_dist, improved = candidate, dist, True

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


def optimize_route(
    route_id: str,
    clients: list,
    dist_matrix: list,
    time_matrix: list,
    start_min: int = 480,
) -> RouteResult:
    """
    dist_matrix and time_matrix must be (n+1)×(n+1) with index 0 = depot.
    dist_matrix[i][j] in km, time_matrix[i][j] in minutes (from Google Maps).
    """
    if not clients:
        return RouteResult(route_id=route_id)

    order = nearest_neighbor(clients, dist_matrix, time_matrix, start_min)
    order = two_opt(order, clients, dist_matrix, time_matrix, start_min)

    stops = _simulate_times(order, clients, time_matrix, start_min)
    dist = _route_distance(order, dist_matrix)
    total_time = stops[-1].departure_min - start_min if stops else 0

    return RouteResult(
        route_id=route_id,
        stops=stops,
        total_distance_km=dist,
        total_time_min=total_time,
        co2_kg=round(dist * 0.27, 2),
        explanations=[_explain_stop(s, i + 1) for i, s in enumerate(stops)],
    )
