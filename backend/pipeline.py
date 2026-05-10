"""
Delivery pipeline — loading → zoning → routing + palletizing → JSON output.

Writes one JSON file per route; each file is consumed by the delivery-man app.

Usage (CLI):
    python -m backend.pipeline [zona_id] [--output DIR] [--google]
"""
from __future__ import annotations

import json
import sys
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


def _tipo_envase(product: dict) -> str:
    """Return 'barril' for barrel products, 'caja' for everything else."""
    if product.get("tipo", "").lower() == "barril":
        return "barril"
    if product.get("sku", "").upper().startswith("BAR"):
        return "barril"
    return "caja"


# ── format ────────────────────────────────────────────────────────────────────


def _format_route(route_result: dict) -> dict:
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
                    product = linea["product"]
                    productos.append(
                        {
                            "nombre": product["name"],
                            "sku": product["sku"],
                            "cantidad_cajas": linea["quantity_boxes"],
                            "tipo_envase": _tipo_envase(product),
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


# ── public API ────────────────────────────────────────────────────────────────


def export_routes_json(
    zona_id: str,
    output_dir: Path | str = Path("output/routes"),
    *,
    usar_google: bool = False,
    cajas_por_palet: int = 60,
    distancia_max: Optional[float] = None,
) -> list[dict]:
    """
    Run the full pipeline for *zona_id* and write one JSON file per route.

    Returns a list of dicts, each with {"path": Path, "route": dict}.
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

    written: list[dict] = []
    for route_result in result["routes"]:
        route_json = _format_route(route_result)
        ruta_id = route_json["ruta_id"]
        path = output_dir / f"{zona_id}_{ruta_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(route_json, f, ensure_ascii=False, indent=2)
        written.append({"path": path, "route": route_json})

    return written


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
    print()

    results = export_routes_json(
        args.zona_id,
        output_dir=args.output,
        usar_google=args.google,
    )

    print(f"{len(results)} route(s) written:")
    for r in results:
        route = r["route"]
        path = r["path"]
        num_stops = len(route["paradas"])
        print(
            f"  {path.name}"
            f"  |  {route['tipo_camion']}"
            f"  |  {route['num_palets']} palets"
            f"  |  {num_stops} paradas"
        )
