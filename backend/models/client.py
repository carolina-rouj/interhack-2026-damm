from dataclasses import dataclass
from enum import Enum


class AccessRestriction(Enum):
    NONE = "none"
    TIME_RESTRICTED = "time_restricted"
    PEDESTRIAN_ZONE = "pedestrian_zone"


@dataclass
class TimeWindow:
    open_min: int   # minutes from midnight, e.g. 8*60=480
    close_min: int

    def to_dict(self):
        return {"open_min": self.open_min, "close_min": self.close_min}

    @staticmethod
    def from_hhmm(open_hhmm: str, close_hhmm: str) -> "TimeWindow":
        def to_min(hhmm: str) -> int:
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)
        return TimeWindow(to_min(open_hhmm), to_min(close_hhmm))


@dataclass
class Client:
    client_id: str
    name: str
    lat: float
    lon: float
    unload_time_min: int
    time_window: TimeWindow
    restriction: AccessRestriction
    priority: int               # 1=must-serve, 2=high, 3=normal
    expected_returnables: int   # boxes expected to collect (empties)

    def to_dict(self):
        return {
            "client_id": self.client_id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "unload_time_min": self.unload_time_min,
            "time_window": self.time_window.to_dict(),
            "restriction": self.restriction.value,
            "priority": self.priority,
            "expected_returnables": self.expected_returnables,
        }
