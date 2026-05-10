from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from backend.models.product import Product, OrderLine


@dataclass
class Pedido:
    """
    A delivery order placed by a Tienda.

    *lineas* mirrors OrderLine so existing product definitions are reused
    without duplication.  Solver-populated fields (palets assigned, etc.)
    are filled in by external solvers — this class is intentionally free
    of packing or routing logic.
    """

    pedido_id: str
    tienda_id: str
    lineas: list[OrderLine] = field(default_factory=list)
    es_retornable: bool = False
    num_envases_recogida: int = 0

    # ── computed metrics ──────────────────────────────────────────────────

    @property
    def peso_total(self) -> float:
        """Total weight in kg of all boxes in this order."""
        return round(
            sum(l.product.weight_kg_per_box * l.quantity_boxes for l in self.lineas), 3
        )

    @property
    def volumen_total(self) -> float:
        """Proxy volume: sum of (tamano × quantity_boxes) across lines."""
        return round(
            sum(l.product.tamano * l.quantity_boxes for l in self.lineas), 3
        )

    @property
    def num_cajas(self) -> int:
        return sum(l.quantity_boxes for l in self.lineas)

    @property
    def total_boxes(self) -> int:
        return self.num_cajas

    # ── validation ────────────────────────────────────────────────────────

    def validar(self) -> list[str]:
        """Return a list of consistency errors; empty list means valid."""
        errors: list[str] = []
        if not self.lineas:
            errors.append(f"Pedido {self.pedido_id}: no lines")
        for line in self.lineas:
            if line.quantity_boxes <= 0:
                errors.append(
                    f"Pedido {self.pedido_id}: line {line.product.sku} "
                    f"has quantity_boxes={line.quantity_boxes}"
                )
        if self.num_envases_recogida < 0:
            errors.append(
                f"Pedido {self.pedido_id}: num_envases_recogida cannot be negative"
            )
        return errors

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "pedido_id": self.pedido_id,
            "tienda_id": self.tienda_id,
            "lineas": [
                {
                    "product": l.product.to_dict(),
                    "quantity_boxes": l.quantity_boxes,
                }
                for l in self.lineas
            ],
            "es_retornable": self.es_retornable,
            "num_envases_recogida": self.num_envases_recogida,
            "num_cajas": self.num_cajas,
            "peso_total": self.peso_total,
            "volumen_total": self.volumen_total,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pedido:
        lineas = [
            OrderLine(
                product=Product(
                    sku=l["product"]["sku"],
                    name=l["product"]["name"],
                    is_returnable=l["product"]["is_returnable"],
                    weight_kg_per_box=l["product"]["weight_kg_per_box"],
                    tipo=l["product"].get("tipo", "generico"),
                    tamano=l["product"].get("tamano", 0.0),
                ),
                quantity_boxes=l["quantity_boxes"],
            )
            for l in data.get("lineas", [])
        ]
        return cls(
            pedido_id=data["pedido_id"],
            tienda_id=data["tienda_id"],
            lineas=lineas,
            es_retornable=data.get("es_retornable", False),
            num_envases_recogida=data.get("num_envases_recogida", 0),
        )

    def __repr__(self) -> str:
        return (
            f"Pedido(id={self.pedido_id!r}, tienda={self.tienda_id!r}, "
            f"{self.num_cajas} boxes, {self.peso_total}kg)"
        )
