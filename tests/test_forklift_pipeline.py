"""
Forklift pipeline tests: unit, integration, and end-to-end.

Run with:  pytest tests/test_forklift_pipeline.py -v
"""

from __future__ import annotations
import sys
import os

# Make sure the project root is on the path when running from tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from backend.models.almacen import Almacen
from backend.models.palet import Palet
from backend.models.product import Product
from backend.models.pedido import Pedido, EstadoPedido
from backend.models.product import OrderLine
from backend.models.toro import Toro, EstadoToro
from backend.models.tarea_pickup import TareaPickup, EstadoTarea
from backend.solvers.warehouse_graph import manhattan, build_cost_matrix
from backend.solvers.task_generator import generar_tareas_pickup
from backend.solvers.forklift_optimizer import ORToolsForkliftSolver, ForkliftPlan


# ── Fixtures ──────────────────────────────────────────────────────────────────

STAGING = (0, 0)


def _product(sku: str, weight: float = 1.0) -> Product:
    return Product(sku=sku, name=sku, is_returnable=False, weight_kg_per_box=weight)


def _make_almacen(dim_x: int = 10, dim_y: int = 10, num_toros: int = 2) -> Almacen:
    return Almacen(almacen_id="test-wh", dim_x=dim_x, dim_y=dim_y, dim_z=1, num_toros=num_toros)


def _make_pedido(pedido_id: str, sku: str, qty: int = 5) -> Pedido:
    return Pedido(
        pedido_id=pedido_id,
        tienda_id="tienda-1",
        lineas=[OrderLine(product=_product(sku), quantity_boxes=qty)],
    )


def _place_pallet_with_sku(almacen: Almacen, palet_id: str, sku: str, x: int, y: int) -> Palet:
    """Register a product, create a pallet, put one box in it, place it in the warehouse."""
    try:
        almacen.registrar_producto(_product(sku))
    except ValueError:
        pass  # already registered

    palet = almacen.crear_palet(palet_id=palet_id)
    almacen.asignar_producto_a_palet(sku, palet_id)
    almacen.colocar_palet(palet_id, x, y, 0)
    return palet


# ── Unit: Toro model ──────────────────────────────────────────────────────────


def test_toro_disponible():
    toro = Toro(toro_id="T1", posicion_inicial=(0, 0))
    assert toro.disponible is True
    toro.estado = EstadoToro.EN_TAREA
    assert toro.disponible is False


def test_toro_to_dict():
    toro = Toro(toro_id="T1", posicion_inicial=(3, 4), velocidad_celdas_por_min=8.0)
    d = toro.to_dict()
    assert d["toro_id"] == "T1"
    assert d["posicion_inicial"] == [3, 4]
    assert d["velocidad_celdas_por_min"] == 8.0
    assert d["estado"] == "libre"


# ── Unit: TareaPickup model ───────────────────────────────────────────────────


def test_tarea_pickup_to_dict():
    tarea = TareaPickup(
        tarea_id="ta01",
        palet_id="p01",
        pedido_id="ped01",
        origin=(5, 3),
        destino=(0, 0),
    )
    d = tarea.to_dict()
    assert d["origin"] == [5, 3]
    assert d["destino"] == [0, 0]
    assert d["estado"] == "pendiente"
    assert d["toro_asignado"] is None


# ── Unit: warehouse graph ─────────────────────────────────────────────────────


def test_manhattan_basic():
    assert manhattan((0, 0), (3, 4)) == 7
    assert manhattan((5, 5), (5, 5)) == 0
    assert manhattan((0, 0), (0, 0)) == 0


def test_build_cost_matrix_no_obstacles():
    locs = [(0, 0), (3, 0), (0, 4)]
    almacen = _make_almacen()
    m = build_cost_matrix(locs, almacen)
    assert m[0][1] == 3    # (0,0) → (3,0)
    assert m[0][2] == 4    # (0,0) → (0,4)
    assert m[1][2] == 7    # (3,0) → (0,4)
    assert m[0][0] == 0    # diagonal


def test_build_cost_matrix_with_blocked():
    almacen = _make_almacen(dim_x=5, dim_y=5)
    # Block the direct horizontal path between (0,2) and (4,2)
    blocked = {(1, 2), (2, 2), (3, 2)}
    locs = [(0, 2), (4, 2)]
    m = build_cost_matrix(locs, almacen, blocked=blocked)
    # Direct Manhattan would be 4, but must route around blocked cells
    assert m[0][1] > 4


# ── Unit: task generator ──────────────────────────────────────────────────────


def test_task_generator_basic():
    almacen = _make_almacen()
    _place_pallet_with_sku(almacen, "p01", "SKU-A", x=3, y=3)
    _place_pallet_with_sku(almacen, "p02", "SKU-B", x=7, y=7)

    pedidos = [
        _make_pedido("ped01", "SKU-A"),
        _make_pedido("ped02", "SKU-B"),
    ]

    tareas, warnings = generar_tareas_pickup(pedidos, almacen, staging_pos=STAGING)

    assert len(tareas) == 2
    assert len(warnings) == 0
    origins = {t.origin for t in tareas}
    assert (3, 3) in origins
    assert (7, 7) in origins


def test_task_generator_no_placed_pallets():
    almacen = _make_almacen()
    # Register a pallet in the registry but do NOT place it in the matrix
    almacen.registrar_produto_y_palet = None  # noqa
    palet = almacen.crear_palet("floating")
    try:
        almacen.registrar_producto(_product("SKU-X"))
    except ValueError:
        pass
    almacen.asignar_producto_a_palet("SKU-X", "floating")
    # palet is not placed

    pedidos = [_make_pedido("ped-x", "SKU-X")]
    tareas, warnings = generar_tareas_pickup(pedidos, almacen, staging_pos=STAGING)

    assert len(tareas) == 0
    assert any("SKU-X" in w for w in warnings)


def test_task_generator_skips_non_pending():
    almacen = _make_almacen()
    _place_pallet_with_sku(almacen, "p01", "SKU-A", x=2, y=2)

    pedido = _make_pedido("ped01", "SKU-A")
    pedido.estado = EstadoPedido.ENTREGADO

    tareas, warnings = generar_tareas_pickup([pedido], almacen, staging_pos=STAGING)
    # solo_pendientes=True by default → ENTREGADO is skipped
    assert len(tareas) == 0


def test_task_generator_solo_pendientes_false():
    almacen = _make_almacen()
    _place_pallet_with_sku(almacen, "p01", "SKU-A", x=2, y=2)

    pedido = _make_pedido("ped01", "SKU-A")
    pedido.estado = EstadoPedido.ENTREGADO

    tareas, _ = generar_tareas_pickup(
        [pedido], almacen, staging_pos=STAGING, solo_pendientes=False
    )
    assert len(tareas) == 1


# ── Integration: optimizer (greedy path, no OR-Tools required) ────────────────


def _make_scenario(n_tasks: int = 4, n_toros: int = 2):
    # Ensure warehouse is large enough: tasks placed at (i+1, i+1), need dim > n_tasks
    wh_dim = max(10, n_tasks + 2)
    almacen = _make_almacen(dim_x=wh_dim, dim_y=wh_dim)
    tareas = []
    for i in range(n_tasks):
        sku = f"SKU-{i}"
        try:
            almacen.registrar_producto(_product(sku))
        except ValueError:
            pass
        palet_id = f"p{i:02d}"
        palet = almacen.crear_palet(palet_id)
        almacen.asignar_producto_a_palet(sku, palet_id)
        x, y = i + 1, i + 1
        almacen.colocar_palet(palet_id, x, y, 0)
        tareas.append(
            TareaPickup(
                tarea_id=f"ta{i:02d}",
                palet_id=palet_id,
                pedido_id=f"ped{i:02d}",
                origin=(x, y),
                destino=STAGING,
            )
        )
    toros = [
        Toro(toro_id=f"T{j}", posicion_inicial=(0, j))
        for j in range(n_toros)
    ]
    return tareas, toros, almacen


def test_optimizer_assigns_all_tasks():
    tareas, toros, almacen = _make_scenario(n_tasks=4, n_toros=2)
    solver = ORToolsForkliftSolver(time_limit_seconds=2)
    plan = solver.solve(tareas, toros, almacen)

    assert isinstance(plan, ForkliftPlan)
    assert len(plan.tareas_asignadas) == 4
    assert all(t.tarea.toro_asignado is not None for t in plan.tareas_asignadas)


def test_optimizer_all_tasks_assigned_to_known_toros():
    tareas, toros, almacen = _make_scenario(n_tasks=6, n_toros=3)
    solver = ORToolsForkliftSolver(time_limit_seconds=2)
    plan = solver.solve(tareas, toros, almacen)

    known_toro_ids = {t.toro_id for t in toros}
    for assigned in plan.tareas_asignadas:
        assert assigned.toro_id in known_toro_ids


def test_optimizer_positive_total_distance():
    tareas, toros, almacen = _make_scenario(n_tasks=3, n_toros=2)
    solver = ORToolsForkliftSolver(time_limit_seconds=2)
    plan = solver.solve(tareas, toros, almacen)
    assert plan.distancia_total > 0


def test_optimizer_empty_tasks():
    _, toros, almacen = _make_scenario(n_tasks=0, n_toros=2)
    solver = ORToolsForkliftSolver()
    plan = solver.solve([], toros, almacen)
    assert plan.tareas_asignadas == []
    assert plan.distancia_total == 0


def test_optimizer_no_toros():
    tareas, _, almacen = _make_scenario(n_tasks=2, n_toros=0)
    solver = ORToolsForkliftSolver()
    plan = solver.solve(tareas, [], almacen)
    assert len(plan.tareas_asignadas) == 0
    assert plan.warnings


# ── End-to-end: Pedido → tasks → Toro assignments → LoadPlan ─────────────────


def test_e2e_pedido_to_load_plan():
    """
    Full pipeline:
      1. Set up warehouse with placed pallets.
      2. Create Pedidos for those pallets.
      3. Generate TareaPickup objects from Pedidos.
      4. Run forklift optimizer to assign tasks to toros.
      5. Convert ForkliftPlan to a truck LoadPlan.
    """
    from backend.solvers.inverse_logistics import plan_returnables
    from backend.solvers.load_optimizer import load_sequence_from_forklift_plan

    almacen = _make_almacen(dim_x=20, dim_y=20, num_toros=3)
    skus = ["BEER-330", "BEER-500", "CIDER-440"]

    # Register products
    for sku in skus:
        almacen.registrar_producto(_product(sku, weight=0.5))

    # Place pallets at various positions
    positions = [(4, 2), (8, 5), (12, 3), (3, 9), (15, 7)]
    for idx, (sku, pos) in enumerate(zip(skus * 2, positions)):
        pid = f"palet-{idx:02d}"
        palet = almacen.crear_palet(pid)
        almacen.asignar_producto_a_palet(sku, pid)
        almacen.colocar_palet(pid, pos[0], pos[1], 0)

    # Create one Pedido per placed pallet
    pedidos = [
        Pedido(
            pedido_id=f"ped-{idx:02d}",
            tienda_id="tienda-bcn",
            lineas=[OrderLine(product=_product(sku, 0.5), quantity_boxes=1)],
        )
        for idx, (sku, _) in enumerate(zip(skus * 2, positions))
    ]

    # Step 1 – generate tasks
    tareas, gen_warnings = generar_tareas_pickup(pedidos, almacen, staging_pos=STAGING)
    assert len(tareas) > 0, f"Expected tasks; warnings: {gen_warnings}"

    # Step 2 – assign toros
    toros = [Toro(toro_id=f"TORO-{i}", posicion_inicial=(0, i)) for i in range(3)]
    solver = ORToolsForkliftSolver(time_limit_seconds=3)
    forklift_plan = solver.solve(tareas, toros, almacen)

    assert len(forklift_plan.tareas_asignadas) == len(tareas)
    assert forklift_plan.distancia_total > 0

    # Step 3 – derive load plan (use a dummy returnables plan with no reservations)
    dummy_clients = []
    returnables_plan = plan_returnables(dummy_clients)
    load_plan = load_sequence_from_forklift_plan(
        forklift_plan=forklift_plan,
        route_id="route-bcn-001",
        returnables_plan=returnables_plan,
    )

    assert load_plan.route_id == "route-bcn-001"
    delivery_assignments = [a for a in load_plan.assignments if not a.is_returnable_buffer]
    assert len(delivery_assignments) == len(tareas)
    assert load_plan.utilization_pct >= 0


def test_forklift_plan_to_dict_shape():
    tareas, toros, almacen = _make_scenario(n_tasks=3, n_toros=2)
    solver = ORToolsForkliftSolver(time_limit_seconds=2)
    plan = solver.solve(tareas, toros, almacen)
    d = plan.to_dict()

    assert "distancia_total_celdas" in d
    assert "tareas_asignadas" in d
    assert "rutas_por_toro" in d
    assert "warnings" in d
    assert "solver_used" in d
    for item in d["tareas_asignadas"]:
        assert "toro_id" in item
        assert "secuencia" in item
        assert "origin" in item
        assert "destino" in item
