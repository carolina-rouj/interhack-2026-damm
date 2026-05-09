"""
Multi-toro (forklift) route optimizer.

Models the warehouse pickup problem as a multi-vehicle routing problem (VRP):
  - Vehicles  = toros, each starting at their initial grid position
  - Nodes     = pallet pickup origins (one per TareaPickup)
  - Arc cost  = realistic travel cost that accounts for the mandatory staging
                drop-off between consecutive pickups:
                    cost(task_i → task_j) = dist(task_i.origin, staging)
                                          + dist(staging, task_j.origin)
  - Objective = minimise total distance across all toros

Node layout in the distance matrix
-----------------------------------
  index 0              : staging area (common end for every toro)
  indices 1 … n_toros  : toro start positions (unique per-vehicle start)
  indices n_toros+1 …  : pallet task origins

OR-Tools is used when installed.  A greedy round-robin fallback is used
otherwise so the system degrades gracefully during local development.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    _HAS_ORTOOLS = True
except ImportError:
    _HAS_ORTOOLS = False

from backend.models.toro import Toro
from backend.models.tarea_pickup import TareaPickup, EstadoTarea
from backend.models.almacen import Almacen
from backend.solvers.base import ForkliftSolver
from backend.solvers.warehouse_graph import manhattan


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass
class TareaAsignada:
    """A TareaPickup bound to a specific toro with a position in its route."""

    tarea: TareaPickup
    toro_id: str
    secuencia: int      # 1-indexed position within this toro's route

    def to_dict(self) -> dict:
        return {
            "tarea_id": self.tarea.tarea_id,
            "palet_id": self.tarea.palet_id,
            "pedido_id": self.tarea.pedido_id,
            "origin": list(self.tarea.origin),
            "destino": list(self.tarea.destino),
            "toro_id": self.toro_id,
            "secuencia": self.secuencia,
        }


@dataclass
class ForkliftPlan:
    """Full result of forklift route optimisation."""

    tareas_asignadas: list[TareaAsignada] = field(default_factory=list)
    distancia_total: int = 0
    rutas_por_toro: dict[str, list[TareaAsignada]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    solver_used: str = "none"

    def ordered_pickups(self) -> list[TareaAsignada]:
        """All assignments sorted by (toro_id, secuencia)."""
        return sorted(self.tareas_asignadas, key=lambda t: (t.toro_id, t.secuencia))

    def to_dict(self) -> dict:
        return {
            "solver_used": self.solver_used,
            "distancia_total_celdas": self.distancia_total,
            "tareas_asignadas": [t.to_dict() for t in self.tareas_asignadas],
            "rutas_por_toro": {
                toro_id: [t.to_dict() for t in tareas]
                for toro_id, tareas in self.rutas_por_toro.items()
            },
            "warnings": self.warnings,
        }


# ── Solver ────────────────────────────────────────────────────────────────────


class ORToolsForkliftSolver(ForkliftSolver):
    """
    OR-Tools VRP solver for warehouse forklift routing.

    Falls back to greedy round-robin when OR-Tools is not installed.
    """

    def __init__(self, time_limit_seconds: int = 5) -> None:
        self.time_limit_seconds = time_limit_seconds

    def solve(
        self,
        tareas: list[TareaPickup],
        toros: list[Toro],
        almacen: Almacen,
        blocked: Optional[set[tuple[int, int]]] = None,
        **kwargs: Any,
    ) -> ForkliftPlan:
        if not tareas:
            return ForkliftPlan()
        if not toros:
            return ForkliftPlan(warnings=["No toros available"])

        if _HAS_ORTOOLS:
            return self._solve_ortools(tareas, toros, blocked)
        return self._solve_greedy(tareas, toros)

    # ── OR-Tools path ─────────────────────────────────────────────────────

    def _solve_ortools(
        self,
        tareas: list[TareaPickup],
        toros: list[Toro],
        blocked: Optional[set[tuple[int, int]]],
    ) -> ForkliftPlan:
        n_toros = len(toros)
        n_tareas = len(tareas)
        staging = tareas[0].destino

        # Node indices:
        #   0             → staging (end depot for all vehicles)
        #   1 … n_toros   → toro start positions
        #   n_toros+1 …   → pallet task origins
        all_locs: list[tuple[int, int]] = (
            [staging]
            + [t.posicion_inicial for t in toros]
            + [t.origin for t in tareas]
        )
        n_nodes = len(all_locs)
        staging_idx = 0

        # Cost matrix encoding mandatory staging drop-off between consecutive tasks
        cost = [[0] * n_nodes for _ in range(n_nodes)]
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i == j:
                    continue
                i_is_task = i >= n_toros + 1
                j_is_task = j >= n_toros + 1

                if i_is_task and j_is_task:
                    # task → task: must pass through staging
                    cost[i][j] = (
                        manhattan(all_locs[i], staging)
                        + manhattan(staging, all_locs[j])
                    )
                else:
                    # any other arc: direct Manhattan
                    cost[i][j] = manhattan(all_locs[i], all_locs[j])

        starts = list(range(1, n_toros + 1))   # toro start nodes
        ends = [staging_idx] * n_toros          # all end at staging

        manager = pywrapcp.RoutingIndexManager(n_nodes, n_toros, starts, ends)
        routing = pywrapcp.RoutingModel(manager)

        def _dist(from_idx: int, to_idx: int) -> int:
            return cost[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

        transit_idx = routing.RegisterTransitCallback(_dist)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        # Toro start nodes (1..n_toros) must not be visited by other vehicles
        for v in range(n_toros):
            start_node = v + 1
            start_index = manager.NodeToIndex(start_node)
            routing.AddDisjunction([start_index], 0)

        # All task nodes are mandatory
        for task_node in range(n_toros + 1, n_nodes):
            routing.AddDisjunction([manager.NodeToIndex(task_node)], 10_000_000)

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.seconds = self.time_limit_seconds

        solution = routing.SolveWithParameters(params)

        if solution is None:
            plan = self._solve_greedy(tareas, toros)
            plan.warnings.insert(0, "OR-Tools found no solution; greedy fallback used")
            return plan

        return self._extract(solution, routing, manager, tareas, toros, n_toros)

    def _extract(
        self,
        solution: Any,
        routing: Any,
        manager: Any,
        tareas: list[TareaPickup],
        toros: list[Toro],
        n_toros: int,
    ) -> ForkliftPlan:
        plan = ForkliftPlan(solver_used="ortools")
        total_dist = 0

        for v_idx, toro in enumerate(toros):
            route: list[TareaAsignada] = []
            index = routing.Start(v_idx)
            seq = 1

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                task_offset = node - (n_toros + 1)
                if task_offset >= 0:
                    tarea = tareas[task_offset]
                    assigned = TareaAsignada(tarea=tarea, toro_id=toro.toro_id, secuencia=seq)
                    tarea.toro_asignado = toro.toro_id
                    tarea.estado = EstadoTarea.ASIGNADA
                    route.append(assigned)
                    plan.tareas_asignadas.append(assigned)
                    seq += 1

                next_index = solution.Value(routing.NextVar(index))
                total_dist += routing.GetArcCostForVehicle(index, next_index, v_idx)
                index = next_index

            plan.rutas_por_toro[toro.toro_id] = route

        plan.distancia_total = total_dist
        return plan

    # ── Greedy fallback ───────────────────────────────────────────────────

    def _solve_greedy(
        self,
        tareas: list[TareaPickup],
        toros: list[Toro],
    ) -> ForkliftPlan:
        """
        Nearest-pallet-first greedy assignment.

        For each unassigned task, pick the toro whose current position is
        closest to the task origin; break ties by toro index.
        """
        plan = ForkliftPlan(solver_used="greedy")
        if not _HAS_ORTOOLS:
            plan.warnings.append("OR-Tools not installed; using greedy nearest-first assignment")

        # Track each toro's current position (starts at initial position)
        toro_pos: dict[str, tuple[int, int]] = {
            t.toro_id: t.posicion_inicial for t in toros
        }
        toro_seq: dict[str, int] = {t.toro_id: 1 for t in toros}
        staging = tareas[0].destino if tareas else (0, 0)

        for toro in toros:
            plan.rutas_por_toro[toro.toro_id] = []

        remaining = list(tareas)
        while remaining:
            # Pick the (toro, task) pair with minimum travel from toro's current pos
            best_toro = toros[0]
            best_task = remaining[0]
            best_cost = manhattan(toro_pos[best_toro.toro_id], best_task.origin)

            for toro in toros:
                for task in remaining:
                    c = manhattan(toro_pos[toro.toro_id], task.origin)
                    if c < best_cost:
                        best_cost = c
                        best_toro = toro
                        best_task = task

            assigned = TareaAsignada(
                tarea=best_task,
                toro_id=best_toro.toro_id,
                secuencia=toro_seq[best_toro.toro_id],
            )
            best_task.toro_asignado = best_toro.toro_id
            best_task.estado = EstadoTarea.ASIGNADA

            plan.rutas_por_toro[best_toro.toro_id].append(assigned)
            plan.tareas_asignadas.append(assigned)
            plan.distancia_total += (
                manhattan(toro_pos[best_toro.toro_id], best_task.origin)
                + manhattan(best_task.origin, staging)
            )

            # Toro returns to staging after delivery
            toro_pos[best_toro.toro_id] = staging
            toro_seq[best_toro.toro_id] += 1
            remaining.remove(best_task)

        return plan
