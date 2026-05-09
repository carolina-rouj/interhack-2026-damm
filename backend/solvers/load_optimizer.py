from __future__ import annotations
from typing import TYPE_CHECKING

from backend.models.truck import LoadPlan, PalletAssignment, Side, build_truck_slots
from backend.solvers.inverse_logistics import ReturnablesPlan

if TYPE_CHECKING:
    from backend.solvers.forklift_optimizer import ForkliftPlan


def optimize_load(
    route_id: str,
    delivery_sequence: list,   # list of (client_id, client_name)
    orders: dict,              # client_id -> Order
    returnables_plan: ReturnablesPlan,
) -> LoadPlan:
    all_slots = build_truck_slots()
    reserved_ids = set(returnables_plan.reserved_slot_ids)

    # Slots available for deliveries, ordered rear-to-front (row 1 first)
    delivery_slots = [s for s in sorted(all_slots, key=lambda s: (s.row, s.col))
                      if s.slot_id not in reserved_ids]

    assignments = []
    warnings = []

    slot_idx = 0
    remaining_in_slot = 60  # boxes per pallet

    for position, (client_id, client_name) in enumerate(delivery_sequence):
        order = orders.get(client_id)
        if order is None:
            continue
        boxes_needed = order.total_boxes

        while boxes_needed > 0:
            if remaining_in_slot == 0:
                slot_idx += 1
                remaining_in_slot = 60

            if slot_idx >= len(delivery_slots):
                warnings.append(
                    f"OVERLOAD: No hay suficiente espacio para {client_name}. "
                    f"Faltan {boxes_needed} cajas sin asignar."
                )
                break

            allocate = min(boxes_needed, remaining_in_slot)
            assignments.append(
                PalletAssignment(
                    slot=delivery_slots[slot_idx],
                    client_id=client_id,
                    client_name=client_name,
                    boxes=allocate,
                    is_returnable_buffer=False,
                    delivery_position=position + 1,
                )
            )
            boxes_needed -= allocate
            remaining_in_slot -= allocate

    # Fill returnable buffer slots
    for slot in all_slots:
        if slot.slot_id in reserved_ids:
            assignments.append(
                PalletAssignment(
                    slot=slot,
                    client_id=None,
                    client_name="Retornables",
                    boxes=0,
                    is_returnable_buffer=True,
                    delivery_position=0,
                )
            )

    # Validate LIFO: first-delivery clients should be in rear slots (low row number)
    warnings.extend(_validate_lifo(assignments))

    return LoadPlan(
        route_id=route_id,
        assignments=assignments,
        returnable_slots=list(reserved_ids),
        warnings=warnings,
    )


def _validate_lifo(assignments: list) -> list:
    warnings = []
    delivery_items = [a for a in assignments if not a.is_returnable_buffer]

    # group by delivery_position -> max row used
    pos_to_rows: dict = {}
    for a in delivery_items:
        pos = a.delivery_position
        pos_to_rows.setdefault(pos, []).append(a.slot.row)

    # Earlier positions should have smaller (more rear) rows
    sorted_positions = sorted(pos_to_rows.keys())
    for i, pos in enumerate(sorted_positions[:-1]):
        max_row_here = max(pos_to_rows[pos])
        next_pos = sorted_positions[i + 1]
        min_row_next = min(pos_to_rows[next_pos])

        if max_row_here > min_row_next:
            # Check if conflicting slot has lona access (mitigating)
            conflicting = [
                a for a in delivery_items
                if a.delivery_position == next_pos and a.slot.row < max_row_here
            ]
            for a in conflicting:
                has_lona = any(s in (Side.LEFT, Side.RIGHT) for s in a.slot.accessible_from)
                level = "AVISO" if has_lona else "CONFLICTO LIFO"
                warnings.append(
                    f"{level}: Parada {next_pos} en palé P{a.slot.slot_id} "
                    f"(fila {a.slot.row}) está delante de parada {pos} "
                    f"(fila {max_row_here}). "
                    + ("Accesible por lona lateral." if has_lona else "Difícil acceso.")
                )

    return warnings


# ── Forklift-order adapter ────────────────────────────────────────────────────


def load_sequence_from_forklift_plan(
    forklift_plan: ForkliftPlan,
    route_id: str,
    returnables_plan: ReturnablesPlan,
) -> LoadPlan:
    """
    Derive a truck LoadPlan from the ordered pickup sequence produced by the
    forklift optimizer.

    Pallets arrive at the truck dock in the order they are listed in
    *forklift_plan.ordered_pickups()*.  We assign them to truck slots
    rear-to-front (LIFO-safe for delivery) while reserving returnable buffers
    as specified by *returnables_plan*.

    Each TareaAsignada contributes one pallet slot; the delivery_position is
    derived from the task's secuencia so that LIFO validation still applies.
    """
    all_slots = build_truck_slots()
    reserved_ids = set(returnables_plan.reserved_slot_ids)
    delivery_slots = [
        s for s in sorted(all_slots, key=lambda s: (s.row, s.col))
        if s.slot_id not in reserved_ids
    ]

    assignments = []
    warnings: list[str] = []

    for slot_idx, assigned_task in enumerate(forklift_plan.ordered_pickups()):
        if slot_idx >= len(delivery_slots):
            warnings.append(
                f"OVERLOAD: truck full; pallet {assigned_task.tarea.palet_id!r} "
                f"(pedido {assigned_task.tarea.pedido_id!r}) could not be loaded."
            )
            continue
        assignments.append(
            PalletAssignment(
                slot=delivery_slots[slot_idx],
                client_id=assigned_task.tarea.pedido_id,
                client_name=f"palet:{assigned_task.tarea.palet_id}",
                boxes=0,   # box-level count resolved upstream by packing solver
                is_returnable_buffer=False,
                delivery_position=assigned_task.secuencia,
            )
        )

    for slot in all_slots:
        if slot.slot_id in reserved_ids:
            assignments.append(
                PalletAssignment(
                    slot=slot,
                    client_id=None,
                    client_name="Retornables",
                    boxes=0,
                    is_returnable_buffer=True,
                    delivery_position=0,
                )
            )

    warnings.extend(_validate_lifo(assignments))

    return LoadPlan(
        route_id=route_id,
        assignments=assignments,
        returnable_slots=list(reserved_ids),
        warnings=warnings,
    )
