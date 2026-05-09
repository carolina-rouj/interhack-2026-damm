from dataclasses import dataclass, field
from enum import Enum


class Side(Enum):
    REAR = "rear"
    LEFT = "left_lona"
    RIGHT = "right_lona"


@dataclass
class PalletSlot:
    slot_id: int
    row: int    # 1=rear (near door), 3=front (near cab)
    col: int    # 1=left, 2=right
    # Truck viewed from above:
    # [REAR DOOR]
    # [ P1 | P2 ]  row=1  ← first to unload
    # [ P3 | P4 ]  row=2
    # [ P5 | P6 ]  row=3  ← last to unload, lona only
    # [CABIN]
    accessible_from: list = field(default_factory=list)

    def to_dict(self):
        return {
            "slot_id": self.slot_id,
            "row": self.row,
            "col": self.col,
            "accessible_from": [s.value for s in self.accessible_from],
        }


def build_truck_slots() -> list:
    return [
        PalletSlot(1, 1, 1, [Side.REAR, Side.LEFT]),
        PalletSlot(2, 1, 2, [Side.REAR, Side.RIGHT]),
        PalletSlot(3, 2, 1, [Side.LEFT]),
        PalletSlot(4, 2, 2, [Side.RIGHT]),
        PalletSlot(5, 3, 1, [Side.LEFT]),
        PalletSlot(6, 3, 2, [Side.RIGHT]),
    ]


@dataclass
class PalletAssignment:
    slot: PalletSlot
    client_id: str | None
    client_name: str | None
    boxes: int
    is_returnable_buffer: bool = False
    delivery_position: int = 0

    def to_dict(self):
        return {
            "slot": self.slot.to_dict(),
            "client_id": self.client_id,
            "client_name": self.client_name,
            "boxes": self.boxes,
            "is_returnable_buffer": self.is_returnable_buffer,
            "delivery_position": self.delivery_position,
        }


@dataclass
class LoadPlan:
    route_id: str
    assignments: list = field(default_factory=list)
    returnable_slots: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def utilization_pct(self) -> float:
        used = sum(a.boxes for a in self.assignments if not a.is_returnable_buffer)
        return round(used / (6 * 60) * 100, 1)

    def to_dict(self):
        return {
            "route_id": self.route_id,
            "assignments": [a.to_dict() for a in self.assignments],
            "returnable_slots": self.returnable_slots,
            "warnings": self.warnings,
            "utilization_pct": self.utilization_pct,
        }
