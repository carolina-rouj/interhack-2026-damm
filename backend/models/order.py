from dataclasses import dataclass, field


@dataclass
class Product:
    sku: str
    name: str
    is_returnable: bool
    weight_kg_per_box: float

    def to_dict(self):
        return {
            "sku": self.sku,
            "name": self.name,
            "is_returnable": self.is_returnable,
            "weight_kg_per_box": self.weight_kg_per_box,
        }


@dataclass
class OrderLine:
    product: Product
    quantity_boxes: int

    def to_dict(self):
        return {
            "product": self.product.to_dict(),
            "quantity_boxes": self.quantity_boxes,
        }


@dataclass
class Order:
    order_id: str
    client_id: str
    lines: list = field(default_factory=list)

    @property
    def total_boxes(self) -> int:
        return sum(l.quantity_boxes for l in self.lines)

    @property
    def pallets_needed(self) -> float:
        return self.total_boxes / 60

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "client_id": self.client_id,
            "lines": [l.to_dict() for l in self.lines],
            "total_boxes": self.total_boxes,
            "pallets_needed": round(self.pallets_needed, 2),
        }
