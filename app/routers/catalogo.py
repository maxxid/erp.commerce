"""Router de Catálogo: exportar, subir/bajar, importar catálogo de productos."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaBase, RespuestaData, RespuestaLista
from app.services import catalogo_service, backup_service

router = APIRouter(prefix="/api/catalogo", tags=["Catálogo"])


class ImportarRequest(BaseModel):
    data: list  # lista de productos o dict con clave 'productos'


@router.get("/estado", response_model=RespuestaData)
def estado(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    """Estado del catálogo: exportables, catálogo cargado, último export."""
    return RespuestaData(data=catalogo_service.estado_catalogo(db), message="Estado del catálogo")


@router.post("/exportar", response_model=RespuestaData)
def exportar(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    """Exporta productos a JSON local y sube a R2 si está configurado."""
    data = catalogo_service.exportar_productos(db)
    subido = catalogo_service.subir_catalogo_a_r2(db)
    catalogo_service.exportar_a_json(db)
    return RespuestaData(
        data={"exportados": data["total_productos"], "subido_r2": subido},
        message=f"{data['total_productos']} producto(s) exportados" + (" y subidos a R2" if subido else ""),
    )


@router.get("/r2", response_model=RespuestaLista)
def listar_r2(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    """Lista archivos de catálogo en R2."""
    r2_cfg = backup_service._get_r2_config(db)
    if not r2_cfg:
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    archivos = catalogo_service.listar_catalogos_r2(db)
    return RespuestaLista(data=archivos, total=len(archivos), message=f"{len(archivos)} archivo(s)")


@router.post("/descargar", response_model=RespuestaData)
def descargar(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    """Descarga el catálogo central desde R2 (catalogo/{machine_id}/productos.json)."""
    path = catalogo_service.descargar_catalogo_central(db)
    if not path:
        raise HTTPException(status_code=404, detail="No se pudo descargar el catálogo central")
    return RespuestaData(data={"path": path}, message="Catálogo central descargado")


@router.post("/recargar", response_model=RespuestaData)
def recargar(user: Usuario = Depends(require_role("admin", "encargado"))):
    """Recarga el catálogo local (catalogo_completo.json) en memoria."""
    total = catalogo_service.cargar_catalogo_memoria(force=True)
    return RespuestaData(data={"total": total}, message=f"Catálogo recargado: {total} producto(s)")


@router.post("/importar", response_model=RespuestaData)
def importar(data: ImportarRequest, user: Usuario = Depends(require_role("admin", "encargado"))):
    """Importa un catálogo mergeado (guarda en catalogo_completo.json y carga en memoria)."""
    total = catalogo_service.importar_catalogo(data.data)
    return RespuestaData(data={"importados": total}, message=f"{total} producto(s) importados al catálogo")


@router.get("/lookup/{barcode}", response_model=RespuestaData)
def lookup_catalogo(barcode: str, user: Usuario = Depends(require_role("admin", "encargado", "cajero", "repositor"))):
    """Busca un código de barras en el catálogo central cargado."""
    result = catalogo_service.buscar_en_catalogo(barcode)
    if result:
        return RespuestaData(data=result, message="Encontrado en catálogo central")
    raise HTTPException(status_code=404, detail="No encontrado en catálogo central")
