"""
Zone shop-clustering tests.

Run with:  pytest tests/test_zone_clustering.py -v
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from backend.models.tienda import Tienda
from backend.models.pedido import Pedido
from backend.models.product import Product, OrderLine
from backend.models.zona import Zona, TipoMatriz
from backend.models.ruta import Parada


# ── helpers ───────────────────────────────────────────────────────────────────

def _product(sku: str = "SKU01") -> Product:
    return Product(sku=sku, name=sku, is_returnable=False, weight_kg_per_box=1.0)


def _tienda(tid: str, x: float, y: float, boxes: int = 0) -> Tienda:
    t = Tienda(tienda_id=tid, nombre=tid, x=x, y=y)
    if boxes > 0:
        t.añadir_pedido(Pedido(
            pedido_id=f"p-{tid}",
            tienda_id=tid,
            lineas=[OrderLine(product=_product(), quantity_boxes=boxes)],
        ))
    return t


def _zone(*tiendas: Tienda, tipo: TipoMatriz = TipoMatriz.EUCLIDEA) -> Zona:
    z = Zona(zona_id="z1", nombre="Test")
    for t in tiendas:
        z.añadir_tienda(t)
    z.generar_matriz(tipo)
    return z


# ── Test 1: close shops are grouped ──────────────────────────────────────────

def test_close_shops_grouped():
    """Three nearby shops together fill one pallet; far shop stays alone."""
    # A, B, C at x=0/0.1/0.2 — close.  D at x=100 — far.
    # With pallet=65: A+B+C=60 fits; adding D would be 65 ≤ 65 so we use
    # distancia_max to enforce proximity.
    t_a = _tienda("A", 0.0, 0.0, boxes=20)
    t_b = _tienda("B", 0.1, 0.0, boxes=20)
    t_c = _tienda("C", 0.2, 0.0, boxes=20)
    t_d = _tienda("D", 100.0, 0.0, boxes=5)

    zona = _zone(t_a, t_b, t_c, t_d)
    paradas = zona.agrupar_tiendas(cajas_por_palet=65, distancia_max=1.0)

    assert len(paradas) == 2

    grouped = next(p for p in paradas if p.num_tiendas > 1)
    grouped_ids = {t.tienda_id for t in grouped.tiendas}
    assert {"A", "B", "C"} == grouped_ids

    solo = next(p for p in paradas if p.num_tiendas == 1)
    assert solo.tiendas[0].tienda_id == "D"


# ── Test 2: far shop stays separate ──────────────────────────────────────────

def test_far_shop_stays_separate():
    """A shop far from all others forms its own stop."""
    t1 = _tienda("A", 0.0, 0.0, boxes=10)
    t2 = _tienda("B", 0.1, 0.0, boxes=10)
    t_far = _tienda("FAR", 1000.0, 1000.0, boxes=5)

    zona = _zone(t1, t2, t_far)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60, distancia_max=1.0)

    assert len(paradas) == 2

    far_stop = next(p for p in paradas if any(t.tienda_id == "FAR" for t in p.tiendas))
    assert far_stop.num_tiendas == 1


# ── Test 3: oversized shop is a forced single stop ────────────────────────────

def test_oversized_shop_forced_single():
    """A shop whose demand alone exceeds the pallet cap is never merged."""
    t_big = _tienda("BIG", 0.0, 0.0, boxes=100)
    t_small = _tienda("SMALL", 0.1, 0.0, boxes=5)

    zona = _zone(t_big, t_small)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60)

    big_stop = next(p for p in paradas if any(t.tienda_id == "BIG" for t in p.tiendas))
    assert big_stop.num_tiendas == 1
    assert len(paradas) == 2


# ── Test 4: representative is inside the cluster ──────────────────────────────

def test_representative_is_in_cluster():
    """representante_id must be the tienda_id of a member of the stop."""
    t1 = _tienda("A", 0.0, 0.0, boxes=10)
    t2 = _tienda("B", 0.1, 0.0, boxes=10)
    t3 = _tienda("C", 0.2, 0.0, boxes=10)

    zona = _zone(t1, t2, t3)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60)

    for parada in paradas:
        assert parada.representante_id is not None
        cluster_ids = {t.tienda_id for t in parada.tiendas}
        assert parada.representante_id in cluster_ids


def test_medoid_is_central():
    """The medoid of a collinear cluster is the middle store."""
    # A(0) — B(1) — C(2): B has the smallest sum of distances (1+1=2 vs A:3, C:3)
    t_a = _tienda("A", 0.0, 0.0, boxes=10)
    t_b = _tienda("B", 1.0, 0.0, boxes=10)
    t_c = _tienda("C", 2.0, 0.0, boxes=10)

    zona = _zone(t_a, t_b, t_c)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60)

    assert len(paradas) == 1
    assert paradas[0].representante_id == "B"


# ── Test 5: one-pallet limit is always respected ──────────────────────────────

def test_one_pallet_limit_respected():
    """No cluster ever exceeds cajas_por_palet boxes."""
    shops = [_tienda(str(i), float(i) * 0.1, 0.0, boxes=15) for i in range(6)]
    zona = _zone(*shops)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60)

    for parada in paradas:
        total = sum(t.num_cajas_total for t in parada.tiendas)
        assert total <= 60


def test_exact_pallet_boundary():
    """A cluster that fills the pallet exactly should not absorb the next shop."""
    # Three shops of 20 boxes each fill a 60-box pallet exactly.
    # The fourth shop should start a new cluster.
    shops = [_tienda(str(i), float(i) * 0.1, 0.0, boxes=20) for i in range(4)]
    zona = _zone(*shops)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60)

    assert len(paradas) == 2
    totals = sorted(sum(t.num_cajas_total for t in p.tiendas) for p in paradas)
    assert totals == [20, 60]


# ── Test 6: deterministic output with same matrix ─────────────────────────────

def test_deterministic_output():
    """Calling agrupar_tiendas twice on the same zone yields identical results."""
    t1 = _tienda("A", 0.0, 0.0, boxes=10)
    t2 = _tienda("B", 0.5, 0.0, boxes=10)
    t3 = _tienda("C", 10.0, 0.0, boxes=10)

    def run():
        zona = _zone(t1, t2, t3)
        return [
            (p.parada_id, p.representante_id, sorted(t.tienda_id for t in p.tiendas))
            for p in zona.agrupar_tiendas(60)
        ]

    assert run() == run()


# ── Test 7: end-to-end — Parada objects ready for route planning ──────────────

def test_end_to_end_parada_output():
    """agrupar_tiendas returns valid Parada objects covering all stores."""
    t1 = _tienda("A", 0.0, 0.0, boxes=20)
    t2 = _tienda("B", 0.2, 0.0, boxes=20)
    t3 = _tienda("C", 100.0, 0.0, boxes=20)

    zona = _zone(t1, t2, t3)
    paradas = zona.agrupar_tiendas(cajas_por_palet=60, distancia_max=1.0)

    # Every returned object is a proper Parada
    for i, parada in enumerate(paradas):
        assert isinstance(parada, Parada)
        assert parada.orden == i
        assert parada.num_tiendas >= 1
        assert parada.representante_id is not None

    # Every store appears exactly once
    all_ids = [t.tienda_id for p in paradas for t in p.tiendas]
    assert sorted(all_ids) == ["A", "B", "C"]
    assert len(all_ids) == len(set(all_ids))  # no duplicates


# ── Test 8: matrix not built — clear error ────────────────────────────────────

def test_requires_matrix_before_clustering():
    """agrupar_tiendas raises RuntimeError if no matrix has been generated."""
    zona = Zona(zona_id="z", nombre="no-matrix")
    zona.añadir_tienda(_tienda("A", 0.0, 0.0, boxes=10))

    with pytest.raises(RuntimeError):
        zona.agrupar_tiendas()


# ── Test 9: empty zone ────────────────────────────────────────────────────────

def test_empty_zone_returns_empty_list():
    zona = Zona(zona_id="z", nombre="empty")
    zona.generar_matriz(TipoMatriz.EUCLIDEA)
    assert zona.agrupar_tiendas() == []
