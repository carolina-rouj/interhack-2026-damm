"""
Delivery pipeline — loading → zoning → routing + palletizing → JSON output.

Writes one JSON file per route; each file is consumed by the delivery-man app.
Also writes a *_summary.json* with aggregated metrics for the whole zone run.

Usage (CLI):
    python -m backend.pipeline [zona_id] [--output DIR] [--google]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


# ── helpers ───────────────────────────────────────────────────────────────────


def _truck_tipo(camion_id: Optional[str]) -> str:
    if not camion_id:
        return "grande"
    for label in ("furgoneta", "mediano", "grande"):
        if camion_id.startswith(label):
            return label
    return "grande"


def _tipo_envase(sku: str, skus: dict) -> str:
    """Return 'barril' for barrel products, 'caja' for everything else."""
    product = skus.get(sku)
    if product is not None and getattr(product, "tipo", "").lower() == "barril":
        return "barril"
    if sku.upper().startswith("BAR"):
        return "barril"
    return "caja"


# ── route formatter ───────────────────────────────────────────────────────────


def _format_route(route_result: dict, skus: dict) -> dict:
    """
    Transform one orchestrator route_result into the frontend route schema.

    Schema
    ------
    {
      "ruta_id": str,
      "zona_id": str,
      "tipo_camion": "furgoneta" | "mediano" | "grande",
      "num_palets": int,
      "paradas": [
        {
          "orden": int,
          "llegada_min": int | null,
          "coordenadas": { "lat": float, "lon": float },
          "clientes": [
            {
              "nombre": str,
              "total_cajas": int,
              "productos": [
                {
                  "nombre": str,
                  "sku": str,
                  "cantidad_cajas": int,
                  "tipo_envase": "caja" | "barril"
                }
              ]
            }
          ]
        }
      ]
    }
    """
    ruta = route_result["ruta"]

    num_palets = sum(len(p["palets_entregados"]) for p in ruta["paradas"])

    paradas_out: list[dict] = []
    for parada in ruta["paradas"]:
        tiendas = parada["tiendas"]
        rep_id = parada.get("representante_id")

        rep = next((t for t in tiendas if t["tienda_id"] == rep_id), None)
        if rep is None and tiendas:
            rep = tiendas[0]

        coordenadas = (
            {"lat": rep["x"], "lon": rep["y"]} if rep else {"lat": None, "lon": None}
        )

        clientes: list[dict] = []
        for tienda in tiendas:
            productos: list[dict] = []
            for pedido in tienda.get("pedidos", []):
                for linea in pedido.get("lineas", []):
                    sku = linea["sku"]
                    qty = linea["quantity_boxes"]
                    product = skus.get(sku)
                    nombre = product.name if product else sku
                    productos.append(
                        {
                            "nombre": nombre,
                            "sku": sku,
                            "cantidad_cajas": qty,
                            "tipo_envase": _tipo_envase(sku, skus),
                        }
                    )

            clientes.append(
                {
                    "nombre": tienda["nombre"],
                    "total_cajas": tienda["num_cajas_total"],
                    "productos": productos,
                }
            )

        paradas_out.append(
            {
                "orden": parada["orden"],
                "llegada_min": parada.get("llegada_min"),
                "coordenadas": coordenadas,
                "clientes": clientes,
            }
        )

    return {
        "ruta_id": ruta["ruta_id"],
        "zona_id": ruta["zona_id"],
        "tipo_camion": _truck_tipo(ruta.get("camion_id")),
        "num_palets": num_palets,
        "paradas": paradas_out,
    }


# ── metrics ───────────────────────────────────────────────────────────────────


def _compute_metrics(
    zona_id: str,
    route_results: list[dict],
    formatted_routes: list[dict],
    skus: dict,
) -> dict:
    """Aggregate metrics across all routes for one zone solve."""
    trucks: dict[str, int] = {}
    total_palets = 0
    total_cost = 0.0
    total_cajas_entregadas = 0
    total_cajas_recogidas = 0
    por_sku: dict[str, dict] = {}

    for raw, fmt in zip(route_results, formatted_routes):
        ruta = raw["ruta"]

        # trucks
        tipo = fmt["tipo_camion"]
        trucks[tipo] = trucks.get(tipo, 0) + 1

        # pallets
        total_palets += fmt["num_palets"]

        # cost
        total_cost += ruta.get("coste_total") or 0.0

        # returnables from raw parada data
        for parada in ruta["paradas"]:
            total_cajas_recogidas += parada.get("cajas_recogidas", 0)
            total_cajas_entregadas += parada.get("cajas_entregadas", 0)

        # delivered by SKU from formatted route
        for parada in fmt["paradas"]:
            for cliente in parada["clientes"]:
                for producto in cliente["productos"]:
                    sku = producto["sku"]
                    if sku not in por_sku:
                        por_sku[sku] = {
                            "nombre": producto["nombre"],
                            "tipo_envase": producto["tipo_envase"],
                            "total_cajas": 0,
                        }
                    por_sku[sku]["total_cajas"] += producto["cantidad_cajas"]

    return {
        "zona_id": zona_id,
        "num_rutas": len(formatted_routes),
        "trucks": trucks,
        "total_palets": total_palets,
        "coste_total": round(total_cost, 2),
        "total_cajas_entregadas": total_cajas_entregadas,
        "total_cajas_recogidas": total_cajas_recogidas,
        "por_sku": por_sku,
    }


def _print_metrics(metrics: dict) -> None:
    """Print a formatted metrics summary to stdout."""
    sep = "─" * 52
    print(f"\n{sep}")
    print(f"  METRICS — {metrics['zona_id']}")
    print(sep)
    print(f"  Trucks  : {metrics['num_rutas']}  {metrics['trucks']}")
    print(f"  Pallets : {metrics['total_palets']}")
    print(f"  Cost    : {metrics['coste_total']:.2f}")
    print(f"  Boxes delivered  : {metrics['total_cajas_entregadas']}")
    print(f"  Returnables coll.: {metrics['total_cajas_recogidas']}")
    print(f"\n  Breakdown by product:")
    for sku, info in sorted(metrics["por_sku"].items()):
        tag = "🛢" if info["tipo_envase"] == "barril" else "📦"
        print(
            f"    {tag}  {sku:<8} {info['nombre']:<30}  {info['total_cajas']:>4} cajas"
        )
    print(sep)


# ── public API ────────────────────────────────────────────────────────────────


def export_routes_json(
    zona_id: str,
    output_dir: Path | str = Path("output/routes"),
    *,
    usar_google: bool = False,
    cajas_por_palet: int = 60,
    distancia_max: Optional[float] = None,
) -> dict:
    """
    Run the full pipeline for *zona_id*, write one JSON per route plus a
    summary JSON with metrics.

    Returns:
        {
            "routes": [{"path": Path, "route": dict}, ...],
            "metrics": dict,
            "summary_path": Path,
        }
    """
    from backend.solvers.orchestrator import run_pipeline

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_pipeline(
        zona_id,
        usar_google=usar_google,
        cajas_por_palet=cajas_por_palet,
        distancia_max=distancia_max,
    )

    skus = result["skus"]

    # Format and write one JSON per route
    written: list[dict] = []
    formatted_routes: list[dict] = []
    for route_result in result["routes"]:
        route_json = _format_route(route_result, skus)
        formatted_routes.append(route_json)
        ruta_id = route_json["ruta_id"]
        path = output_dir / f"{zona_id}_{ruta_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(route_json, f, ensure_ascii=False, indent=2)
        written.append({"path": path, "route": route_json})

    # Compute and write summary metrics
    metrics = _compute_metrics(zona_id, result["routes"], formatted_routes, skus)
    summary_path = output_dir / f"{zona_id}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    return {"routes": written, "metrics": metrics, "summary_path": summary_path}


# ── CLI ───────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the delivery pipeline and export one JSON per route."
    )
    parser.add_argument(
        "zona_id",
        nargs="?",
        default="granollers-center-01",
        help="Zone ID to solve (default: granollers-center-01)",
    )
    parser.add_argument(
        "--output",
        default="output/routes",
        metavar="DIR",
        help="Directory for output JSON files (default: output/routes)",
    )
    parser.add_argument(
        "--google",
        action="store_true",
        help="Use Google Maps Distance Matrix (requires API key in .env)",
    )
    args = parser.parse_args()

    print(f"Zone    : {args.zona_id}")
    print(f"Output  : {args.output}")
    print(f"Google  : {'yes' if args.google else 'no (Euclidean fallback)'}")

    result = export_routes_json(
        args.zona_id,
        output_dir=args.output,
        usar_google=args.google,
    )

    routes = result["routes"]
    print(f"\n{len(routes)} route file(s) written:")
    for r in routes:
        route = r["route"]
        print(
            f"  {r['path'].name}"
            f"  |  {route['tipo_camion']}"
            f"  |  {route['num_palets']} palets"
            f"  |  {len(route['paradas'])} paradas"
        )
    print(f"  {result['summary_path'].name}  (metrics summary)")

    _print_metrics(result["metrics"])
