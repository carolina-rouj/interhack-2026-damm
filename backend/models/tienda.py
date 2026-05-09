from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional

from backend.models.pedido import Pedido, EstadoPedido


@dataclass
class Tienda:
    """
    A delivery point (store, bar, restaurant, etc.).

    Coordinates (x, y) are used by distance / cost matrix generators and VRP
    solvers.  All routing and packing logic lives in external solvers — Tienda
    only owns its data and exposes read-only computed properties.
    """

    tienda_id: str
    nombre: str
    x: float
    y: float
    pedidos: list[Pedido] = field(default_factory=list)
    nombre_contacto: Optional[str] = None
    telefono: Optional[str] = None

    # ── order management ──────────────────────────────────────────────────

    def añadir_pedido(self, pedido: Pedido) -> None:
        if pedido.tienda_id != self.tienda_id:
            raise ValueError(
                f"Pedido {pedido.pedido_id!r} belongs to tienda "
                f"{pedido.tienda_id!r}, not {self.tienda_id!r}"
            )
        self.pedidos.append(pedido)

    def pedidos_pendientes(self) -> list[Pedido]:
        return [p for p in self.pedidos if p.estado == EstadoPedido.PENDIENTE]

    def pedidos_entregados(self) -> list[Pedido]:
        return [p for p in self.pedidos if p.estado == EstadoPedido.ENTREGADO]

    # ── demand metrics ────────────────────────────────────────────────────

    @property
    def peso_total_pedidos(self) -> float:
        return round(sum(p.peso_total for p in self.pedidos), 3)

    @property
    def volumen_total_pedidos(self) -> float:
        return round(sum(p.volumen_total for p in self.pedidos), 3)

    @property
    def num_cajas_total(self) -> int:
        return sum(p.num_cajas for p in self.pedidos)

    @property
    def num_envases_retorno(self) -> int:
        return sum(p.num_envases_recogida for p in self.pedidos if p.es_retornable)

    @property
    def tiene_retornables(self) -> bool:
        return any(p.es_retornable for p in self.pedidos)

    # ── spatial helpers ───────────────────────────────────────────────────

    def distancia_a(self, otra: Tienda) -> float:
        """Euclidean distance to another store."""
        return math.sqrt((self.x - otra.x) ** 2 + (self.y - otra.y) ** 2)

    # ── validation ────────────────────────────────────────────────────────

    def validar(self) -> list[str]:
        errors: list[str] = []
        if not self.pedidos:
            errors.append(f"Tienda {self.tienda_id!r}: has no orders")
        for pedido in self.pedidos:
            errors.extend(pedido.validar())
        return errors

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "tienda_id": self.tienda_id,
            "nombre": self.nombre,
            "x": self.x,
            "y": self.y,
            "nombre_contacto": self.nombre_contacto,
            "telefono": self.telefono,
            "pedidos": [p.to_dict() for p in self.pedidos],
            "num_cajas_total": self.num_cajas_total,
            "peso_total_pedidos": self.peso_total_pedidos,
            "num_envases_retorno": self.num_envases_retorno,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Tienda:
        tienda = cls(
            tienda_id=data["tienda_id"],
            nombre=data["nombre"],
            x=data["x"],
            y=data["y"],
            nombre_contacto=data.get("nombre_contacto"),
            telefono=data.get("telefono"),
        )
        for p_data in data.get("pedidos", []):
            tienda.pedidos.append(Pedido.from_dict(p_data))
        return tienda

    def __repr__(self) -> str:
        return (
            f"Tienda(id={self.tienda_id!r}, nombre={self.nombre!r}, "
            f"pos=({self.x},{self.y}), {len(self.pedidos)} pedidos, "
            f"{self.num_cajas_total} cajas)"
        )
