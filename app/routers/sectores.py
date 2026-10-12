"""Router de Sectores: agrupaciones físicas del local (estantes, góndolas).

Se usan para ordenar y filtrar la impresión de etiquetas por dónde van
colocadas. El nombre se valida contra los sectores activos (no hay unique en la
DB) para que un sector borrado no bloquee volver a crearlo.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.producto import Producto
from app.models.sector import Sector
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData, RespuestaLista
from app.schemas.sector import SectorCreate, SectorOut, SectorUpdate

router = APIRouter(prefix="/api/sectores", tags=["Sectores"])


def _conteos(db: Session) -> dict:
    """Un solo query en vez de contar los productos de cada sector."""
    filas = (
        db.query(Producto.sector_id, func.count(Producto.id))
        .filter(Producto.activo == True, Producto.sector_id.isnot(None))
        .group_by(Producto.sector_id)
        .all()
    )
    return {sector_id: total for sector_id, total in filas}


def _a_out(sector: Sector, conteos: dict) -> SectorOut:
    return SectorOut(
        id=sector.id,
        nombre=sector.nombre,
        orden=sector.orden,
        activo=sector.activo,
        cantidad_productos=conteos.get(sector.id, 0),
    )


def _buscar_activo(db: Session, nombre: str) -> Sector | None:
    limpio = (nombre or "").strip().lower()
    if not limpio:
        return None
    return (
        db.query(Sector)
        .filter(Sector.activo == True, func.lower(Sector.nombre) == limpio)
        .first()
    )


@router.get("", response_model=RespuestaLista[SectorOut])
def listar(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista los sectores activos con cuántos productos tiene cada uno."""
    sectores = db.query(Sector).filter(Sector.activo == True).order_by(Sector.orden, Sector.nombre).all()
    conteos = _conteos(db)
    data = [_a_out(s, conteos) for s in sectores]
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} sector(es)")


@router.post("", response_model=RespuestaData[SectorOut])
def crear(
    data: SectorCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea un sector. Si ya existe activo lo devuelve; si estaba borrado, lo reactiva."""
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del sector no puede estar vacío")

    existente = _buscar_activo(db, nombre)
    if existente:
        conteos = _conteos(db)
        return RespuestaData(
            data=_a_out(existente, conteos),
            message=f"El sector '{existente.nombre}' ya existía",
        )

    # Reactivar uno borrado con el mismo nombre en vez de duplicarlo.
    borrado = (
        db.query(Sector)
        .filter(Sector.activo == False, func.lower(Sector.nombre) == nombre.lower())
        .first()
    )
    if borrado:
        borrado.nombre = nombre
        borrado.activo = True
        if data.orden:
            borrado.orden = data.orden
        db.commit()
        db.refresh(borrado)
        return RespuestaData(data=_a_out(borrado, {}), message="Sector reactivado")

    sector = Sector(nombre=nombre, orden=data.orden)
    db.add(sector)
    db.commit()
    db.refresh(sector)
    return RespuestaData(data=_a_out(sector, {}), message="Sector creado")


@router.put("/{sector_id}", response_model=RespuestaData[SectorOut])
def actualizar(
    sector_id: int,
    data: SectorUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Renombra o reordena un sector."""
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector or not sector.activo:
        raise HTTPException(status_code=404, detail="Sector no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        nombre = (cambios["nombre"] or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del sector no puede estar vacío")
        chocan = _buscar_activo(db, nombre)
        if chocan and chocan.id != sector_id:
            raise HTTPException(status_code=400, detail="Ya existe un sector con ese nombre")
        sector.nombre = nombre
    if "orden" in cambios and cambios["orden"] is not None:
        sector.orden = cambios["orden"]

    db.commit()
    db.refresh(sector)
    return RespuestaData(data=_a_out(sector, _conteos(db)), message="Sector actualizado")


@router.delete("/{sector_id}", response_model=RespuestaData)
def eliminar(
    sector_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Desactiva un sector y libera los productos que apuntaban a él."""
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector or not sector.activo:
        raise HTTPException(status_code=404, detail="Sector no encontrado")

    afectados = (
        db.query(func.count(Producto.id))
        .filter(Producto.sector_id == sector_id)
        .scalar()
        or 0
    )
    db.query(Producto).filter(Producto.sector_id == sector_id).update(
        {"sector_id": None}, synchronize_session=False
    )
    sector.activo = False
    db.commit()

    detalle = f"Sector '{sector.nombre}' desactivado"
    if afectados:
        detalle += f"; {afectados} producto(s) quedaron sin sector"
    return RespuestaData(data={"productos_afectados": afectados}, message=detalle)
