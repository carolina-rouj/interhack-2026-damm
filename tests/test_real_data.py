"""
Focused tests for the real-data loader and zone clustering.
"""
from __future__ import annotations

import os
import sys

import pytest

# Make sure the project root is on the path when running from tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.loader import load_zona


ZONA_ID = "granollers-center-01"


@pytest.fixture(scope="module")
def zona_data():
    return load_zona(ZONA_ID)


def test_load_zona_hydrates_and_clusters(zona_data):
    zona = zona_data["zona"]

    assert zona.zona_id == ZONA_ID
    assert len(zona.tiendas) > 0, "Zona must have at least one tienda with pedidos"

    for t in zona.tiendas:
        assert t.pedidos, f"Tienda {t.tienda_id} attached with no pedidos"

    zona.cargar_mejor_matriz()
    paradas_a = zona.agrupar_tiendas(cajas_por_palet=60)
    paradas_b = zona.agrupar_tiendas(cajas_por_palet=60)

    assert [p.parada_id for p in paradas_a] == [p.parada_id for p in paradas_b], (
        "Clustering is not deterministic"
    )

    for p in paradas_a:
        cajas = sum(t.num_cajas_total for t in p.tiendas)
        assert cajas <= 60 or len(p.tiendas) == 1, (
            f"{p.parada_id} exceeds 60 boxes with {len(p.tiendas)} tiendas"
        )
