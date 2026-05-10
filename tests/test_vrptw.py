"""
VRPTW solver sanity tests.

Run with:  pytest tests/test_vrptw.py -v
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from backend.models.tienda import Tienda
from backend.models.pedido import Pedido
from backend.models.product import Product, OrderLine
from backend.models.ruta import Parada, Ruta
from backend.models.zona import Zona, TipoMatriz
from backend.solvers.vrptw_solver import ORToolsVRPTWSolver
from backend.solvers.palletizer import palletize_route, simulate_returnables


# ── helpers ───────────────────────────────────────────────────────────────────

def _product(sku: str = "ED33") -> Product:
    return Product(sku=sku, name=sku, is_returnable=False, weight_kg_per_box=0.5)


def _tienda(tid: str, lat: float, lon: float, boxes: int = 10,
            inicio: int = 0, fin: int = 1439,
            returnables: int = 0) -> Tienda:
    t = Tienda(tienda_id=tid, nombre=tid, x=lat, y=lon,
               horario_inicio_min=inicio, horario_fin_min=fin)
    if boxes > 0:
        pedido = Pedido(
            pedido_id=f"p-{tid}",
            tienda_id=tid,
            lineas=[OrderLine(product=_product(), quantity_boxes=boxes)],
            es_retornable=returnables > 0,
            num_envases_recogida=returnables,
        )
        t.añadir_pedido(pedido)
    return t


def _parada(pid: str, tiendas: list[Tienda], orden: int = 0) -> Parada:
    rep = tiendas[0]
    return Parada(
        parada_id=pid,
        orden=orden,
        tiendas=tiendas,
        representante_id=rep.tienda_id,
    )


def _zone_with_paradas(*tiendas_per_stop: list[Tienda]) -> tuple[Zona, list[Parada]]:
    all_tiendas = [t for group in tiendas_per_stop for t in group]
    zona = Zona(zona_id="test", nombre="Test Zone")
    for t in all_tiendas:
        zona.añadir_tienda(t)
    zona.generar_matriz(TipoMatriz.EUCLIDEA)

    paradas = [
        _parada(f"p-{i}", list(group), i)
        for i, group in enumerate(tiendas_per_stop)
    ]
    return zona, paradas


# ── VRPTW tests ───────────────────────────────────────────────────────────────

def test_all_stops_assigned():
    """Every parada must appear in exactly one returned Ruta."""
    t1 = _tienda("T1", 41.60, 2.28, boxes=20)
    t2 = _tienda("T2", 41.61, 2.29, boxes=20)
    t3 = _tienda("T3", 41.62, 2.30, boxes=20)
    zona, paradas = _zone_with_paradas([t1], [t2], [t3])

    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas,
                         depot_lat=41.39, depot_lon=2.16)

    assigned_ids = [p.parada_id for r in rutas for p in r.paradas]
    assert sorted(assigned_ids) == sorted(p.parada_id for p in paradas)
    assert len(assigned_ids) == len(set(assigned_ids)), "No parada assigned twice"


def test_arrivals_within_windows():
    """Solver must schedule arrivals inside each stop's time window."""
    t1 = _tienda("T1", 41.60, 2.28, boxes=10, inicio=540, fin=1200)  # 09:00–20:00
    t2 = _tienda("T2", 41.61, 2.29, boxes=10, inicio=600, fin=1200)  # 10:00–20:00
    zona, paradas = _zone_with_paradas([t1], [t2])

    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas,
                         depot_lat=41.39, depot_lon=2.16, start_min=480)

    for ruta in rutas:
        for parada in ruta.paradas:
            if parada.llegada_min is not None:
                assert parada.llegada_min >= parada.horario_inicio_min, (
                    f"Parada {parada.parada_id} arrived before window open"
                )
                assert parada.llegada_min <= parada.horario_fin_min, (
                    f"Parada {parada.parada_id} arrived after window close"
                )


def test_multiple_trucks_when_capacity_exceeded():
    """When total demand exceeds one truck's capacity, multiple trucks are used."""
    # CamionGrande holds 8 pallets × 60 = 480 boxes
    # 5 stops × 120 boxes = 600 boxes → needs 2+ trucks
    tiendas = [_tienda(f"T{i}", 41.60 + i * 0.01, 2.28, boxes=120) for i in range(5)]
    zona, paradas = _zone_with_paradas(*[[t] for t in tiendas])

    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas,
                         depot_lat=41.39, depot_lon=2.16)

    assert len(rutas) >= 2, "Should need more than one truck for 600 boxes"
    # All stops covered
    all_ids = [p.parada_id for r in rutas for p in r.paradas]
    assert sorted(all_ids) == sorted(p.parada_id for p in paradas)


def test_empty_paradas_returns_empty():
    zona = Zona(zona_id="z", nombre="empty")
    zona.generar_matriz(TipoMatriz.EUCLIDEA)
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=[])
    assert rutas == []


def test_single_stop():
    """A zone with one stop produces exactly one route."""
    t = _tienda("T1", 41.60, 2.28, boxes=30)
    zona, paradas = _zone_with_paradas([t])

    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas,
                         depot_lat=41.39, depot_lon=2.16)

    assert len(rutas) == 1
    assert len(rutas[0].paradas) == 1


# ── Palletizer tests ──────────────────────────────────────────────────────────

def test_palletize_single_stop():
    """One stop with 60 boxes fills exactly one pallet."""
    t = _tienda("T1", 41.60, 2.28, boxes=60)
    zona, paradas = _zone_with_paradas([t])
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas, depot_lat=41.39, depot_lon=2.16)

    plan = palletize_route(rutas[0], boxes_per_pallet=60)
    assert plan.num_palets == 1
    assert plan.palets[0].ocupacion == 60


def test_palletize_cross_stop_mixing():
    """Palletization uses ceil(route_boxes / 60) pallets regardless of routing."""
    import math
    t1 = _tienda("T1", 41.60, 2.28, boxes=40)
    t2 = _tienda("T2", 41.61, 2.29, boxes=40)
    zona, paradas = _zone_with_paradas([t1], [t2])
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas, depot_lat=41.39, depot_lon=2.16)

    for ruta in rutas:
        plan = palletize_route(ruta, boxes_per_pallet=60)
        boxes = sum(p.num_cajas_total for p in ruta.paradas)
        assert sum(pal.ocupacion for pal in plan.palets) == boxes
        assert plan.num_palets == math.ceil(boxes / 60)


def test_returnables_fit_in_freed_space():
    """After delivering, returnables should fit in freed pallet cells."""
    t1 = _tienda("T1", 41.60, 2.28, boxes=30, returnables=20)
    t2 = _tienda("T2", 41.61, 2.29, boxes=30, returnables=20)
    zona, paradas = _zone_with_paradas([t1], [t2])
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(zona, [], paradas=paradas, depot_lat=41.39, depot_lon=2.16)

    plan = palletize_route(rutas[0], boxes_per_pallet=60)
    warnings = simulate_returnables(rutas[0], plan, boxes_per_pallet=60)
    # 60 boxes on 1 pallet (exactly full), freed 30 at first stop > 20 returnables → ok
    assert warnings == [], f"Unexpected overflow: {warnings}"
