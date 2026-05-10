from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Product:
    sku: str
    name: str
    is_returnable: bool
    weight_kg_per_box: float
    tipo: str = "generico"
    tamano: float = 0.0  # volume in litres

    def __post_init__(self) -> None:
        if self.weight_kg_per_box < 0:
            raise ValueError(f"weight_kg_per_box must be >= 0, got {self.weight_kg_per_box}")
        if self.tamano < 0:
            raise ValueError(f"tamano must be >= 0, got {self.tamano}")

    # ── aliases for domain-language consistency ───────────────────────────

    @property
    def id(self) -> str:
        return self.sku

    @property
    def peso(self) -> float:
        return self.weight_kg_per_box

    @property
    def retornable(self) -> bool:
        return self.is_returnable

    # ── dunder ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Product(sku={self.sku!r}, name={self.name!r}, "
            f"tipo={self.tipo!r}, tamano={self.tamano}L, "
            f"peso={self.weight_kg_per_box}kg, retornable={self.is_returnable})"
        )

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "name": self.name,
            "is_returnable": self.is_returnable,
            "weight_kg_per_box": self.weight_kg_per_box,
            "tipo": self.tipo,
            "tamano": self.tamano,
        }


@dataclass
class OrderLine:
    product: Product
    quantity_boxes: int

    def to_dict(self) -> dict:
        return {
            "product": self.product.to_dict(),
            "quantity_boxes": self.quantity_boxes,
        }


@dataclass
class Order:
    order_id: str
    client_id: str
    lines: list[OrderLine] = field(default_factory=list)

    @property
    def total_boxes(self) -> int:
        return sum(line.quantity_boxes for line in self.lines)

    @property
    def pallets_needed(self) -> float:
        return self.total_boxes / 60

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "client_id": self.client_id,
            "lines": [line.to_dict() for line in self.lines],
            "total_boxes": self.total_boxes,
            "pallets_needed": round(self.pallets_needed, 2),
        }
