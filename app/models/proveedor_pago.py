"""
Modelos de cuentas corrientes con proveedores.

Son el análogo invertido de lo que ya hace Cliente con saldo_cta_corriente.
La diferencia clave es que acá el pago importa por partida doble:

    -.reduce la deuda con el proveedor (motivo por el que existe DeudaProveedor)
    -y además puede mover la caja de una sesión, o no hacerlo

Esa segunda mitad es lo que hace que el arqueo de un cajero sea verídico. Un
pago hecho con plata de la sesión tiene que bajar el esperado del cajón, porque
esa plata efectivamente salió. Un pago hecho con plata de afuera no puede tocar
el cajón del cajero, porque esa plata nunca estuvo ahí. Por eso PagoProveedor
guarda afecta_arqueo y no se apoya solo en MovimientoCaja.

Sobre el saldo del proveedor: es una caché. La verdad siempre son las filas de
DeudaProveedor y PagoProveedor. recalcular_saldo() es el único que escribe ahí,
y los tests lo cubren para que no se desincronice.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class DeudaProveedor(Base):
    """Obligación pendiente con un proveedor.

    Es la causa de un pago. Puede originarse en una compra, en un encargo
    (pedido hecho al proveedor que todavía no llegó) o cargarse a mano para
    saldar deuda de servicios o mercadería recibido fuera del circuito de
    compras.
    """

    __tablename__ = "deudas_proveedor"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    origen = Column(String(20), nullable=False, default="manual")  # compra | encargo | manual
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=True, index=True)

    detalle = Column(String(200), nullable=True)
    monto_original = Column(Float, nullable=False)
    saldo = Column(Float, nullable=False)

    fecha_emision = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    fecha_vencimiento = Column(DateTime, nullable=True)

    estado = Column(String(20), nullable=False, default="pendiente")  # pendiente | parcial | cancelada
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    proveedor = relationship("Proveedor", back_populates="deudas")
    pagos = relationship(
        "PagoProveedor", back_populates="deuda", cascade="all, delete-orphan"
    )

    @property
    def pagada(self) -> float:
        """Cuánto se le pagó de más: saldo negativo significa anticipo."""
        return round(self.monto_original - self.saldo, 2)

    def __repr__(self):
        return (
            f"<DeudaProveedor(id={self.id}, proveedor_id={self.proveedor_id}, "
            f"origen='{self.origen}', saldo={self.saldo})>"
        )


class PagoProveedor(Base):
    """Pago hecho a un proveedor.

    Guarda su propio registro en vez de depender de MovimientoCaja porque un
    pago necesita más datos de los que el movimiento de caja soporta: a qué
    deuda se aplica, con qué comprobante se respaldó y si tocó o no la caja de
    la sesión.

    Cuando afecta_arqueo es True, además queda el MovimientoCaja espejo que
    baja el esperado del cajón. Ese espejo es lo que hace que el arqueo siga
    siendo verídico: el dinero físico y el registro contable cuentan lo mismo.

    afecta_arqueo en False es para pagos con plata de afuera. El pago existe
    contablemente y reduce la deuda, pero no pertenece a ninguna sesión de caja
    y por lo tanto no puede tocar el esperado de un cajero. Esa separación es
    lo que impide "justificar" plata faltante.
    """

    __tablename__ = "pagos_proveedor"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    monto = Column(Float, nullable=False)
    medio_pago = Column(String(30), nullable=False, default="efectivo")
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # A qué deuda se aplica. Null = anticipo o pago a cuenta, sin causa
    # concreta todavia. Es lo que marca el pago como "sin verificar".
    deuda_id = Column(Integer, ForeignKey("deudas_proveedor.id"), nullable=True, index=True)
    # Copia del nombre para que un pago no dependa del join con Proveedor
    # (que se puede renombrar o dar de baja).
    proveedor_nombre = Column(String(150), nullable=True)
    # Respaldo documental: número de factura o recibo del proveedor.
    comprobante_nro = Column(String(50), nullable=True)
    descripcion = Column(String(200), nullable=True)

    # La mitad que decide si el arqueo del cajero dice la verdad o miente.
    # False = plata de afuera, no toca ninguna sesión de caja.
    afecta_arqueo = Column(Boolean, default=True, nullable=False)
    # Sesión de caja a la que pertenece el movimiento espejo. Solo si afecta_arqueo.
    sesion_cierre_id = Column(Integer, nullable=True)
    # Movimiento de caja espejo. Necesario para anular el pago en caja.
    movimiento_caja_id = Column(Integer, ForeignKey("movimientos_caja.id"), nullable=True)

    anulado = Column(Boolean, default=False, nullable=False)
    anulado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    anulado_at = Column(DateTime, nullable=True)
    motivo_anulacion = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    proveedor = relationship("Proveedor", back_populates="pagos")
    deuda = relationship("DeudaProveedor", back_populates="pagos")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    anulado_por = relationship("Usuario", foreign_keys=[anulado_por_id])

    @property
    def verificado(self) -> bool:
        """Respaldo suficiente: tiene causa y comprobante.

        Un pago que no cumple esto sigue siendo válido (puede ser un anticipo o
        un pago informal), pero queda en la lista de "sin verificar" para que
        el dueño lo revise. Preferimos que el cajero pueda operar y que quede
        rastro, antes que bloquearle el mostrador y que busque el rodeo.
        """
        return bool(self.deuda_id and self.comprobante_nro)

    def __repr__(self):
        return (
            f"<PagoProveedor(id={self.id}, proveedor_id={self.proveedor_id}, "
            f"monto={self.monto}, afecta_arqueo={self.afecta_arqueo})>"
        )