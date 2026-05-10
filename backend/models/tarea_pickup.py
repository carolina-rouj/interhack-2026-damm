from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EstadoTarea(Enum):
    PENDIENTE = "pendiente"
    ASIGNADA = "asignada"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"


@dataclass
class TareaPickup:
    """
    A single forklift pickup task: retrieve *palet_id* from its current
    warehouse floor position (*origin*) and deliver it to the truck staging
    area (*destino*).

    Both coordinates are global (x, y) on the warehouse floor plan.
    """

    tarea_id: str
    palet_id: str
    pedido_id: str
    origin: tuple[int, int]
    destino: tuple[int, int]
    prioridad: int = 1                          # 1 = highest
    estado: EstadoTarea = field(default=EstadoTarea.PENDIENTE)
    toro_asignado: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tarea_id": self.tarea_id,
            "palet_id": self.palet_id,
            "pedido_id": self.pedido_id,
            "origin": list(self.origin),
            "destino": list(self.destino),
            "prioridad": self.prioridad,
            "estado": self.estado.value,
            "toro_asignado": self.toro_asignado,
        }

    def __repr__(self) -> str:
        return (
            f"TareaPickup(id={self.tarea_id!r}, "
            f"palet={self.palet_id!r}, "
            f"{self.origin} → {self.destino}, "
            f"prio={self.prioridad})"
        )
