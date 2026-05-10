from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid

from backend.models.product import Product

# (x, y, z) inside a pallet grid
Position = tuple[int, int, int]


@dataclass
class Palet:
    """
    Physical pallet that stores product boxes in a 3D grid.

    The matrix[x][y][z] stores either None (empty slot) or a Product reference
    (one box of that product type). Default grid is 5×4×3 = 60 slots, matching
    the 60-box pallet capacity used throughout the logistics model.

    Axes:
      x → column  (0 = left,   dim_x-1 = right)
      y → row     (0 = front,  dim_y-1 = back)
      z → layer   (0 = bottom, dim_z-1 = top)
    """

    palet_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    capacidad_max: int = 60
    dim_x: int = 5
    dim_y: int = 4
    dim_z: int = 3

    _productos: list[Product] = field(default_factory=list, init=False, repr=False)
    _matriz: list[list[list[Optional[Product]]]] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self) -> None:
        volume = self.dim_x * self.dim_y * self.dim_z
        if volume < self.capacidad_max:
            raise ValueError(
                f"Matrix {self.dim_x}×{self.dim_y}×{self.dim_z} ({volume} cells) "
                f"cannot hold capacidad_max={self.capacidad_max}"
            )
        self._matriz = [
            [[None for _ in range(self.dim_z)] for _ in range(self.dim_y)]
            for _ in range(self.dim_x)
        ]

    # ── capacity ──────────────────────────────────────────────────────────

    @property
    def ocupacion(self) -> int:
        return len(self._productos)

    @property
    def disponible(self) -> int:
        return self.capacidad_max - self.ocupacion

    @property
    def esta_lleno(self) -> bool:
        return self.ocupacion >= self.capacidad_max

    @property
    def porcentaje_ocupacion(self) -> float:
        return round(self.ocupacion / self.capacidad_max * 100, 1)

    # ── weight ────────────────────────────────────────────────────────────

    @property
    def peso_total(self) -> float:
        return round(sum(p.weight_kg_per_box for p in self._productos), 3)

    # ── matrix helpers ────────────────────────────────────────────────────

    def _validate_position(self, pos: Position) -> None:
        x, y, z = pos
        if not (0 <= x < self.dim_x and 0 <= y < self.dim_y and 0 <= z < self.dim_z):
            raise IndexError(
                f"Position {pos} out of bounds for {self.dim_x}×{self.dim_y}×{self.dim_z} grid"
            )

    def get_at(self, pos: Position) -> Optional[Product]:
        """Return the product at the given position, or None if empty."""
        self._validate_position(pos)
        x, y, z = pos
        return self._matriz[x][y][z]

    def _next_free_position(self) -> Optional[Position]:
        """Scan the matrix in (x, y, z) order and return the first empty cell."""
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                for z in range(self.dim_z):
                    if self._matriz[x][y][z] is None:
                        return (x, y, z)
        return None

    # ── CRUD ──────────────────────────────────────────────────────────────

    def add_product(self, product: Product, pos: Optional[Position] = None) -> Position:
        """
        Add one box of *product* to the pallet.

        If *pos* is None the next free cell is used automatically.
        Returns the position where the box was placed.
        """
        if self.esta_lleno:
            raise OverflowError(
                f"Palet {self.palet_id!r} is full ({self.capacidad_max} boxes)"
            )
        if pos is None:
            pos = self._next_free_position()

        self._validate_position(pos)
        x, y, z = pos
        if self._matriz[x][y][z] is not None:
            raise ValueError(f"Position {pos} is already occupied")

        self._matriz[x][y][z] = product
        self._productos.append(product)
        return pos

    def remove_product_at(self, pos: Position) -> Product:
        """Remove and return the product at *pos*."""
        self._validate_position(pos)
        x, y, z = pos
        product = self._matriz[x][y][z]
        if product is None:
            raise ValueError(f"Position {pos} is empty")
        self._matriz[x][y][z] = None
        self._productos.remove(product)
        return product

    def remove_product(self, product: Product) -> bool:
        """Remove a product by object identity. Returns True if found."""
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                for z in range(self.dim_z):
                    if self._matriz[x][y][z] is product:
                        self._matriz[x][y][z] = None
                        self._productos.remove(product)
                        return True
        return False

    def find_product(self, product: Product) -> Optional[Position]:
        """Return the matrix position of *product*, or None if not found."""
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                for z in range(self.dim_z):
                    if self._matriz[x][y][z] is product:
                        return (x, y, z)
        return None

    def find_by_sku(self, sku: str) -> list[Position]:
        """Return all positions that hold a product with the given SKU."""
        positions: list[Position] = []
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                for z in range(self.dim_z):
                    cell = self._matriz[x][y][z]
                    if cell is not None and cell.sku == sku:
                        positions.append((x, y, z))
        return positions

    @property
    def productos(self) -> list[Product]:
        return list(self._productos)

    # ── serialization ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "palet_id": self.palet_id,
            "ocupacion": self.ocupacion,
            "capacidad_max": self.capacidad_max,
            "porcentaje_ocupacion": self.porcentaje_ocupacion,
            "peso_total_kg": self.peso_total,
            "disponible": self.disponible,
        }

    def __repr__(self) -> str:
        return (
            f"Palet(id={self.palet_id!r}, "
            f"{self.ocupacion}/{self.capacidad_max} boxes, "
            f"{self.peso_total}kg)"
        )

    def to_dict(self) -> dict:
        return {
            "palet_id": self.palet_id,
            "capacidad_max": self.capacidad_max,
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "dim_z": self.dim_z,
            "ocupacion": self.ocupacion,
            "peso_total_kg": self.peso_total,
            "porcentaje_ocupacion": self.porcentaje_ocupacion,
            "productos": [p.to_dict() for p in self._productos],
        }
