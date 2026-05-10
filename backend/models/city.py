from __future__ import annotations
from backend.models.almacen import Almacen
from backend.models.zona import Zona
from backend.models.tienda import Tienda
from backend.models.pedido import Pedido
from backend.models.ruta import Ruta


class Ciudad:
    """
    Top-level logistics environment.

    Ciudad owns the Almacen and one or more Zonas.  It acts as the
    coordination layer that:
      - exposes cross-zone aggregates (all stores, all orders, all routes)
      - runs consistency validations before and after solver runs
      - emits solver-ready input structures for the global routing problem

    It does not make routing or packing decisions — those are delegated to
    solver classes that operate on the data exposed here.
    """

    def __init__(
        self,
        ciudad_id: str,
        nombre: str,
        almacen: Almacen,
    ) -> None:
        self.ciudad_id = ciudad_id
        self.nombre = nombre
        self.almacen = almacen
        self.zonas: list[Zona] = []

    # ── zone management ───────────────────────────────────────────────────

    def añadir_zona(self, zona: Zona) -> None:
        if any(z.zona_id == zona.zona_id for z in self.zonas):
            raise ValueError(f"Zone {zona.zona_id!r} already registered")
        self.zonas.append(zona)

    def obtener_zona(self, zona_id: str) -> Zona:
        for z in self.zonas:
            if z.zona_id == zona_id:
                return z
        raise KeyError(f"Zone {zona_id!r} not found")

    # ── cross-zone aggregates ─────────────────────────────────────────────

    def tiendas_totales(self) -> list[Tienda]:
        return [t for z in self.zonas for t in z.tiendas]

    def pedidos_totales(self) -> list[Pedido]:
        return [p for z in self.zonas for p in z.pedidos]

    def rutas_totales(self) -> list[Ruta]:
        return [r for z in self.zonas for r in z.rutas]

    def pedidos_pendientes(self) -> list[Pedido]:
        return [p for p in self.pedidos_totales() if p.esta_pendiente]

    def tiendas_con_retornables(self) -> list[Tienda]:
        return [t for t in self.tiendas_totales() if t.tiene_retornables]

    # ── demand aggregation ────────────────────────────────────────────────

    @property
    def demanda_total_cajas(self) -> int:
        return sum(z.demanda_total_cajas for z in self.zonas)

    @property
    def demanda_total_peso(self) -> float:
        return round(sum(z.demanda_total_peso for z in self.zonas), 3)

    @property
    def total_envases_retorno(self) -> int:
        return sum(z.total_envases_retorno for z in self.zonas)

    # ── validation ────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """
        Run all consistency checks and return a list of error strings.
        An empty list means the city is in a valid state.
        """
        errors: list[str] = []

        if not self.zonas:
            errors.append("Ciudad has no zones")

        tienda_ids: set[str] = set()
        pedido_ids: set[str] = set()

        for zona in self.zonas:
            errors.extend(zona.validar())
            for tienda in zona.tiendas:
                if tienda.tienda_id in tienda_ids:
                    errors.append(
                        f"Duplicate tienda_id {tienda.tienda_id!r} "
                        f"across zones"
                    )
                tienda_ids.add(tienda.tienda_id)
                for pedido in tienda.pedidos:
                    if pedido.pedido_id in pedido_ids:
                        errors.append(
                            f"Duplicate pedido_id {pedido.pedido_id!r}"
                        )
                    pedido_ids.add(pedido.pedido_id)

        return errors

    def check_consistency(self) -> bool:
        """Return True if validate() finds no errors."""
        return len(self.validate()) == 0

    def verify_all_deliveries(self) -> list[str]:
        """
        Returns all pedido IDs (no delivery state is tracked on Pedido).
        """
        return [p.pedido_id for p in self.pedidos_totales()]

    def verify_pallet_capacity(self) -> list[str]:
        """Return warnings for any registered pallet that is over capacity."""
        warnings: list[str] = []
        for palet in self.almacen.palets:
            if palet.ocupacion > palet.capacidad_max:
                warnings.append(
                    f"Palet {palet.palet_id!r}: "
                    f"{palet.ocupacion}/{palet.capacidad_max} boxes (overflow)"
                )
        return warnings

    def verify_truck_capacity(self) -> list[str]:
        """Return warnings for any registered truck that is over capacity."""
        warnings: list[str] = []
        for camion in self.almacen.camiones:
            if camion.ocupacion > camion.capacidad_max:
                warnings.append(
                    f"Truck {camion.camion_id!r}: "
                    f"{camion.ocupacion}/{camion.capacidad_max} pallets (overflow)"
                )
        return warnings

    def verify_trazabilidad(self) -> dict:
        """
        Trace every box from order → pallet → route → stop.

        Returns a summary dict; a future solver can use this to detect gaps.
        """
        pedidos = self.pedidos_totales()
        return {
            "total_pedidos": len(pedidos),
            "trazabilidad_completa": False,
        }

    # ── metrics ───────────────────────────────────────────────────────────

    def estadisticas_globales(self) -> dict:
        palets = self.almacen.palets
        camiones = self.almacen.camiones

        pct_palets = (
            round(
                sum(p.porcentaje_ocupacion for p in palets) / len(palets), 1
            )
            if palets else 0.0
        )
        pct_camiones = (
            round(
                sum(c.porcentaje_ocupacion for c in camiones) / len(camiones), 1
            )
            if camiones else 0.0
        )

        return {
            "ciudad_id": self.ciudad_id,
            "nombre": self.nombre,
            "num_zonas": len(self.zonas),
            "num_tiendas": len(self.tiendas_totales()),
            "num_pedidos": len(self.pedidos_totales()),
            "num_pedidos_pendientes": len(self.pedidos_pendientes()),
            "demanda_total_cajas": self.demanda_total_cajas,
            "demanda_total_peso_kg": self.demanda_total_peso,
            "total_envases_retorno": self.total_envases_retorno,
            "num_rutas": len(self.rutas_totales()),
            "almacen": {
                "num_palets": len(palets),
                "num_camiones": len(camiones),
                "pct_ocupacion_media_palets": pct_palets,
                "pct_ocupacion_media_camiones": pct_camiones,
                **self.almacen.consultar_ocupacion(),
            },
            "zonas": [z.metricas() for z in self.zonas],
            "trazabilidad": self.verify_trazabilidad(),
        }

    # ── routing structures for global solvers ─────────────────────────────

    def to_routing_input(
        self,
        depot_x: float = 0.0,
        depot_y: float = 0.0,
    ) -> dict:
        """
        Export a multi-zone routing problem structure.

        Each zone contributes its own VRP-ready sub-problem.  A meta-solver
        can either solve zones independently or combine them into a single
        multi-depot / multi-zone problem.
        """
        return {
            "ciudad_id": self.ciudad_id,
            "depot": {"x": depot_x, "y": depot_y},
            "demanda_total_cajas": self.demanda_total_cajas,
            "num_tiendas": len(self.tiendas_totales()),
            "zonas": [
                z.to_vrp_input(depot_x=depot_x, depot_y=depot_y)
                for z in self.zonas
                if z.matriz is not None
            ],
        }

    # ── serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "ciudad_id": self.ciudad_id,
            "nombre": self.nombre,
            "zonas": [z.to_dict() for z in self.zonas],
            "almacen": self.almacen.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, almacen: Almacen) -> Ciudad:
        ciudad = cls(
            ciudad_id=data["ciudad_id"],
            nombre=data["nombre"],
            almacen=almacen,
        )
        for z_data in data.get("zonas", []):
            ciudad.zonas.append(Zona.from_dict(z_data))
        return ciudad

    def __repr__(self) -> str:
        return (
            f"Ciudad(id={self.ciudad_id!r}, nombre={self.nombre!r}, "
            f"{len(self.zonas)} zonas, "
            f"{len(self.tiendas_totales())} tiendas, "
            f"{len(self.pedidos_totales())} pedidos)"
        )
