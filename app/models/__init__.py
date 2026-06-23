"""
Import centralizado de todos los modelos.

Importar este módulo garantiza que todos los modelos estén registrados
en Base.metadata antes de crear las tablas.
"""

from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario, Sucursal
from app.models.venta import Venta, VentaItem
from app.models.compra import Compra, CompraItem
from app.models.movimiento_stock import MovimientoStock
from app.models.movimiento_caja import MovimientoCaja
from app.models.configuracion import Configuracion
from app.models.auditoria import Auditoria
from app.models.licencia import Licencia
from app.models.oferta import Oferta

__all__ = [
    "Categoria",
    "Producto",
    "Cliente",
    "Proveedor",
    "Usuario",
    "Sucursal",
    "Venta",
    "VentaItem",
    "Compra",
    "CompraItem",
    "MovimientoStock",
    "MovimientoCaja",
    "Configuracion",
    "Auditoria",
    "Licencia",
    "Oferta",
]
