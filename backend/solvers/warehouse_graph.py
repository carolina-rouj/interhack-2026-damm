"""
Warehouse movement-cost service.

Provides Manhattan distance by default; falls back to Dijkstra when blocked
cells are supplied so the optimizer can route around physical obstacles.

All distances are expressed in warehouse grid cells.  Multiply by cell_size_m
to get metres; divide by toro.velocidad_celdas_por_min to get minutes.
"""

from __future__ import annotations
import heapq
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.models.almacen import Almacen


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def build_cost_matrix(
    locations: list[tuple[int, int]],
    almacen: Almacen,
    blocked: Optional[set[tuple[int, int]]] = None,
) -> list[list[int]]:
    """
    Return an n×n integer cost matrix (grid cells) for *locations*.

    When *blocked* is None or empty, Manhattan distance is used directly.
    When *blocked* is non-empty, Dijkstra computes shortest paths around
    obstacles within the warehouse bounds.
    """
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]

    if not blocked:
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = manhattan(locations[i], locations[j])
        return matrix

    for i in range(n):
        dist_from_i = _dijkstra(locations[i], almacen, blocked)
        for j in range(n):
            if i != j:
                matrix[i][j] = dist_from_i.get(
                    locations[j],
                    manhattan(locations[i], locations[j]),  # fallback if unreachable
                )
    return matrix


def _dijkstra(
    start: tuple[int, int],
    almacen: Almacen,
    blocked: set[tuple[int, int]],
) -> dict[tuple[int, int], int]:
    """
    Shortest-path distances from *start* to every reachable cell in the
    warehouse grid, skipping blocked cells.
    """
    dist: dict[tuple[int, int], int] = {start: 0}
    heap: list[tuple[int, tuple[int, int]]] = [(0, start)]

    while heap:
        cost, (x, y) = heapq.heappop(heap)
        if cost > dist.get((x, y), float("inf")):
            continue
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not (0 <= nx < almacen.dim_x and 0 <= ny < almacen.dim_y):
                continue
            if (nx, ny) in blocked:
                continue
            new_cost = cost + 1
            if new_cost < dist.get((nx, ny), float("inf")):
                dist[(nx, ny)] = new_cost
                heapq.heappush(heap, (new_cost, (nx, ny)))

    return dist


def pickup_trip_cost(
    toro_pos: tuple[int, int],
    pallet_pos: tuple[int, int],
    staging_pos: tuple[int, int],
    blocked: Optional[set[tuple[int, int]]] = None,
) -> int:
    """
    Total cells a toro travels for one pickup: toro → pallet → staging.

    Uses Manhattan when no blocked set is given.
    """
    if blocked:
        # Simple approximation; full Dijkstra would need an Almacen reference
        pass
    return manhattan(toro_pos, pallet_pos) + manhattan(pallet_pos, staging_pos)
