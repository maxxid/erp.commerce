"""Servicio de denominaciones de efectivo (contador de caja)."""

from sqlalchemy.orm import Session

from app.models.denominacion import Denominacion

BILLETES_DEFAULT = [100000, 50000, 20000, 10000, 5000, 2000, 1000]
MONEDAS_DEFAULT = [500, 200, 100, 50, 20, 10, 5, 1]

TIPOS_VALIDOS = ("billete", "moneda")


def _normalizar_valor(valor) -> float:
    try:
        v = round(float(valor), 2)
    except (TypeError, ValueError):
        raise ValueError("El valor de la denominación debe ser numérico")
    if v <= 0:
        raise ValueError("El valor de la denominación debe ser mayor a 0")
    if v > 1_000_000_000:
        raise ValueError("El valor de la denominación es demasiado alto")
    return v


def listar(db: Session, incluir_inactivas: bool = False) -> list:
    q = db.query(Denominacion)
    if not incluir_inactivas:
        q = q.filter(Denominacion.activo == True)
    return q.order_by(Denominacion.valor.desc()).all()


def obtener(db: Session, den_id: int):
    return db.query(Denominacion).filter(Denominacion.id == den_id).first()


def crear(db: Session, valor: float, tipo: str = "moneda", activo: bool = True) -> Denominacion:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError("El tipo debe ser 'billete' o 'moneda'")
    v = _normalizar_valor(valor)
    if db.query(Denominacion).filter(Denominacion.valor == v).first():
        raise ValueError(f"Ya existe la denominación de {v:,.0f}".replace(",", "."))
    den = Denominacion(valor=v, tipo=tipo, activo=activo)
    db.add(den)
    db.commit()
    db.refresh(den)
    return den


def actualizar(db: Session, den_id: int, campos: dict):
    den = obtener(db, den_id)
    if not den:
        raise ValueError("Denominación no encontrada")
    cambios = {k: v for k, v in (campos or {}).items() if v is not None}
    if "tipo" in cambios and cambios["tipo"] not in TIPOS_VALIDOS:
        raise ValueError("El tipo debe ser 'billete' o 'moneda'")
    if "valor" in cambios:
        v = _normalizar_valor(cambios["valor"])
        duplicada = (
            db.query(Denominacion)
            .filter(Denominacion.valor == v, Denominacion.id != den_id)
            .first()
        )
        if duplicada:
            raise ValueError(f"Ya existe la denominación de {v:,.0f}".replace(",", "."))
        cambios["valor"] = v
    for campo, valor in cambios.items():
        setattr(den, campo, valor)
    db.commit()
    db.refresh(den)
    return den


def eliminar(db: Session, den_id: int) -> Denominacion:
    den = obtener(db, den_id)
    if not den:
        raise ValueError("Denominación no encontrada")
    db.delete(den)
    db.commit()
    return den


def restaurar_defaults(db: Session) -> int:
    """Reemplaza la lista configurada por los valores por defecto de Argentina."""
    db.query(Denominacion).delete()
    db.flush()
    for valor in BILLETES_DEFAULT:
        db.add(Denominacion(valor=valor, tipo="billete", activo=True))
    for valor in MONEDAS_DEFAULT:
        db.add(Denominacion(valor=valor, tipo="moneda", activo=True))
    db.commit()
    return len(BILLETES_DEFAULT) + len(MONEDAS_DEFAULT)


def asegurar_defaults(db: Session) -> int:
    """Siembra las denominaciones por defecto la primera vez que se usa la tabla."""
    if db.query(Denominacion).first():
        return 0
    return restaurar_defaults(db)
