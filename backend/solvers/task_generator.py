"""
Expands a list of Pedidos into forklift pickup tasks.

For each pallet that is placed in the warehouse matrix and contains at least
one SKU demanded by a pending Pedido, one TareaPickup is generated.

Assignment strategy
-------------------
* Build a demand map: pedido_id → {sku: remaining_boxes}.
* Iterate placed pallets in warehouse order (x, y ascending).
* Match each pallet to the first Pedido whose demand overlaps the pallet's SKUs.
* Emit one TareaPickup per matched pallet and remove covered boxes from demand.
* Pallets with no relevant SKUs are skipped.
* Pedidos with no matching pallet produce a warning entry (returned alongside tasks).
"""

from __future__ import annotations
import uuid
from typing import Optional

from backend.models.almacen import Almacen
from backend.models.pedido import Pedido
from backend.models.tarea_pickup import TareaPickup


def generar_tareas_pickup(
    pedidos: list[Pedido],
    almacen: Almacen,
    staging_pos: tuple[int, int],
    solo_pendientes: bool = True,
) -> tuple[list[TareaPickup], list[str]]:
    """
    Generate TareaPickup objects for *pedidos* given the current *almacen* state.

    Parameters
    ----------
    pedidos        : orders to fulfil
    almacen        : warehouse with placed pallets
    staging_pos    : global (x, y) of the truck loading dock / staging area
    solo_pendientes: kept for API compatibility; all pedidos are processed

    Returns
    -------
    (tareas, warnings) — warnings list non-empty when coverage is incomplete.
    """
    target_pedidos = list(pedidos)

    # demand[pedido_id][sku] = remaining boxes still needed
    demand: dict[str, dict[str, int]] = {
        p.pedido_id: {l.product.sku: l.quantity_boxes for l in p.lineas}
        for p in target_pedidos
    }

    tareas: list[TareaPickup] = []
    warnings: list[str] = []

    # Track which pedidos received at least one task
    covered_pedidos: set[str] = set()

    # Iterate pallets in a deterministic spatial order
    placed_pallets = sorted(
        (
            (palet_id, pos)
            for palet_id, pos in almacen._palet_posiciones.items()
        ),
        key=lambda item: (item[1][0], item[1][1], item[1][2]),
    )

    for palet_id, (gx, gy, _gz) in placed_pallets:
        palet = almacen.obtener_palet(palet_id)
        palet_skus = {prod.sku for prod in palet.productos}

        if not palet_skus:
            continue

        # Find the first pedido whose remaining demand overlaps with this pallet
        matched_pedido_id: Optional[str] = None
        for pedido_id, sku_demand in demand.items():
            overlap = palet_skus & sku_demand.keys()
            if overlap:
                matched_pedido_id = pedido_id
                # Deduct covered boxes (best-effort; pallet may not fill exact qty)
                for sku in overlap:
                    boxes_on_pallet = sum(
                        1 for prod in palet.productos if prod.sku == sku
                    )
                    sku_demand[sku] = max(0, sku_demand[sku] - boxes_on_pallet)
                # Remove fully satisfied SKUs from remaining demand
                demand[pedido_id] = {k: v for k, v in sku_demand.items() if v > 0}
                break

        if matched_pedido_id is None:
            continue  # pallet not needed by any target pedido

        covered_pedidos.add(matched_pedido_id)
        tareas.append(
            TareaPickup(
                tarea_id=str(uuid.uuid4())[:8],
                palet_id=palet_id,
                pedido_id=matched_pedido_id,
                origin=(gx, gy),
                destino=staging_pos,
            )
        )

    # Warn only when a pedido got zero tasks (no placed pallet covers any of its SKUs)
    for pedido_id in demand:
        if pedido_id not in covered_pedidos:
            missing_skus = list(demand[pedido_id].keys())
            warnings.append(
                f"Pedido {pedido_id!r}: no placed pallets found for {missing_skus}"
            )

    return tareas, warnings
