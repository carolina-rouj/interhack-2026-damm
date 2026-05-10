"""
Demo runner: load a real zone, cluster stores, then print the paradas.

Usage:
    python3 -m backend.data.run_demo
    python3 backend/data/run_demo.py
"""
from __future__ import annotations
import sys
from pathlib import Path


# Allow direct execution with `python3 backend/data/run_demo.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data.loader import load_zona
from backend.models.zona import TipoMatriz

ZONA_ID = "granollers-center-01"
CAJAS_POR_PALET = 60


def main() -> None:
    data = load_zona(ZONA_ID)
    zona = data["zona"]

    print(f"\n=== Zona: {zona.nombre} ({zona.zona_id}) ===")
    print(f"Tiendas con pedidos: {len(zona.tiendas)}")
    total_cajas = sum(t.num_cajas_total for t in zona.tiendas)
    print(f"Total cajas: {total_cajas}")

    print("Cargando matriz de distancias…")
    tipo = zona.cargar_mejor_matriz()
    unit = "coste 1-10 (Google Maps)" if tipo == TipoMatriz.GOOGLE else "grados Euclídeos (fallback)"
    print(f"  → {tipo.value}  |  unidades: {unit}")

    paradas = zona.agrupar_tiendas(cajas_por_palet=CAJAS_POR_PALET)

    print(f"\n--- Paradas ({len(paradas)}) ---")
    for p in paradas:
        cajas = sum(t.num_cajas_total for t in p.tiendas)
        names = ", ".join(
            (t.nombre + (" <- medoid" if t.tienda_id == p.representante_id else ""))
            for t in p.tiendas
        )
        print(f"  [{p.parada_id}] {cajas} cajas | {names}")


if __name__ == "__main__":
    main()
