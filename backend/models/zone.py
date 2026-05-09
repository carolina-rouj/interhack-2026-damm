from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Depot:
    name: str
    lat: float
    lon: float

    def to_dict(self) -> dict:
        return {"name": self.name, "lat": self.lat, "lon": self.lon}


@dataclass
class Zone:
    zone_id: str
    name: str
    city: str
    depot: Depot

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "city": self.city,
            "depot": self.depot.to_dict(),
        }
