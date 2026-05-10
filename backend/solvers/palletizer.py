"""
Route palletization, returnables simulation, and truck-slot loading plan.

Three public functions:
    palletize_route(ruta, boxes_per_pallet) -> RouteLoadPlan
    simulate_returnables(ruta, plan, boxes_per_pallet) -> list[str]
    plan_truck_loading(ruta, plan, camion) -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from backend.models.palet import Palet
from backend.models.ruta import Parada, Ruta
from backend.models.truck import Camion


# ── result types ──────────────────────────────────────────────────────────────

@dataclass
class StopPalletSlice:
    """Records how many boxes from one stop went onto one pallet."""
    parada_id: str
    palet_id: str
    boxes: int


@dataclass
class RouteLoadPlan:
    """Palletization result for one Ruta."""
    ruta_id: str
    palets: list[Palet]
    slices: list[StopPalletSlice]
    warnings: list[str] = field(default_factory=list)

    @property
    def num_palets(self) -> int:
        return len(self.palets)

    def palets_for_stop(self, parada_id: str) -> list[str]:
        return list(dict.fromkeys(
            s.palet_id for s in self.slices if s.parada_id == parada_id
        ))

    def to_dict(self) -> dict:
        return {
            "ruta_id": self.ruta_id,
            "num_palets": self.num_palets,
            "palets": [p.stats() for p in self.palets],
            "slices": [
                {"parada_id": s.parada_id, "palet_id": s.palet_id, "boxes": s.boxes}
                for s in self.slices
            ],
            "warnings": self.warnings,
        }


# ── palletize_route ───────────────────────────────────────────────────────────

def palletize_route(ruta: Ruta, boxes_per_pallet: int = 60) -> RouteLoadPlan:
    """
    Assign each stop's delivery boxes to pallets, allowing cross-stop mixing.

    Algorithm: process stops in delivery order; for each stop, fill the current
    open pallet before opening a new one. This minimises the total number of
    pallets while naturally mixing adjacent stops on shared pallets.

    Populates Parada.palets_entregados and Parada.cajas_entregadas in place.
    """
    palets: list[Palet] = []
    slices: list[StopPalletSlice] = []
    warnings: list[str] = []
    active: Optional[Palet] = None

    for parada in ruta.paradas:
        # Build flat product list for this stop (preserves sku traceability)
        products = []
        for tienda in parada.tiendas:
            for pedido in tienda.pedidos:
                for linea in pedido.lineas:
                    products.extend([linea.product] * linea.quantity_boxes)

        if not products:
            continue

        remaining = list(products)
        while remaining:
            if active is None or active.esta_lleno:
                active = Palet(capacidad_max=boxes_per_pallet)
                palets.append(active)

            to_fill = min(len(remaining), active.disponible)
            for p in remaining[:to_fill]:
                active.add_product(p)

            slices.append(StopPalletSlice(
                parada_id=parada.parada_id,
                palet_id=active.palet_id,
                boxes=to_fill,
            ))
            remaining = remaining[to_fill:]

        parada.palets_entregados = list(dict.fromkeys(
            s.palet_id for s in slices if s.parada_id == parada.parada_id
        ))
        parada.cajas_entregadas = parada.num_cajas_total

    return RouteLoadPlan(
        ruta_id=ruta.ruta_id,
        palets=palets,
        slices=slices,
        warnings=warnings,
    )


# ── simulate_returnables ──────────────────────────────────────────────────────

def simulate_returnables(
    ruta: Ruta,
    plan: RouteLoadPlan,
    boxes_per_pallet: int = 60,
) -> list[str]:
    """
    Simulate returnables being collected as deliveries free up pallet space.

    At each stop: space freed = boxes delivered there.
    Returnables from that stop are placed into that freed space.
    If returnables exceed the freed space at any point, emit a warning.

    Populates Parada.cajas_recogidas in place.
    Returns a list of overflow warnings.
    """
    warnings: list[str] = []
    total_boxes = sum(p.num_cajas_total for p in ruta.paradas)
    total_capacity = len(plan.palets) * boxes_per_pallet
    free = total_capacity - total_boxes  # initial empty space (tail of last pallet)

    cumulative_freed = 0
    cumulative_returned = 0

    for parada in ruta.paradas:
        cumulative_freed += parada.num_cajas_total
        returnables = sum(t.num_envases_retorno for t in parada.tiendas)
        cumulative_returned += returnables

        available = free + cumulative_freed - cumulative_returned
        if available < 0:
            overflow = -available
            warnings.append(
                f"Stop {parada.parada_id}: {returnables} returnables "
                f"but only {free + cumulative_freed - (cumulative_returned - returnables)} "
                f"free cells. Overflow: {overflow} boxes. "
                "Consider a larger truck or fewer pallets."
            )

        parada.cajas_recogidas = returnables

    return warnings


# ── plan_truck_loading ────────────────────────────────────────────────────────

def plan_truck_loading(
    ruta: Ruta,
    plan: RouteLoadPlan,
    camion: Camion,
) -> dict:
    """
    Place pallets into truck slots.

    Pallets needed by later stops are loaded deeper (near the cab) so that
    pallets for the first stop are closest to the rear door.
    """
    # Determine the last delivery-stop order index for each pallet
    last_stop_order: dict[str, int] = {}
    for parada in ruta.paradas:
        for palet_id in parada.palets_entregados:
            last_stop_order[palet_id] = parada.orden

    # Sort: latest-needed first → deepest (cab side)
    sorted_palets = sorted(
        plan.palets,
        key=lambda p: last_stop_order.get(p.palet_id, 0),
        reverse=True,
    )

    loading: list[dict] = []
    overflow: list[str] = []

    for palet in sorted_palets:
        pos = camion.posicion_libre()
        if pos is None:
            overflow.append(f"Palet {palet.palet_id!r} doesn't fit in {camion.camion_id!r}")
            continue
        camion.cargar_palet(palet, pos[0], pos[1])
        loading.append({
            "palet_id": palet.palet_id,
            "slot_x": pos[0],
            "slot_y": pos[1],
            "last_stop_order": last_stop_order.get(palet.palet_id),
        })

    return {
        "ruta_id": ruta.ruta_id,
        "camion_id": camion.camion_id,
        "pct_ocupacion": camion.porcentaje_ocupacion,
        "slots": loading,
        "warnings": overflow + plan.warnings,
    }
