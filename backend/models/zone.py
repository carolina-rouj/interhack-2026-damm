from dataclasses import dataclass, field


@dataclass
class Depot:
    name: str
    lat: float
    lon: float

    def to_dict(self):
        return {"name": self.name, "lat": self.lat, "lon": self.lon}


@dataclass
class Zone:
    zone_id: str
    name: str
    city: str
    depot: Depot

    def to_dict(self):
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "city": self.city,
            "depot": self.depot.to_dict(),
        }


