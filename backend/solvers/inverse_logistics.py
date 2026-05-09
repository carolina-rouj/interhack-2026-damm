import math
from dataclasses import dataclass, field

from backend.models.truck import build_truck_slots


@dataclass
class ReturnablesPlan:
    reserved_slot_ids: list = field(default_factory=list)
    total_expected_boxes: int = 0
    pallets_reserved: int = 0
    per_client: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "reserved_slot_ids": self.reserved_slot_ids,
            "total_expected_boxes": self.total_expected_boxes,
            "pallets_reserved": self.pallets_reserved,
            "per_client": self.per_client,
        }


def plan_returnables(clients: list) -> ReturnablesPlan:
    total_boxes = sum(c.expected_returnables for c in clients)
    pallets_needed = math.ceil(total_boxes / 60) if total_boxes > 0 else 0

    slots = build_truck_slots()
    # Reserve from front (highest row number = closest to cabin = last unloaded)
    front_first = sorted(slots, key=lambda s: -s.row)
    reserved_ids = [s.slot_id for s in front_first[:pallets_needed]]

    per_client = {c.client_id: c.expected_returnables for c in clients if c.expected_returnables > 0}

    return ReturnablesPlan(
        reserved_slot_ids=reserved_ids,
        total_expected_boxes=total_boxes,
        pallets_reserved=pallets_needed,
        per_client=per_client,
    )
