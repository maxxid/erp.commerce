"""Router del panel de recategorización.

Cuatro rutas, siempre en este orden:

1. `GET  /sugerencias/candidatos`  → qué hay que revisar (sugerencia local ya calculada)
1b. `GET  /sugerencias/ids`        → todos los ids del filtro, para "Seleccionar todo"
2. `POST /sugerencias/ia`          → segundo parecer, en lotes (requiere el plan con IA)
3. `POST /aplicar-sugerencias`     → el único que escribe, y recibe lo que eligió una persona
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role, requiere_feature
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData
from app.schemas.recategorizar import (
    AplicarRequest,
    AplicarResultado,
    CandidatosPage,
    SugerenciaIds,
    SugerenciasIAOut,
    SugerenciasIARequest,
)
from app.services import auditoria_service, categorizacion_service as servicio

router = APIRouter(prefix="/api/productos", tags=["Recategorización"])


@router.get("/sugerencias/candidatos", response_model=RespuestaData[CandidatosPage])
def listar_candidatos(
    modo: str = Query("pendientes", pattern="^(pendientes|sin_categoria|general|todos)$"),
    q: str = Query("", max_length=80),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Productos a revisar, con la sugerencia del motor local ya calculada."""
    filas, total = servicio.candidatos(
        db, modo=modo, q=q, page=page, page_size=page_size
    )
    return RespuestaData(
        data=CandidatosPage(items=filas, total=total, page=page, page_size=page_size),
        message=f"{total} producto(s) para revisar",
    )


@router.get("/sugerencias/ids", response_model=RespuestaData[SugerenciaIds])
def listar_ids_candidatos(
    modo: str = Query("pendientes", pattern="^(pendientes|sin_categoria|general|todos)$"),
    q: str = Query("", max_length=80),
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Todos los ids del filtro: el "Seleccionar todo" no se queda en una página."""
    ids, total = servicio.ids_candidatos(db, modo=modo, q=q)
    return RespuestaData(
        data=SugerenciaIds(ids=ids, total=total),
        message=f"{total} producto(s) para seleccionar",
    )


@router.post("/sugerencias/ia", response_model=RespuestaData[SugerenciasIAOut])
def sugerir_con_ia(
    body: SugerenciasIARequest,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_role("admin", "encargado")),
    _plan: Usuario = Depends(requiere_feature("ia")),
):
    """Segundo parecer del LLM para un lote chico. 402 si el plan no incluye IA."""
    from app.services.ia import registro
    from app.services.ia.proveedor import ErrorProveedor, IADeshabilitada, LimiteAgotado

    ids = list(dict.fromkeys(body.productos_ids))[: servicio.TAMANO_LOTE_IA]
    filas, nombre_por_id = servicio.detalle(db, ids)
    if not filas:
        raise HTTPException(status_code=400, detail="Sin productos para analizar")

    cat = servicio.catalogo(db)
    try:
        respuesta = registro.completar(
            db,
            sistema=servicio.SISTEMA_IA,
            usuario=servicio.prompt_ia(filas, cat),
            como_json=True,
            max_tokens=2048,
            temperatura=0.0,
        )
    except IADeshabilitada as err:
        raise HTTPException(status_code=402, detail=str(err))
    except LimiteAgotado as err:
        raise HTTPException(status_code=409, detail=str(err))
    except ErrorProveedor as err:
        raise HTTPException(status_code=502, detail=f"El proveedor de IA falló: {err}")

    try:
        lote = servicio.interpretar_ia(respuesta.texto, filas, cat)
    except ValueError as err:
        raise HTTPException(status_code=502, detail=f"Respuesta ilegible de la IA: {err}")

    for item in lote:
        item["categoria_actual"] = nombre_por_id.get(item["categoria_actual_id"]) or item["categoria_actual"]

    return RespuestaData(
        data=SugerenciasIAOut(
            lote=lote,
            ignorados=max(0, len(filas) - len(lote)),
            tokens_out=respuesta.tokens_out or 0,
        ),
        message=f"{len(lote)} sugerencia(s) para revisar",
    )


@router.post("/aplicar-sugerencias", response_model=RespuestaData[AplicarResultado])
def aplicar_sugerencias(
    body: AplicarRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Escribe las categorías que confirmó la persona. Acá se mueve de verdad."""
    if len(body.cambios) > 500:
        raise HTTPException(status_code=400, detail="Máximo 500 cambios por operación")

    cambios = [c.model_dump() for c in body.cambios]
    resultado = servicio.aplicar(db, cambios)

    if resultado["aplicados"] or resultado["categorias_creadas"]:
        auditoria_service.registrar(
            db,
            user.id,
            "recategorizacion_producto",
            None,
            None,
            {
                "aplicados": resultado["aplicados"],
                "creadas": resultado["categorias_creadas"],
                "producto_ids": [c.get("producto_id") for c in cambios][:50],
            },
        )

    return RespuestaData(
        data=resultado,
        message=f"{resultado['aplicados']} producto(s) recategorizado(s)",
    )
