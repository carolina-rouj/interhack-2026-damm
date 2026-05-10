"""
End-to-end delivery pipeline orchestrator.

run_pipeline(zona_id, **kwargs) -> dict

Pipeline stages
---------------
1. Load zone from JSON
2. Build distance / cost matrix (Google Maps or Euclidean fallback)
3. Schedule-safe store clustering → Parada stops
4. VRPTW routing → Ruta list with arrival times
5. Palletization → RouteLoadPlan per route
6. Returnables simulation → warnings
7. Truck-slot loading plan
"""
from __future__ import annotations

from typing import Optional

from backend.models.truck import CamionFactory, TipoCamion


# Fábrica Damm — default depot
_DEPOT_LAT = 41.3985
_DEPOT_LON = 2.1620


def run_pipeline(
    zona_id: str,
    *,
    usar_google: bool = False,
    cajas_por_palet: int = 60,
    distancia_max: Optional[float] = None,
    depot_lat: float = _DEPOT_LAT,
    depot_lon: float = _DEPOT_LON,
    start_min: int = 480,
    service_time_min: int = 15,
    solver_time_limit_sec: int = 30,
) -> dict:
    """
    Run the full delivery optimisation pipeline for one zone.

    Returns a dict with zone metadata and per-route plans including
    palletization, returnables, and truck loading.
    """
    from backend.data.loader import load_zona
    from backend.models.zona import TipoMatriz
    from backend.solvers.vrptw_solver import ORToolsVRPTWSolver
    from backend.solvers.palletizer import (
        palletize_route,
        simulate_returnables,
        plan_truck_loading,
    )

    # ── 1. Load ───────────────────────────────────────────────────────────
    data = load_zona(zona_id)
    zona = data["zona"]

    # ── 2. Matrix ─────────────────────────────────────────────────────────
    if usar_google:
        tipo = zona.cargar_mejor_matriz()
    else:
        zona.generar_matriz(TipoMatriz.EUCLIDEA)
        tipo = TipoMatriz.EUCLIDEA

    # ── 3. Clustering ─────────────────────────────────────────────────────
    paradas = zona.agrupar_tiendas(
        cajas_por_palet=cajas_por_palet,
        distancia_max=distancia_max,
    )

    # ── 4. VRPTW routing ──────────────────────────────────────────────────
    solver = ORToolsVRPTWSolver()
    rutas = solver.solve(
        zona, [],
        paradas=paradas,
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        start_min=start_min,
        service_time_min=service_time_min,
        solver_time_limit_sec=solver_time_limit_sec,
    )

    # ── 5–7. Per-route palletization + returnables + truck loading ─────────
    route_results: list[dict] = []
    for ruta in rutas:
        load_plan = palletize_route(ruta, cajas_por_palet)
        ret_warnings = simulate_returnables(ruta, load_plan, cajas_por_palet)
        load_plan.warnings.extend(ret_warnings)

        # Infer truck type from the camion_id set by the solver
        camion_tipo = TipoCamion.GRANDE
        if ruta.camion_id:
            for t in TipoCamion:
                if ruta.camion_id.startswith(t.value):
                    camion_tipo = t
                    break

        camion = CamionFactory.crear(camion_tipo, ruta.camion_id or f"truck-{ruta.ruta_id}")
        truck_plan = plan_truck_loading(ruta, load_plan, camion)

        route_results.append({
            "ruta": ruta.to_dict(),
            "load_plan": load_plan.to_dict(),
            "truck_loading": truck_plan,
        })

    return {
        "zona_id": zona_id,
        "zona_nombre": zona.nombre,
        "matriz_tipo": tipo.value,
        "num_paradas_clustering": len(paradas),
        "num_rutas": len(rutas),
        "routes": route_results,
        "skus": data["skus"],
    }
