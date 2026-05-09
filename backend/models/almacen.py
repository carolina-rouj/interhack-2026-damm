from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import uuid

from backend.models.product import Product
from backend.models.palet import Palet
from backend.models.truck import Camion

# Global warehouse position: (x, y, z)
Position3D = tuple[int, int, int]


@dataclass
class ZonaAlmacen:
    """
    Rectangular subregion of the warehouse floor plan.

    Coordinates are expressed in the global matrix space:
      offset_x, offset_y  → top-left corner of this zone
      dim_x, dim_y        → width and depth of the zone (in pallet slots)
      dim_z               → maximum stacking height within this zone

    Use contains() to test whether a global (gx, gy) belongs here.
    """

    zona_id: str
    nombre: str
    offset_x: int
    offset_y: int
    dim_x: int
    dim_y: int
    dim_z: int = 1  # stacking levels

    @property
    def capacidad(self) -> int:
        """Maximum pallets this zone can hold."""
        return self.dim_x * self.dim_y * self.dim_z

    def contains(self, gx: int, gy: int) -> bool:
        """Return True if global column *gx* and row *gy* fall within this zone."""
        return (
            self.offset_x <= gx < self.offset_x + self.dim_x
            and self.offset_y <= gy < self.offset_y + self.dim_y
        )

    def __repr__(self) -> str:
        return (
            f"ZonaAlmacen(id={self.zona_id!r}, nombre={self.nombre!r}, "
            f"offset=({self.offset_x},{self.offset_y}), "
            f"dim={self.dim_x}×{self.dim_y}×{self.dim_z}, "
            f"cap={self.capacidad})"
        )

    def to_dict(self) -> dict:
        return {
            "zona_id": self.zona_id,
            "nombre": self.nombre,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "dim_z": self.dim_z,
            "capacidad": self.capacidad,
        }


class Almacen:
    """
    Central warehouse manager — single source of truth for the logistics system.

    Responsibilities
    ----------------
    * Product catalogue (sku → Product)
    * Pallet registry (palet_id → Palet) and spatial tracking
    * Fleet registry (camion_id → Camion)
    * Storage-zone registry (zona_id → ZonaAlmacen)
    * Global 3-D spatial matrix for optimization / solver algorithms

    Global matrix
    -------------
    _matriz[x][y][z] = Palet | None

      x → column   (warehouse width)
      y → row      (warehouse depth)
      z → level    (stacking height)

    The matrix is a contiguous 3-D grid that spans the full warehouse footprint.
    Zones are named subregions within it; a pallet can be placed anywhere the
    cell is empty, but zone-aware placement allows future solvers to respect
    product-type segregation, temperature zones, etc.

    Forklift (toro) count is tracked for capacity-planning; actual scheduling
    of forklifts is delegated to a future solver.
    """

    def __init__(
        self,
        almacen_id: str,
        dim_x: int,
        dim_y: int,
        dim_z: int,
        num_toros: int = 2,
    ) -> None:
        self.almacen_id = almacen_id
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.dim_z = dim_z
        self.num_toros = num_toros

        # Global 3-D spatial matrix
        self._matriz: list[list[list[Optional[Palet]]]] = [
            [[None for _ in range(dim_z)] for _ in range(dim_y)]
            for _ in range(dim_x)
        ]

        # Registries
        self._productos: dict[str, Product] = {}       # sku → Product
        self._palets: dict[str, Palet] = {}            # palet_id → Palet
        self._camiones: dict[str, Camion] = {}         # camion_id → Camion
        self._zonas: dict[str, ZonaAlmacen] = {}       # zona_id → ZonaAlmacen

        # Spatial index: palet_id → global (x, y, z)
        self._palet_posiciones: dict[str, Position3D] = {}

    # ── zones ─────────────────────────────────────────────────────────────

    def registrar_zona(self, zona: ZonaAlmacen) -> None:
        """Register a storage zone. Its footprint must fit the global matrix."""
        if zona.offset_x + zona.dim_x > self.dim_x:
            raise ValueError(
                f"Zone {zona.zona_id!r} exceeds x-bound "
                f"({zona.offset_x + zona.dim_x} > {self.dim_x})"
            )
        if zona.offset_y + zona.dim_y > self.dim_y:
            raise ValueError(
                f"Zone {zona.zona_id!r} exceeds y-bound "
                f"({zona.offset_y + zona.dim_y} > {self.dim_y})"
            )
        if zona.dim_z > self.dim_z:
            raise ValueError(
                f"Zone {zona.zona_id!r} stacking height {zona.dim_z} "
                f"exceeds warehouse height {self.dim_z}"
            )
        self._zonas[zona.zona_id] = zona

    def zona_de_posicion(self, gx: int, gy: int) -> Optional[ZonaAlmacen]:
        """Return the zone that contains global (gx, gy), or None."""
        for zona in self._zonas.values():
            if zona.contains(gx, gy):
                return zona
        return None

    @property
    def zonas(self) -> list[ZonaAlmacen]:
        return list(self._zonas.values())

    # ── products ──────────────────────────────────────────────────────────

    def registrar_producto(self, producto: Product) -> None:
        if producto.sku in self._productos:
            raise ValueError(f"Product {producto.sku!r} is already registered")
        self._productos[producto.sku] = producto

    def obtener_producto(self, sku: str) -> Product:
        if sku not in self._productos:
            raise KeyError(f"Product {sku!r} not found")
        return self._productos[sku]

    def buscar_producto(
        self,
        sku: Optional[str] = None,
        tipo: Optional[str] = None,
        retornable: Optional[bool] = None,
    ) -> list[Product]:
        """Filter the product catalogue by any combination of sku / tipo / retornable."""
        results = list(self._productos.values())
        if sku is not None:
            results = [p for p in results if p.sku == sku]
        if tipo is not None:
            results = [p for p in results if p.tipo == tipo]
        if retornable is not None:
            results = [p for p in results if p.is_returnable == retornable]
        return results

    @property
    def productos(self) -> list[Product]:
        return list(self._productos.values())

    # ── pallets ───────────────────────────────────────────────────────────

    def crear_palet(
        self,
        palet_id: Optional[str] = None,
        capacidad_max: int = 60,
    ) -> Palet:
        """Create, register, and return a new pallet."""
        pid = palet_id or str(uuid.uuid4())[:8]
        if pid in self._palets:
            raise ValueError(f"Palet {pid!r} already exists")
        palet = Palet(palet_id=pid, capacidad_max=capacidad_max)
        self._palets[pid] = palet
        return palet

    def registrar_palet(self, palet: Palet) -> None:
        """Register an externally-created pallet."""
        if palet.palet_id in self._palets:
            raise ValueError(f"Palet {palet.palet_id!r} already registered")
        self._palets[palet.palet_id] = palet

    def eliminar_palet(self, palet_id: str) -> Palet:
        """Remove a pallet from the registry and clear its matrix cell if placed."""
        if palet_id not in self._palets:
            raise KeyError(f"Palet {palet_id!r} not found")
        palet = self._palets.pop(palet_id)
        if palet_id in self._palet_posiciones:
            x, y, z = self._palet_posiciones.pop(palet_id)
            self._matriz[x][y][z] = None
        return palet

    def obtener_palet(self, palet_id: str) -> Palet:
        if palet_id not in self._palets:
            raise KeyError(f"Palet {palet_id!r} not found")
        return self._palets[palet_id]

    @property
    def palets(self) -> list[Palet]:
        return list(self._palets.values())

    # ── product → pallet assignment ───────────────────────────────────────

    def asignar_producto_a_palet(
        self,
        sku: str,
        palet_id: str,
        pos: Optional[tuple[int, int, int]] = None,
    ) -> tuple[int, int, int]:
        """
        Place one box of *sku* onto *palet_id*.

        *pos* is the (x, y, z) cell within the pallet; auto-assigned if None.
        Returns the cell position used.
        """
        producto = self.obtener_producto(sku)
        palet = self.obtener_palet(palet_id)
        return palet.add_product(producto, pos)

    # ── global spatial matrix ─────────────────────────────────────────────

    def _validate_global_pos(self, x: int, y: int, z: int) -> None:
        if not (0 <= x < self.dim_x and 0 <= y < self.dim_y and 0 <= z < self.dim_z):
            raise IndexError(
                f"Global position ({x},{y},{z}) out of bounds "
                f"for {self.dim_x}×{self.dim_y}×{self.dim_z} warehouse"
            )

    def colocar_palet(self, palet_id: str, x: int, y: int, z: int) -> None:
        """Place a registered pallet at global matrix position (x, y, z)."""
        self._validate_global_pos(x, y, z)
        if self._matriz[x][y][z] is not None:
            raise ValueError(f"Global position ({x},{y},{z}) is already occupied")
        if palet_id in self._palet_posiciones:
            raise ValueError(f"Palet {palet_id!r} is already placed in the matrix")
        palet = self.obtener_palet(palet_id)
        self._matriz[x][y][z] = palet
        self._palet_posiciones[palet_id] = (x, y, z)

    def mover_palet(self, palet_id: str, x: int, y: int, z: int) -> None:
        """Move a pallet to a new global position. Both positions must be valid."""
        self._validate_global_pos(x, y, z)
        if palet_id not in self._palet_posiciones:
            raise ValueError(f"Palet {palet_id!r} has no position in the matrix")
        if self._matriz[x][y][z] is not None:
            raise ValueError(f"Target position ({x},{y},{z}) is already occupied")
        ox, oy, oz = self._palet_posiciones[palet_id]
        self._matriz[ox][oy][oz] = None
        palet = self.obtener_palet(palet_id)
        self._matriz[x][y][z] = palet
        self._palet_posiciones[palet_id] = (x, y, z)

    def retirar_palet_de_matriz(self, palet_id: str) -> None:
        """Remove a pallet from the spatial matrix without deleting it from the registry."""
        if palet_id not in self._palet_posiciones:
            return
        x, y, z = self._palet_posiciones.pop(palet_id)
        self._matriz[x][y][z] = None

    def posicion_de_palet(self, palet_id: str) -> Optional[Position3D]:
        """Return the global (x, y, z) of a pallet, or None if unplaced."""
        return self._palet_posiciones.get(palet_id)

    def palet_en(self, x: int, y: int, z: int) -> Optional[Palet]:
        """Return the pallet at global (x, y, z), or None."""
        self._validate_global_pos(x, y, z)
        return self._matriz[x][y][z]

    def buscar_posicion_libre(
        self, zona_id: Optional[str] = None
    ) -> Optional[Position3D]:
        """
        Find the first free global cell, optionally restricted to a named zone.

        Scans in (x, y, z) order — solvers can override this with their own
        placement strategies by using palet_en() / colocar_palet() directly.
        """
        zona = self._zonas.get(zona_id) if zona_id else None
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                for z in range(self.dim_z):
                    if self._matriz[x][y][z] is None:
                        if zona is None or zona.contains(x, y):
                            return (x, y, z)
        return None

    def palets_en_zona(self, zona_id: str) -> list[Palet]:
        """Return all pallets currently placed within a given zone."""
        zona = self._zonas.get(zona_id)
        if zona is None:
            raise KeyError(f"Zone {zona_id!r} not found")
        return [
            self._palets[palet_id]
            for palet_id, (gx, gy, _) in self._palet_posiciones.items()
            if zona.contains(gx, gy)
        ]

    # ── trucks ────────────────────────────────────────────────────────────

    def registrar_camion(self, camion: Camion) -> None:
        if camion.camion_id in self._camiones:
            raise ValueError(f"Truck {camion.camion_id!r} already registered")
        self._camiones[camion.camion_id] = camion

    def obtener_camion(self, camion_id: str) -> Camion:
        if camion_id not in self._camiones:
            raise KeyError(f"Truck {camion_id!r} not found")
        return self._camiones[camion_id]

    def cargar_camion(
        self,
        camion_id: str,
        palet_id: str,
        cx: int,
        cy: int,
    ) -> None:
        """
        Load *palet_id* into truck slot (cx, cy) and remove it from the warehouse matrix.
        """
        camion = self.obtener_camion(camion_id)
        palet = self.obtener_palet(palet_id)
        camion.cargar_palet(palet, cx, cy)
        self.retirar_palet_de_matriz(palet_id)

    def descargar_camion(
        self,
        camion_id: str,
        cx: int,
        cy: int,
        x: int,
        y: int,
        z: int,
    ) -> Palet:
        """
        Unload truck slot (cx, cy) and place the pallet at global position (x, y, z).
        """
        camion = self.obtener_camion(camion_id)
        palet = camion.descargar_palet(cx, cy)
        self.colocar_palet(palet.palet_id, x, y, z)
        return palet

    @property
    def camiones(self) -> list[Camion]:
        return list(self._camiones.values())

    # ── occupancy & statistics ────────────────────────────────────────────

    def consultar_ocupacion(self) -> dict:
        total = self.dim_x * self.dim_y * self.dim_z
        occupied = sum(
            1
            for x in range(self.dim_x)
            for y in range(self.dim_y)
            for z in range(self.dim_z)
            if self._matriz[x][y][z] is not None
        )
        return {
            "total_celdas": total,
            "celdas_ocupadas": occupied,
            "celdas_libres": total - occupied,
            "porcentaje_ocupacion": round(occupied / total * 100, 1) if total else 0.0,
            "num_palets_registrados": len(self._palets),
            "num_palets_colocados": len(self._palet_posiciones),
            "num_productos_registrados": len(self._productos),
        }

    def estadisticas(self) -> dict:
        ocupacion = self.consultar_ocupacion()
        peso_total_kg = round(sum(p.peso_total for p in self._palets.values()), 3)

        zonas_info = []
        for z in self._zonas.values():
            palets_en_zona = sum(
                1
                for pid, (gx, gy, _) in self._palet_posiciones.items()
                if z.contains(gx, gy)
            )
            info = z.to_dict()
            info["palets_colocados"] = palets_en_zona
            info["porcentaje_zona"] = (
                round(palets_en_zona / z.capacidad * 100, 1) if z.capacidad else 0.0
            )
            zonas_info.append(info)

        return {
            "almacen_id": self.almacen_id,
            "dimensiones": {"x": self.dim_x, "y": self.dim_y, "z": self.dim_z},
            "num_toros": self.num_toros,
            "ocupacion_global": ocupacion,
            "peso_total_kg": peso_total_kg,
            "camiones": [c.stats() for c in self._camiones.values()],
            "zonas": zonas_info,
        }

    # ── dunder ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Almacen(id={self.almacen_id!r}, "
            f"{self.dim_x}×{self.dim_y}×{self.dim_z}, "
            f"{len(self._palets)} pallets, "
            f"{len(self._camiones)} trucks, "
            f"{len(self._zonas)} zones)"
        )

    def to_dict(self) -> dict:
        return {
            "almacen_id": self.almacen_id,
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "dim_z": self.dim_z,
            "num_toros": self.num_toros,
            "productos": [p.to_dict() for p in self._productos.values()],
            "palets": [p.to_dict() for p in self._palets.values()],
            "camiones": [c.to_dict() for c in self._camiones.values()],
            "zonas": [z.to_dict() for z in self._zonas.values()],
            "ocupacion": self.consultar_ocupacion(),
        }
