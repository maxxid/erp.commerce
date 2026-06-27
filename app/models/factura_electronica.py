"""Modelo de Factura Electrónica AFIP."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from app.database import Base


class FacturaElectronica(Base):
    """Registro de cada factura electrónica emitida ante AFIP."""

    __tablename__ = "facturas_electronicas"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    venta_numero = Column(String(20), nullable=False)

    tipo = Column(String(2), nullable=False, default="11")  # 11=Factura C
    punto_venta = Column(Integer, nullable=False, default=1)
    numero_fiscal = Column(Integer, nullable=True)  # Número de comprobante AFIP

    cae = Column(String(14), nullable=True)  # Código de Autorización Electrónico
    vencimiento_cae = Column(DateTime, nullable=True)
    resultado = Column(String(20), nullable=True)  ########""A"=Aprobado, "R"=Rechazado

    total = Column(Float, nullable=False, default=0.0)
    neto = Column(Float, nullable=False, default=0.0)
    iva = Column(Float, nullable=False, default=0.0)

    tipo_doc_comprador = Column(Integer, nullable=True, default=99)  # 99=Cons Final
    nro_doc_comprador = Column(String(20), nullable=True, default="0")

    observaciones = Column(Text, nullable=True)

    estado = Column(String(20), nullable=False, default="pendiente")  # pendiente/emitida/rechazada/anulada
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    emitted_at = Column(DateTime, nullable=True)
