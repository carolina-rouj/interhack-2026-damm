from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class EstadoToro(Enum):
    LIBRE = "libre"
    EN_TAREA = "en_tarea"
    AVERIADO = "averiado"


@dataclass
class Toro:
    """
    Forklift operating inside the warehouse.

    posicion_inicial is the (x, y) grid cell where this toro starts each shift.
    velocidad_celdas_por_min is used by the optimizer to estimate travel times.
    """

    toro_id: str
    posicion_inicial: tuple[int, int]
    velocidad_celdas_por_min: float = 5.0
    estado: EstadoToro = field(default=EstadoToro.LIBRE)

    @property
    def disponible(self) -> bool:
        return self.estado == EstadoToro.LIBRE

    def to_dict(self) -> dict:
        return {
            "toro_id": self.toro_id,
            "posicion_inicial": list(self.posicion_inicial),
            "velocidad_celdas_por_min": self.velocidad_celdas_por_min,
            "estado": self.estado.value,
        }

    def __repr__(self) -> str:
        return (
            f"Toro(id={self.toro_id!r}, "
            f"pos={self.posicion_inicial}, "
            f"estado={self.estado.value})"
        )
