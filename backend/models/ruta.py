from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.tienda import Tienda


@dataclass
class Parada:
    """
    A single stop within a delivery route.

    A stop can serve one or more Tiendas (e.g., a pedestrian zone where
    several stores are grouped at the same drop-off point).

    Fields populated by solvers
    ---------------------------
    palets_entregados   — pallet IDs unloaded at this stop
    cajas_entregadas    — boxes delivered
    cajas_recogidas     — empty / returnable boxes picked up
    tiempo_estimado_min — dwell time at stop (unload + service)

    The Parada class itself imposes no business logic on these fields; it is
    a pure data container for solver output.
    """

    parada_id: str
    orden: int                         # position in the route (0 = first)
    tiendas: list[Tienda] = field(default_factory=list)

    # solver-populated
    palets_entregados: list[str] = field(default_factory=list)   # palet IDs
    cajas_entregadas: int = 0
    cajas_recogidas: int = 0
    tiempo_estimado_min: Optional[float] = None
    # set by agrupar_tiendas: the medoid store chosen as the physical stop point
    representante_id: Optional[str] = None

    # ── convenience ───────────────────────────────────────────────────────

    @property
    def num_tiendas(self) -> int:
        return len(self.tiendas)

    @property
    def ids_tiendas(self) -> list[str]:
        return [t.tienda_id for t in self.tiendas]

    # ── metrics ───────────────────────────────────────────────────────────

    def metricas(self) -> dict:
        return {
            "parada_id": self.parada_id,
            "orden": self.orden,
            "num_tiendas": self.num_tiendas,
            "palets_entregados": self.palets_entregados,
            "cajas_entregadas": self.cajas_entregadas,
            "cajas_recogidas": self.cajas_recogidas,
            "tiempo_estimado_min": self.tiempo_estimado_min,
        }

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "parada_id": self.parada_id,
            "orden": self.orden,
            "tiendas": [t.to_dict() for t in self.tiendas],
            "palets_entregados": self.palets_entregados,
            "cajas_entregadas": self.cajas_entregadas,
            "cajas_recogidas": self.cajas_recogidas,
            "tiempo_estimado_min": self.tiempo_estimado_min,
            "representante_id": self.representante_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Parada:
        from backend.models.tienda import Tienda
        return cls(
            parada_id=data["parada_id"],
            orden=data["orden"],
            tiendas=[Tienda.from_dict(t) for t in data.get("tiendas", [])],
            palets_entregados=data.get("palets_entregados", []),
            cajas_entregadas=data.get("cajas_entregadas", 0),
            cajas_recogidas=data.get("cajas_recogidas", 0),
            tiempo_estimado_min=data.get("tiempo_estimado_min"),
            representante_id=data.get("representante_id"),
        )

    def __repr__(self) -> str:
        return (
            f"Parada(id={self.parada_id!r}, orden={self.orden}, "
            f"tiendas={self.ids_tiendas}, "
            f"{self.cajas_entregadas} boxes out / {self.cajas_recogidas} in)"
        )


@dataclass
class Ruta:
    """
    An ordered delivery route within a Zona.

    The route's stop sequence and load plan are set by external solvers
    (VRP/TSP and truck-loading solvers respectively).  Ruta owns the
    result data; it never computes it.

    Fields populated by solvers
    ---------------------------
    camion_id           — truck assigned to this route
    coste_total         — objective value (distance, time, cost…)
    distancia_total_km  — total road distance
    tiempo_estimado_min — total estimated route duration
    """

    ruta_id: str
    zona_id: str
    paradas: list[Parada] = field(default_factory=list)

    # solver-populated
    camion_id: Optional[str] = None
    coste_total: Optional[float] = None
    distancia_total_km: Optional[float] = None
    tiempo_estimado_min: Optional[float] = None

    # ── accessors ─────────────────────────────────────────────────────────

    @property
    def num_paradas(self) -> int:
        return len(self.paradas)

    def tiendas_en_ruta(self) -> list[Tienda]:
        """Flat list of all Tiendas across all stops, in delivery order."""
        return [t for parada in self.paradas for t in parada.tiendas]

    def parada_por_orden(self, orden: int) -> Optional[Parada]:
        for p in self.paradas:
            if p.orden == orden:
                return p
        return None

    # ── aggregate metrics ─────────────────────────────────────────────────

    @property
    def total_cajas_entregadas(self) -> int:
        return sum(p.cajas_entregadas for p in self.paradas)

    @property
    def total_cajas_recogidas(self) -> int:
        return sum(p.cajas_recogidas for p in self.paradas)

    @property
    def total_palets_entregados(self) -> int:
        return sum(len(p.palets_entregados) for p in self.paradas)

    def metricas(self) -> dict:
        return {
            "ruta_id": self.ruta_id,
            "zona_id": self.zona_id,
            "camion_id": self.camion_id,
            "num_paradas": self.num_paradas,
            "num_tiendas": len(self.tiendas_en_ruta()),
            "total_cajas_entregadas": self.total_cajas_entregadas,
            "total_cajas_recogidas": self.total_cajas_recogidas,
            "total_palets_entregados": self.total_palets_entregados,
            "coste_total": self.coste_total,
            "distancia_total_km": self.distancia_total_km,
            "tiempo_estimado_min": self.tiempo_estimado_min,
        }

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "ruta_id": self.ruta_id,
            "zona_id": self.zona_id,
            "camion_id": self.camion_id,
            "coste_total": self.coste_total,
            "distancia_total_km": self.distancia_total_km,
            "tiempo_estimado_min": self.tiempo_estimado_min,
            "paradas": [p.to_dict() for p in self.paradas],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Ruta:
        ruta = cls(
            ruta_id=data["ruta_id"],
            zona_id=data["zona_id"],
            camion_id=data.get("camion_id"),
            coste_total=data.get("coste_total"),
            distancia_total_km=data.get("distancia_total_km"),
            tiempo_estimado_min=data.get("tiempo_estimado_min"),
        )
        ruta.paradas = [Parada.from_dict(p) for p in data.get("paradas", [])]
        return ruta

    def __repr__(self) -> str:
        return (
            f"Ruta(id={self.ruta_id!r}, zona={self.zona_id!r}, "
            f"camion={self.camion_id!r}, {self.num_paradas} paradas, "
            f"dist={self.distancia_total_km}km)"
        )
