"""
Abstract base classes for all logistics solvers.

Design contract
---------------
Each solver receives plain data objects and returns a result dict (or domain
objects for composite solvers).  Solvers must never mutate their inputs; they
return a solution that the caller applies to the model.

Extending a solver
------------------
1. Subclass the appropriate ABC.
2. Implement ``solve()``.
3. Register it in the relevant factory or pass it directly to Ciudad / Zona.

No concrete algorithm lives here — this module is exclusively interfaces.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.models.pedido import Pedido
    from backend.models.palet import Palet
    from backend.models.truck import Camion
    from backend.models.zona import Zona
    from backend.models.ruta import Ruta


# ── Packing solver ────────────────────────────────────────────────────────────


class PackingSolver(ABC):
    """
    Decides how to fill pallets with product boxes.

    Input   : list of Pedido objects + available Palet objects
    Output  : assignment dict describing which box goes to which pallet cell

    Expected output schema
    ----------------------
    {
        "assignments": [
            {
                "pedido_id": str,
                "palet_id": str,
                "sku": str,
                "quantity_boxes": int,
                "positions": [(x, y, z), ...]   # one per box
            },
            ...
        ],
        "palets_usados": [str],   # palet IDs touched
        "warnings": [str],
    }
    """

    @abstractmethod
    def solve(
        self,
        pedidos: list[Pedido],
        palets: list[Palet],
        **kwargs: Any,
    ) -> dict:
        """Pack *pedidos* onto *palets*. Return assignment dict."""

    def nombre(self) -> str:
        return type(self).__name__


# ── Truck loading solver ──────────────────────────────────────────────────────


class TruckLoadingSolver(ABC):
    """
    Decides how to load pallets into a truck and in what order to unload them.

    Input   : list of Palet objects + target Camion
    Output  : loading plan dict

    Expected output schema
    ----------------------
    {
        "camion_id": str,
        "slots": [
            {
                "palet_id": str,
                "x": int,
                "y": int,
                "descarga_orden": int,   # 1 = first off the truck
            },
            ...
        ],
        "warnings": [str],
        "pct_ocupacion": float,
    }
    """

    @abstractmethod
    def solve(
        self,
        palets: list[Palet],
        camion: Camion,
        **kwargs: Any,
    ) -> dict:
        """Assign *palets* to truck slots. Return loading plan dict."""

    def nombre(self) -> str:
        return type(self).__name__


# ── VRP solver ────────────────────────────────────────────────────────────────


class VRPSolver(ABC):
    """
    Generates delivery routes for a zone (Vehicle Routing Problem).

    Input   : Zona (with matrix pre-built) + available Camion list
    Output  : list of Ruta objects with ordered Parada sequences

    Solvers may use Zona.to_vrp_input() to get a solver-library-friendly dict,
    then write results back as Ruta objects.
    """

    @abstractmethod
    def solve(
        self,
        zona: Zona,
        camiones: list[Camion],
        **kwargs: Any,
    ) -> list[Ruta]:
        """Route stores in *zona* across *camiones*. Return ordered Ruta list."""

    def nombre(self) -> str:
        return type(self).__name__


# ── TSP solver ────────────────────────────────────────────────────────────────


class TSPSolver(ABC):
    """
    Finds the optimal single-vehicle tour for a zone (Travelling Salesman).

    Input   : Zona (with matrix pre-built) + one camion_id
    Output  : a single Ruta with stops ordered by the TSP solution

    Use this when a zone is served by exactly one truck.
    """

    @abstractmethod
    def solve(
        self,
        zona: Zona,
        camion_id: str,
        **kwargs: Any,
    ) -> Ruta:
        """Tour all stores in *zona* with truck *camion_id*. Return one Ruta."""

    def nombre(self) -> str:
        return type(self).__name__


# ── Solver registry (optional convenience) ────────────────────────────────────


class SolverRegistry:
    """
    Lightweight registry that maps solver roles to concrete implementations.

    Usage
    -----
        registry = SolverRegistry()
        registry.register("packing", MyPackingSolver())
        solver = registry.get("packing")
        result = solver.solve(pedidos, palets)

    This lets Ciudad / Zona accept different algorithm families without
    hard-coding any specific implementation.
    """

    def __init__(self) -> None:
        self._solvers: dict[str, object] = {}

    def register(self, role: str, solver: object) -> None:
        self._solvers[role] = solver

    def get(self, role: str) -> object:
        if role not in self._solvers:
            raise KeyError(f"No solver registered for role {role!r}")
        return self._solvers[role]

    def roles(self) -> list[str]:
        return list(self._solvers.keys())

    def __repr__(self) -> str:
        return f"SolverRegistry(roles={self.roles()})"
