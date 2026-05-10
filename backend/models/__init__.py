from backend.models.product import Product, OrderLine, Order
from backend.models.palet import Palet
from backend.models.truck import (
    Side,
    PalletSlot,
    PalletAssignment,
    LoadPlan,
    build_truck_slots,
    AperturaTipo,
    TipoCamion,
    Camion,
    Furgoneta,
    CamionMediano,
    CamionGrande,
    CamionFactory,
)
from backend.models.almacen import ZonaAlmacen, Almacen
from backend.models.pedido import Pedido
from backend.models.tienda import Tienda
from backend.models.ruta import Parada, Ruta
from backend.models.zona import Zona, TipoMatriz
from backend.models.city import Ciudad

__all__ = [
    # product
    "Product",
    "OrderLine",
    "Order",
    # palet
    "Palet",
    # truck – solver layer
    "Side",
    "PalletSlot",
    "PalletAssignment",
    "LoadPlan",
    "build_truck_slots",
    # truck – warehouse layer
    "AperturaTipo",
    "TipoCamion",
    "Camion",
    "Furgoneta",
    "CamionMediano",
    "CamionGrande",
    "CamionFactory",
    # almacen
    "ZonaAlmacen",
    "Almacen",
    # logistics domain
    "Pedido",
    "Tienda",
    "Parada",
    "Ruta",
    "Zona",
    "TipoMatriz",
    "Ciudad",
]
