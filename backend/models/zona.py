from __future__ import annotations
import math
import os
import re
import random
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from dotenv import dotenv_values

from backend.models.tienda import Tienda
from backend.models.pedido import Pedido
from backend.models.ruta import Ruta

if TYPE_CHECKING:
    from backend.models.almacen import Almacen


class TipoMatriz(Enum):
    """Strategy for generating the inter-store cost / distance matrix."""
    EUCLIDEA = "euclidea"       # sqrt((xi-xj)² + (yi-yj)²)
    ALEATORIA = "aleatoria"     # random weights (reproducible via seed)
    PERSONALIZADA = "personalizada"  # provided externally
    GOOGLE = "google"           # driving distances via Google Maps Distance Matrix API


class Zona:
    """
    A delivery zone: a named group of Tiendas served in the same area.

    Solver integration points
    -------------------------
    * generar_matriz()   — build the cost/distance matrix (required before
                           passing the zone to a VRP/TSP solver)
    * to_vrp_input()     — export solver-ready dict (nodes, matrix, demand)
    * solicitar_productos_almacen() — aggregate SKU demand so Almacen can
                           prepare pallets before route assignment

    The zone holds Ruta objects written back by solvers; it never generates
    routes itself.
    """

    def __init__(self, zona_id: str, nombre: str) -> None:
        self.zona_id = zona_id
        self.nombre = nombre
        self.tiendas: list[Tienda] = []
        self.rutas: list[Ruta] = []
        # Adjacency cost matrix; None until generar_matriz() is called
        self._matriz: Optional[list[list[float]]] = None
        self._tipo_matriz: Optional[TipoMatriz] = None

    # ── store management ──────────────────────────────────────────────────

    def añadir_tienda(self, tienda: Tienda) -> None:
        if any(t.tienda_id == tienda.tienda_id for t in self.tiendas):
            raise ValueError(f"Tienda {tienda.tienda_id!r} already in zone {self.zona_id!r}")
        self.tiendas.append(tienda)
        # Invalidate cached matrix when topology changes
        self._matriz = None

    def eliminar_tienda(self, tienda_id: str) -> Tienda:
        for i, t in enumerate(self.tiendas):
            if t.tienda_id == tienda_id:
                self._matriz = None
                return self.tiendas.pop(i)
        raise KeyError(f"Tienda {tienda_id!r} not found in zone {self.zona_id!r}")

    def obtener_tienda(self, tienda_id: str) -> Tienda:
        for t in self.tiendas:
            if t.tienda_id == tienda_id:
                return t
        raise KeyError(f"Tienda {tienda_id!r} not found in zone {self.zona_id!r}")

    @property
    def num_tiendas(self) -> int:
        return len(self.tiendas)

    # ── adjacency / cost matrix ───────────────────────────────────────────

    def generar_matriz(
        self,
        tipo: TipoMatriz = TipoMatriz.EUCLIDEA,
        seed: int = 42,
        simetrica: bool = True,
        min_coste: float = 1.0,
        max_coste: float = 100.0,
    ) -> None:
        """
        Build (or rebuild) the inter-store cost matrix.

        Parameters
        ----------
        tipo       : generation strategy
        seed       : RNG seed for reproducible random matrices
        simetrica  : if True, enforce matrix[i][j] == matrix[j][i]
        min_coste  : lower bound for random costs
        max_coste  : upper bound for random costs
        """
        n = len(self.tiendas)
        if n == 0:
            self._matriz = []
            self._tipo_matriz = tipo
            return

        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
        rng = random.Random(seed)

        if tipo == TipoMatriz.EUCLIDEA:
            for i in range(n):
                for j in range(n):
                    if i != j:
                        matrix[i][j] = self.tiendas[i].distancia_a(self.tiendas[j])

        elif tipo == TipoMatriz.ALEATORIA:
            for i in range(n):
                for j in range(n):
                    if i != j:
                        if simetrica and j < i:
                            matrix[i][j] = matrix[j][i]
                        else:
                            matrix[i][j] = round(rng.uniform(min_coste, max_coste), 2)
        else:
            raise ValueError(
                f"Use tipo=TipoMatriz.PERSONALIZADA and set _matriz directly "
                f"for custom matrices; generar_matriz() only handles "
                f"EUCLIDEA and ALEATORIA."
            )

        if simetrica and tipo != TipoMatriz.ALEATORIA:
            for i in range(n):
                for j in range(i + 1, n):
                    matrix[j][i] = matrix[i][j]

        self._matriz = matrix
        self._tipo_matriz = tipo

    def set_matriz_personalizada(
        self, matrix: list[list[float]], validar: bool = True
    ) -> None:
        """Inject an externally computed cost matrix."""
        n = len(self.tiendas)
        if validar:
            if len(matrix) != n or any(len(row) != n for row in matrix):
                raise ValueError(
                    f"Matrix must be {n}×{n}, got {len(matrix)}×{len(matrix[0]) if matrix else 0}"
                )
        self._matriz = [list(row) for row in matrix]
        self._tipo_matriz = TipoMatriz.PERSONALIZADA

    def _require_matriz(self) -> list[list[float]]:
        if self._matriz is None:
            raise RuntimeError(
                f"Zone {self.zona_id!r}: call generar_matriz() before querying costs"
            )
        return self._matriz

    def coste_entre(self, i: int, j: int) -> float:
        """Cost from store at index *i* to store at index *j*."""
        m = self._require_matriz()
        n = len(self.tiendas)
        if not (0 <= i < n and 0 <= j < n):
            raise IndexError(f"Index ({i},{j}) out of range for {n} stores")
        return m[i][j]

    def coste_entre_tiendas(self, tienda_id_a: str, tienda_id_b: str) -> float:
        """Cost between two stores identified by ID."""
        ids = [t.tienda_id for t in self.tiendas]
        try:
            i, j = ids.index(tienda_id_a), ids.index(tienda_id_b)
        except ValueError as exc:
            raise KeyError(f"Tienda not found in zone: {exc}") from exc
        return self.coste_entre(i, j)

    def validar_conectividad(self) -> bool:
        """Return True if every pair of nodes is reachable (cost > 0 for i≠j)."""
        m = self._require_matriz()
        n = len(self.tiendas)
        return all(
            m[i][j] > 0
            for i in range(n)
            for j in range(n)
            if i != j
        )

    @property
    def matriz(self) -> Optional[list[list[float]]]:
        return self._matriz

    # ── Google distance matrix ────────────────────────────────────────────

    def cargar_matriz_google(
        self,
        script_path: Optional[str] = None,
        node_cmd: str = "node",
        timeout: int = 30,
    ) -> None:
        """
        Build a cost matrix by calling backend/distance/index.js once per store.

        Each cell holds the relative cost (1–10) returned by the script:
        1 = cheapest route from that origin, 10 = most expensive.
        Costs are normalised per origin row across all destinations in that call.
        Diagonal stays 0 (a store has zero cost to reach itself).

        Requires GOOGLE_MAPS_API_KEY in the .env file beside the script.
        Raises RuntimeError / ValueError on script failure or unexpected output.
        """
        n = len(self.tiendas)
        if n == 0:
            self._matriz = []
            self._tipo_matriz = TipoMatriz.GOOGLE
            return

        if script_path is None:
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "distance", "index.js",
            )

        script_dir = os.path.dirname(script_path)

        # Load GOOGLE_MAPS_API_KEY from the project root .env (two levels above backend/models/)
        project_root = Path(__file__).resolve().parents[2]
        env = {**os.environ, **dotenv_values(project_root / ".env")}

        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

        for i, origin in enumerate(self.tiendas):
            dests = [(j, t) for j, t in enumerate(self.tiendas) if j != i]
            if not dests:
                continue  # single store — diagonal stays 0

            args = [node_cmd, script_path, str(origin.x), str(origin.y)]
            for _, dest in dests:
                args += [str(dest.x), str(dest.y)]

            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout,
                cwd=script_dir, env=env,
            )
            if result.stderr:
                print(result.stderr, end="", flush=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"Google distance script failed for tienda {origin.tienda_id!r}:\n"
                    f"{result.stderr.strip()}"
                )

            parsed: list[float] = []
            for line in result.stdout.splitlines():
                m_ok = re.search(r"cost\s+(\d+)/10", line)
                m_err = re.search(r"Route error", line, re.IGNORECASE)
                if m_ok:
                    parsed.append(float(m_ok.group(1)))
                elif m_err:
                    parsed.append(10.0)  # treat unreachable as worst cost

            if len(parsed) != len(dests):
                raise ValueError(
                    f"Expected {len(dests)} cost values for tienda {origin.tienda_id!r}, "
                    f"got {len(parsed)}"
                )

            for k, (j, _) in enumerate(dests):
                matrix[i][j] = parsed[k]

        self._matriz = matrix
        self._tipo_matriz = TipoMatriz.GOOGLE

    def cargar_mejor_matriz(
        self,
        script_path: Optional[str] = None,
        node_cmd: str = "node",
        timeout: int = 30,
    ) -> TipoMatriz:
        """
        Try to build a Google Maps matrix; fall back to Euclidean on any error.
        Returns the TipoMatriz that was actually loaded.
        """
        try:
            self.cargar_matriz_google(
                script_path=script_path, node_cmd=node_cmd, timeout=timeout
            )
            return TipoMatriz.GOOGLE
        except Exception:
            self.generar_matriz(TipoMatriz.EUCLIDEA)
            return TipoMatriz.EUCLIDEA

    # ── shop clustering ───────────────────────────────────────────────────

    def agrupar_tiendas(
        self,
        cajas_por_palet: int = 60,
        distancia_max: Optional[float] = None,
        parada_id_prefix: str = "parada",
    ) -> list:
        """
        Group stores into delivery stops using greedy nearest-neighbour clustering.

        Algorithm
        ---------
        1. Pick the smallest-index unvisited store as the cluster seed.
        2. Sort remaining unvisited stores by (distance_from_seed, index).
        3. Add each in turn while cluster_boxes + store_boxes <= cajas_por_palet
           AND distance_from_seed <= distancia_max (when set).
           Stop growing on the first store that fails either constraint.
        4. Choose the cluster's representative (physical stop point) as the
           medoid — the member with the smallest total distance to all others.
        5. Return one Parada per cluster, representative store first in tiendas[].

        A store whose demand alone exceeds cajas_por_palet becomes a forced
        single-store stop (never merged into a larger cluster).

        Requires a distance matrix to be loaded first.

        Parameters
        ----------
        cajas_por_palet : one-pallet capacity cap (default 60)
        distancia_max   : optional proximity radius in the same units as the
                          distance matrix; stops cluster growth when the next
                          nearest store exceeds this threshold
        parada_id_prefix: prefix for generated Parada IDs
        """
        from backend.models.ruta import Parada

        m = self._require_matriz()
        n = len(self.tiendas)

        if n == 0:
            return []

        unvisited: set[int] = set(range(n))
        paradas: list[Parada] = []
        counter = 0

        while unvisited:
            seed = min(unvisited)
            unvisited.remove(seed)

            seed_demand = self.tiendas[seed].num_cajas_total

            # Forced single stop: store alone exceeds pallet capacity
            if seed_demand > cajas_por_palet:
                paradas.append(Parada(
                    parada_id=f"{parada_id_prefix}-{counter}",
                    orden=counter,
                    tiendas=[self.tiendas[seed]],
                    representante_id=self.tiendas[seed].tienda_id,
                ))
                counter += 1
                continue

            cluster: list[int] = [seed]
            cluster_demand = seed_demand

            # Sort by (distance from seed, index) for determinism
            others = sorted(unvisited, key=lambda j: (m[seed][j], j))

            for j in others:
                if distancia_max is not None and m[seed][j] > distancia_max:
                    break  # all subsequent are farther — stop growing
                if cluster_demand + self.tiendas[j].num_cajas_total <= cajas_por_palet:
                    cluster.append(j)
                    cluster_demand += self.tiendas[j].num_cajas_total
                    unvisited.discard(j)
                else:
                    break  # pallet full — stop growing

            # Medoid: member that minimises sum of distances to other members
            if len(cluster) == 1:
                medoid = cluster[0]
            else:
                medoid = min(
                    cluster,
                    key=lambda i: sum(m[i][j] for j in cluster if j != i),
                )

            rep = self.tiendas[medoid]
            tiendas_ordered = [rep] + [
                self.tiendas[i] for i in cluster if i != medoid
            ]

            paradas.append(Parada(
                parada_id=f"{parada_id_prefix}-{counter}",
                orden=counter,
                tiendas=tiendas_ordered,
                representante_id=rep.tienda_id,
            ))
            counter += 1

        return paradas

    # ── demand aggregation ────────────────────────────────────────────────

    @property
    def pedidos(self) -> list[Pedido]:
        return [p for t in self.tiendas for p in t.pedidos]

    def pedidos_pendientes(self) -> list[Pedido]:
        return list(self.pedidos)

    @property
    def demanda_total_cajas(self) -> int:
        return sum(t.num_cajas_total for t in self.tiendas)

    @property
    def demanda_total_peso(self) -> float:
        return round(sum(t.peso_total_pedidos for t in self.tiendas), 3)

    @property
    def total_envases_retorno(self) -> int:
        return sum(t.num_envases_retorno for t in self.tiendas)

    # ── warehouse integration ─────────────────────────────────────────────

    def solicitar_productos_almacen(self, almacen: Almacen) -> dict[str, int]:
        """
        Aggregate product demand for all pending orders in this zone.

        Returns {sku: total_boxes_needed}.  Almacen uses this to prepare
        pallets before the loading solver runs.
        """
        demand: dict[str, int] = {}
        for pedido in self.pedidos_pendientes():
            for linea in pedido.lineas:
                demand[linea.product.sku] = (
                    demand.get(linea.product.sku, 0) + linea.quantity_boxes
                )
        return demand

    # ── solver integration ────────────────────────────────────────────────

    def to_vrp_input(
        self,
        depot_x: float = 0.0,
        depot_y: float = 0.0,
        depot_id: str = "depot",
    ) -> dict:
        """
        Export a solver-ready dict for VRP / TSP algorithms.

        Schema
        ------
        {
            "zona_id": str,
            "depot":   {"id": str, "x": float, "y": float, "index": 0},
            "nodes":   [{"id": str, "index": int, "x": float, "y": float,
                         "demand_cajas": int, "demand_kg": float,
                         "envases_retorno": int}],
            "matrix":  list[list[float]],   # (n+1)×(n+1) with depot at index 0
            "num_nodes": int,
        }

        The depot is prepended at index 0 so matrix[0][i] = cost depot→store i.
        """
        m = self._require_matriz()
        n = len(self.tiendas)

        # Build extended (n+1)×(n+1) matrix including depot
        depot_row = [
            math.sqrt((depot_x - t.x) ** 2 + (depot_y - t.y) ** 2)
            for t in self.tiendas
        ]
        extended = [[0.0] + depot_row]  # depot → stores
        for i, row in enumerate(m):
            depot_col = math.sqrt(
                (self.tiendas[i].x - depot_x) ** 2
                + (self.tiendas[i].y - depot_y) ** 2
            )
            extended.append([depot_col] + list(row))

        nodes = [
            {
                "id": t.tienda_id,
                "index": idx + 1,
                "x": t.x,
                "y": t.y,
                "demand_cajas": t.num_cajas_total,
                "demand_kg": t.peso_total_pedidos,
                "envases_retorno": t.num_envases_retorno,
            }
            for idx, t in enumerate(self.tiendas)
        ]

        return {
            "zona_id": self.zona_id,
            "depot": {"id": depot_id, "x": depot_x, "y": depot_y, "index": 0},
            "nodes": nodes,
            "matrix": extended,
            "num_nodes": n + 1,
        }

    # ── validation ────────────────────────────────────────────────────────

    def validar(self) -> list[str]:
        errors: list[str] = []
        if not self.tiendas:
            errors.append(f"Zona {self.zona_id!r}: no stores")
        for tienda in self.tiendas:
            errors.extend(tienda.validar())
        return errors

    # ── metrics ───────────────────────────────────────────────────────────

    def metricas(self) -> dict:
        return {
            "zona_id": self.zona_id,
            "nombre": self.nombre,
            "num_tiendas": self.num_tiendas,
            "num_rutas": len(self.rutas),
            "demanda_total_cajas": self.demanda_total_cajas,
            "demanda_total_peso_kg": self.demanda_total_peso,
            "total_envases_retorno": self.total_envases_retorno,
            "pedidos_pendientes": len(self.pedidos_pendientes()),
            "matriz_generada": self._matriz is not None,
            "tipo_matriz": self._tipo_matriz.value if self._tipo_matriz else None,
        }

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "zona_id": self.zona_id,
            "nombre": self.nombre,
            "tiendas": [t.to_dict() for t in self.tiendas],
            "rutas": [r.to_dict() for r in self.rutas],
            "matriz": self._matriz,
            "tipo_matriz": self._tipo_matriz.value if self._tipo_matriz else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Zona:
        zona = cls(zona_id=data["zona_id"], nombre=data["nombre"])
        for t_data in data.get("tiendas", []):
            zona.tiendas.append(Tienda.from_dict(t_data))
        for r_data in data.get("rutas", []):
            zona.rutas.append(Ruta.from_dict(r_data))
        if data.get("matriz") is not None:
            zona._matriz = data["matriz"]
            tipo_raw = data.get("tipo_matriz", "personalizada")
            zona._tipo_matriz = TipoMatriz(tipo_raw)
        return zona

    def __repr__(self) -> str:
        return (
            f"Zona(id={self.zona_id!r}, nombre={self.nombre!r}, "
            f"{self.num_tiendas} tiendas, {self.demanda_total_cajas} cajas)"
        )
