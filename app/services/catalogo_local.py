"""Snapshot del catálogo para poder vender sin conexión.

El POS baja productos, categorías y ofertas por separado cada vez que arranca.
Cuando se corta la internet, el navegador no tenía con qué vender: el service
worker sí cachea esas respuestas, pero solo para las URLs exactas que se
pidieron antes y **sin fecha**, así que no hay forma de saber si el precio que
se está cobrando es de hoy o de hace dos meses.

Este snapshot junta las tres listas en una sola respuesta con un solo
`generado`, y usa los mismos serializadores que los endpoints normales: lo que
se ve offline tiene que ser idéntico a lo que se ve online. Si no fuera así, el
catálogo offline sería una segunda verdad que eventualmente contradice a la
primera.

Con los 567 productos activos de hoy el JSON pesa ~0,4 MB, así que entra de
sobra en el almacenamiento del navegador. Si el catálogo crece mucho y deja de
caber, toca moverlo a IndexedDB (está anotado en PENDIENTES.md).
"""

from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session


def _categorias(db: Session) -> list:
    """Misma consulta y mismo schema que GET /api/categorias."""
    from app.models.categoria import Categoria
    from app.schemas.categoria import CategoriaOut

    categorias = (
        db.query(Categoria)
        .filter(Categoria.activo == True)
        .order_by(Categoria.nombre)
        .all()
    )
    for cat in categorias:
        cat.cantidad_productos = len(cat.productos)
    return [CategoriaOut.model_validate(c).model_dump() for c in categorias]


def snapshot_local(db: Session) -> dict[str, Any]:
    """El catálogo entero, con la fecha en que se armó, para guardar en el navegador."""
    # Se importan acá adentro: estos módulos cuelgan de app.services, cuyo
    # __init__ importa producto_service, que importa los modelos. Importarlos
    # arriba del todo arma un circuito.
    from app.routers.ofertas import _oferta_to_dict
    from app.services import oferta_service, producto_service

    productos, total_productos = producto_service.listar_productos(
        db, solo_activos=True, page=1, page_size=100000,
    )
    ofertas, total_ofertas = oferta_service.listar_ofertas(
        db, page=1, page_size=100000,
    )

    return {
        # La fecha es lo que le permite al POS avisar "estás cobrando con
        # precios de hace 3 horas" en vez de fingir que tiene datos frescos.
        "generado": datetime.now(timezone.utc).isoformat(),
        "productos": jsonable_encoder(productos),
        "categorias": _categorias(db),
        "ofertas": [_oferta_to_dict(o) for o in ofertas],
        "totales": {
            "productos": total_productos,
            "ofertas": total_ofertas,
        },
    }
