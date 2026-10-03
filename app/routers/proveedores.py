"""Router de Proveedores: CRUD + cuentas corrientes (deudas y pagos)."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.proveedor import Proveedor
from app.models.proveedor_pago import DeudaProveedor, PagoProveedor
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.services import proveedor_pago_service as pp

router = APIRouter(prefix="/api/proveedores", tags=["Proveedores"])

# Roles que pueden registrar un pago con plata de afuera (afecta_arqueo=False).
#
# La restricción no es burocracia: si el cajero que arquea también pudiera
# declarar un pago que no toca la caja, podría "explicar" plata faltante con un
# pago inventado. Un arqueo vale como prueba sólo si el dinero que el sistema
# dice que salió, salió de verdad.
ROLES_PAGO_EXTERNO = ("admin", "encargado")


class ProveedorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    cuit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    nombre_contacto: Optional[str] = None
    notas: Optional[str] = None


class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    cuit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    nombre_contacto: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


@router.get("", response_model=RespuestaLista)
def listar(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100000),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    query = db.query(Proveedor).filter(Proveedor.activo == True)
    if search:
        like = f"%{search}%"
        query = query.filter(Proveedor.nombre.ilike(like) | Proveedor.cuit.ilike(like))
    total = query.count()
    proveedores = query.order_by(Proveedor.nombre).offset((page - 1) * page_size).limit(page_size).all()
    return RespuestaLista(data=[_prov_to_dict(p) for p in proveedores], total=total, page=page, page_size=page_size)


def _prov_to_dict(p):
    return {"id": p.id, "nombre": p.nombre, "cuit": p.cuit, "telefono": p.telefono,
            "email": p.email, "direccion": p.direccion, "nombre_contacto": p.nombre_contacto,
            "notas": p.notas, "activo": p.activo,
            "saldo_cta_corriente": round(p.saldo_cta_corriente or 0.0, 2),
            "created_at": p.created_at.isoformat() if p.created_at else None} if p else None


@router.get("/{proveedor_id}", response_model=RespuestaData)
def obtener(proveedor_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p: raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return RespuestaData(data=_prov_to_dict(p))


@router.get("/{proveedor_id}/productos", response_model=RespuestaLista)
def productos_de_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Devuelve los productos asociados a un proveedor."""
    from app.models.producto import Producto, producto_proveedor
    from app.services import producto_service

    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    productos = db.query(Producto).join(
        producto_proveedor, Producto.id == producto_proveedor.c.producto_id
    ).filter(
        producto_proveedor.c.proveedor_id == proveedor_id,
        Producto.activo == True
    ).all()

    data = []
    for p in productos:
        rel_data = db.execute(
            producto_proveedor.select().where(
                (producto_proveedor.c.producto_id == p.id) &
                (producto_proveedor.c.proveedor_id == proveedor_id)
            )
        ).first()

        data.append({
            "id": p.id,
            "codigo_barras": p.codigo_barras,
            "nombre": p.nombre,
            "marca": p.marca,
            "precio_venta": p.precio_venta,
            "precio_costo": p.precio_costo,
            "stock_actual": producto_service._suma_lotes_activos(db, p.id),
            "imagen_url": p.imagen_url,
            "costo_proveedor": rel_data.costo if rel_data else None,
            "codigo_proveedor": rel_data.codigo_proveedor if rel_data else None,
        })
    
    return RespuestaLista(
        data=data,
        total=len(data),
        message=f"{len(data)} producto(s)"
    )


@router.post("", response_model=RespuestaData)
def crear(data: ProveedorCreate, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    p = Proveedor(**data.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return RespuestaData(data=_prov_to_dict(p), message="Proveedor creado")


@router.put("/{proveedor_id}", response_model=RespuestaData)
def actualizar(proveedor_id: int, data: ProveedorUpdate, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p: raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(p, k, v)
    db.commit(); db.refresh(p)
    return RespuestaData(data=_prov_to_dict(p), message="Proveedor actualizado")


# ---------------------------------------------------------------------------
# Cuentas corrientes: deudas y pagos
# ---------------------------------------------------------------------------


class DeudaCreate(BaseModel):
    monto: float = Field(..., gt=0)
    origen: str = Field("manual")  # compra | encargo | manual
    compra_id: Optional[int] = None
    detalle: str = ""
    fecha_vencimiento: Optional[datetime] = None


class PagoCreate(BaseModel):
    monto: float = Field(..., gt=0)
    medio_pago: str = Field("efectivo")
    deuda_id: Optional[int] = None
    comprobante_nro: str = ""
    descripcion: str = ""
    # False = la plata vino de afuera: reduce la deuda pero no toca el cajón.
    afecta_arqueo: bool = True
    cierre_id: Optional[int] = None
    sucursal_id: int = 1
    fecha: Optional[datetime] = None


class AnularRequest(BaseModel):
    motivo: str = ""


def _deuda_to_dict(d: DeudaProveedor) -> dict:
    return {
        "id": d.id,
        "proveedor_id": d.proveedor_id,
        "origen": d.origen,
        "compra_id": d.compra_id,
        "detalle": d.detalle,
        "monto_original": round(d.monto_original, 2),
        "saldo": round(d.saldo, 2),
        "pagada": round(d.pagada, 2),
        "estado": d.estado,
        "fecha_emision": d.fecha_emision.isoformat() if d.fecha_emision else None,
        "fecha_vencimiento": d.fecha_vencimiento.isoformat() if d.fecha_vencimiento else None,
    }


def _pago_to_dict(p: PagoProveedor) -> dict:
    return {
        "id": p.id,
        "proveedor_id": p.proveedor_id,
        "proveedor_nombre": p.proveedor_nombre,
        "monto": round(p.monto, 2),
        "medio_pago": p.medio_pago,
        "fecha": p.fecha.isoformat() if p.fecha else None,
        "deuda_id": p.deuda_id,
        "comprobante_nro": p.comprobante_nro,
        "descripcion": p.descripcion,
        "afecta_arqueo": p.afecta_arqueo,
        "sesion_cierre_id": p.sesion_cierre_id,
        "movimiento_caja_id": p.movimiento_caja_id,
        "anulado": p.anulado,
        "verificado": p.verificado,
        "motivo_anulacion": p.motivo_anulacion,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _exigir_proveedor(db: Session, proveedor_id: int) -> Proveedor:
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return p


def _http_error(fn, *args, **kwargs):
    """Traduce ValueError del servicio a 400 con el mensaje que ya está en español."""
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{proveedor_id}/estado-cuenta", response_model=RespuestaData)
def estado_cuenta(proveedor_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Resumen de la cuenta corriente: qué se debe, qué se pagó, qué falta."""
    _exigir_proveedor(db, proveedor_id)
    estado = _http_error(pp.estado_cuenta, db, proveedor_id)
    return RespuestaData(data=estado)


@router.get("/{proveedor_id}/deudas", response_model=RespuestaLista)
def listar_deudas(
    proveedor_id: int,
    estado: Optional[str] = Query(None),
    solo_vencidas: bool = Query(False),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    _exigir_proveedor(db, proveedor_id)
    deudas = _http_error(pp.listar_deudas, db, proveedor_id, estado, solo_vencidas)
    return RespuestaLista(data=[_deuda_to_dict(d) for d in deudas], total=len(deudas))


@router.post("/{proveedor_id}/deudas", response_model=RespuestaData)
def crear_deuda(
    proveedor_id: int,
    data: DeudaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    _exigir_proveedor(db, proveedor_id)
    deuda = _http_error(
        pp.crear_deuda,
        db,
        proveedor_id,
        data.monto,
        user.id,
        data.origen,
        data.compra_id,
        data.detalle,
        data.fecha_vencimiento,
    )
    db.commit()
    db.refresh(deuda)
    return RespuestaData(data=_deuda_to_dict(deuda), message="Deuda registrada")


@router.post("/{proveedor_id}/deudas/{deuda_id}/anular", response_model=RespuestaData)
def anular_deuda(
    proveedor_id: int,
    deuda_id: int,
    data: AnularRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    deuda = db.query(DeudaProveedor).filter(
        DeudaProveedor.id == deuda_id, DeudaProveedor.proveedor_id == proveedor_id
    ).first()
    if not deuda:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    _http_error(pp.anular_deuda, db, deuda_id, user.id)
    db.commit()
    return RespuestaData(data=_deuda_to_dict(deuda), message="Deuda anulada")


@router.get("/{proveedor_id}/pagos", response_model=RespuestaLista)
def listar_pagos(
    proveedor_id: int,
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    _exigir_proveedor(db, proveedor_id)
    pagos = _http_error(pp.listar_pagos, db, proveedor_id, solo_activos)
    return RespuestaLista(data=[_pago_to_dict(p) for p in pagos], total=len(pagos))


@router.post("/{proveedor_id}/pagos", response_model=RespuestaData)
def registrar_pago(
    proveedor_id: int,
    data: PagoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado", "cajero")),
):
    """Registra un pago al proveedor.

    Todos los roles pueden pagar con plata de la caja: es una operación normal
    del mostrador y tiene que reflejar el egreso. Lo que no puede hacer un cajero
    es registrar un pago con afecta_arqueo=False, porque un pago que no toca el
    cajón es exactamente el mecanismo con el que se podría tapar plata faltante
    en el arqueo.
    """
    _exigir_proveedor(db, proveedor_id)
    if not data.afecta_arqueo and user.rol not in ROLES_PAGO_EXTERNO:
        raise HTTPException(
            status_code=403,
            detail=(
                "Los pagos con plata de afuera sólo los puede registrar un "
                "encargado o el dueño. Si el pago salió del cajón, marcalo "
                "como pago del cajón para que el arqueo lo refleje."
            ),
        )
    pago = _http_error(
        pp.registrar_pago,
        db,
        proveedor_id,
        data.monto,
        user.id,
        data.medio_pago,
        data.deuda_id,
        data.comprobante_nro,
        data.descripcion,
        data.afecta_arqueo,
        data.cierre_id,
        data.sucursal_id,
        data.fecha,
    )
    db.commit()
    db.refresh(pago)

    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    mensaje = "Pago registrado"
    if not pago.verificado:
        # Se registra igual, pero avisamos: queda para revisar. Un anticipo es
        # totalmente legítimo; lo que no queremos es que se pierda de vista.
        mensaje += " (sin verificar: queda en la lista de pagos a revisar)"
    return RespuestaData(
        data={**_pago_to_dict(pago), "saldo_proveedor": round(proveedor.saldo_cta_corriente, 2)},
        message=mensaje,
    )


@router.post("/{proveedor_id}/pagos/{pago_id}/anular", response_model=RespuestaData)
def anular_pago(
    proveedor_id: int,
    pago_id: int,
    data: AnularRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Anula un pago: vuelve el saldo al proveedor y saca el egreso del cajón."""
    pago = db.query(PagoProveedor).filter(
        PagoProveedor.id == pago_id, PagoProveedor.proveedor_id == proveedor_id
    ).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    _http_error(pp.anular_pago, db, pago_id, user.id, data.motivo)
    db.commit()
    db.refresh(pago)
    return RespuestaData(data=_pago_to_dict(pago), message="Pago anulado")


@router.get("/pagos-sin-verificar/listado", response_model=RespuestaLista)
def pagos_sin_verificar(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Pagos sin deuda asociada o sin comprobante: los que hay que revisar.

    Todos los roles ven la lista; la idea es que el cajero sepa que su pago quedó
    marcado y el dueño lo resuelva después, no que se entere al final del mes.
    """
    pagos = pp.pagos_sin_verificar(db)
    return RespuestaLista(
        data=[_pago_to_dict(p) for p in pagos],
        total=len(pagos),
        message=f"{len(pagos)} pago(s) sin verificar",
    )
