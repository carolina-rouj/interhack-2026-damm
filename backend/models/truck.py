from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.palet import Palet


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


# ═══════════════════════════════════════════════════════════════════════════════
# Warehouse-level truck model (used by Almacen and logistics optimizers)
# ═══════════════════════════════════════════════════════════════════════════════


class AperturaTipo(Enum):
    """Physical opening type of a truck, determining which pallets are reachable."""
    REAR = "rear"
    LATERAL = "lateral"
    REAR_LATERAL = "rear+lateral"


class TipoCamion(Enum):
    FURGONETA = "furgoneta"
    MEDIANO = "mediano"
    GRANDE = "grande"


class Camion:
    """
    Physical truck for transporting pallets between warehouse and delivery points.

    The internal 2D grid represents the truck floor plan viewed from above:

      x → column  (0 = left, dim_x-1 = right)
      y → row     (0 = rear/door, dim_y-1 = near cabin)

    [REAR DOOR]
    [ (0,0) | (1,0) ]   ← first accessible with REAR opening
    [ (0,1) | (1,1) ]
    [ (0,2) | (1,2) ]   ← only reachable via LATERAL / REAR+LATERAL
    [  CABIN  ]

    Use CamionFactory.crear() to instantiate predefined truck types.
    """

    def __init__(
        self,
        camion_id: str,
        apertura: AperturaTipo,
        dim_x: int,
        dim_y: int,
    ) -> None:
        self.camion_id = camion_id
        self.apertura = apertura
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.capacidad_max: int = dim_x * dim_y
        # _matriz[x][y] = Palet | None
        self._matriz: list[list[Optional[Palet]]] = [
            [None] * dim_y for _ in range(dim_x)
        ]
        self._palets: list[Palet] = []

    # ── validation ────────────────────────────────────────────────────────

    def _validate_pos(self, x: int, y: int) -> None:
        if not (0 <= x < self.dim_x and 0 <= y < self.dim_y):
            raise IndexError(
                f"Position ({x},{y}) out of bounds for "
                f"{self.dim_x}×{self.dim_y} truck {self.camion_id!r}"
            )

    # ── load / unload ─────────────────────────────────────────────────────

    def cargar_palet(self, palet: Palet, x: int, y: int) -> None:
        """Load *palet* into slot (x, y)."""
        self._validate_pos(x, y)
        if self.esta_lleno:
            raise OverflowError(
                f"Truck {self.camion_id!r} is full ({self.capacidad_max} pallets)"
            )
        if self._matriz[x][y] is not None:
            raise ValueError(f"Slot ({x},{y}) is already occupied")
        self._matriz[x][y] = palet
        self._palets.append(palet)

    def descargar_palet(self, x: int, y: int) -> Palet:
        """Unload and return the pallet at slot (x, y)."""
        self._validate_pos(x, y)
        palet = self._matriz[x][y]
        if palet is None:
            raise ValueError(f"Slot ({x},{y}) is empty")
        self._matriz[x][y] = None
        self._palets.remove(palet)
        return palet

    def get_palet_at(self, x: int, y: int) -> Optional[Palet]:
        """Return the pallet at slot (x, y) without removing it."""
        self._validate_pos(x, y)
        return self._matriz[x][y]

    def posicion_libre(self) -> Optional[tuple[int, int]]:
        """Return the first free slot (rear → cabin, left → right), or None if full."""
        for y in range(self.dim_y):
            for x in range(self.dim_x):
                if self._matriz[x][y] is None:
                    return (x, y)
        return None

    def posiciones_ocupadas(self) -> list[tuple[int, int]]:
        return [
            (x, y)
            for x in range(self.dim_x)
            for y in range(self.dim_y)
            if self._matriz[x][y] is not None
        ]

    # ── capacity & weight ─────────────────────────────────────────────────

    @property
    def ocupacion(self) -> int:
        return len(self._palets)

    @property
    def esta_lleno(self) -> bool:
        return self.ocupacion >= self.capacidad_max

    @property
    def porcentaje_ocupacion(self) -> float:
        return round(self.ocupacion / self.capacidad_max * 100, 1)

    @property
    def peso_total(self) -> float:
        return round(sum(p.peso_total for p in self._palets), 3)

    @property
    def palets(self) -> list[Palet]:
        return list(self._palets)

    # ── visual helpers ────────────────────────────────────────────────────

    def visualizar(self) -> str:
        """ASCII top-down view of the truck floor plan."""
        lines = [
            f"Camion [{self.camion_id}] | {self.apertura.value} | "
            f"{self.ocupacion}/{self.capacidad_max} pallets",
            "  [REAR]",
        ]
        for y in range(self.dim_y):
            cells = []
            for x in range(self.dim_x):
                cell = self._matriz[x][y]
                cells.append(f" {cell.palet_id[:4]:^4} " if cell else "  --  ")
            lines.append("  |" + "|".join(cells) + "|")
        lines.append("  [CAB]")
        return "\n".join(lines)

    # ── serialization ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "camion_id": self.camion_id,
            "tipo": type(self).__name__,
            "apertura": self.apertura.value,
            "ocupacion": self.ocupacion,
            "capacidad_max": self.capacidad_max,
            "porcentaje_ocupacion": self.porcentaje_ocupacion,
            "peso_total_kg": self.peso_total,
        }

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.camion_id!r}, "
            f"apertura={self.apertura.value}, "
            f"{self.ocupacion}/{self.capacidad_max} pallets)"
        )

    def to_dict(self) -> dict:
        return {
            "camion_id": self.camion_id,
            "tipo": type(self).__name__,
            "apertura": self.apertura.value,
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "capacidad_max": self.capacidad_max,
            "ocupacion": self.ocupacion,
            "peso_total_kg": self.peso_total,
            "palets": [p.to_dict() for p in self._palets],
        }


# ── predefined truck types ────────────────────────────────────────────────────


class Furgoneta(Camion):
    """Van: rear door only, 3 pallets (1 col × 3 rows)."""

    def __init__(self, camion_id: str) -> None:
        super().__init__(camion_id, AperturaTipo.REAR, dim_x=1, dim_y=3)


class CamionMediano(Camion):
    """Medium truck: lateral tarpaulin, 6 pallets (2 cols × 3 rows)."""

    def __init__(self, camion_id: str) -> None:
        super().__init__(camion_id, AperturaTipo.LATERAL, dim_x=2, dim_y=3)


class CamionGrande(Camion):
    """Large truck: rear door + lateral tarpaulin, 8 pallets (2 cols × 4 rows)."""

    def __init__(self, camion_id: str) -> None:
        super().__init__(camion_id, AperturaTipo.REAR_LATERAL, dim_x=2, dim_y=4)


# ── factory ───────────────────────────────────────────────────────────────────


class CamionFactory:
    """
    Creates Camion instances by TipoCamion.

    To extend with a new type:
        CamionFactory.registrar_tipo(TipoCamion.NUEVO, MiCamion)
    """

    _registry: dict[TipoCamion, type[Camion]] = {
        TipoCamion.FURGONETA: Furgoneta,
        TipoCamion.MEDIANO: CamionMediano,
        TipoCamion.GRANDE: CamionGrande,
    }

    @classmethod
    def crear(cls, tipo: TipoCamion, camion_id: str) -> Camion:
        klass = cls._registry.get(tipo)
        if klass is None:
            raise ValueError(f"Unknown truck type: {tipo!r}")
        return klass(camion_id)

    @classmethod
    def registrar_tipo(cls, tipo: TipoCamion, klass: type[Camion]) -> None:
        cls._registry[tipo] = klass
