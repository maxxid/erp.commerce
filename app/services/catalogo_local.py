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

Con los 567 productos activos de hoy el JSON pesa ~0,41 MB. Para no bajar eso
en cada apertura está `version_local()`: ~100 bytes que dicen si algo cambió.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session


def _iso(valor) -> Optional[str]:
    """SQLite devuelve el max() de una fecha como texto, otros dialectos como datetime."""
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def version_local(db: Session) -> dict[str, Any]:
    """Versión chiquita del catálogo (~100 bytes).

    Es lo que permite refrescar sin bajar 0,41 MB: si esto no cambió, no hay
    nada que descargar.

    Incluye el **stock de los lotes**, que es la parte que evita el error feo:
    una venta mueve lotes sin tocar `productos.updated_at`, así que mirando
    solamente los productos el POS se quedaría mostrando un stock que ya no
    existe. Ante la duda la versión cambia y se baja el completo — nunca
    conviene quedar con datos viejos por ahorrar unos bytes.
    """
    from app.models.categoria import Categoria
    from app.models.lote import Lote
    from app.models.oferta import Oferta
    from app.models.producto import Producto

    def firma(modelo, filtro, fecha="updated_at"):
        cantidad, modificado = (
            db.query(func.count(modelo.id), func.max(getattr(modelo, fecha)))
            .filter(filtro)
            .one()
        )
        return {"cantidad": int(cantidad or 0), "modificado": _iso(modificado)}

    # `Categoria` es el único de estos modelos sin `updated_at`: tiene nomás
    # `created_at`, con lo que una edición de nombre quedaría invisible. En vez
    # de agregar una columna sólo por esto, se miran las categorías enteras
    # —son 10 y cambian muy poco—: así la versión cambia con cualquier alta,
    # baja o renombre, sin migración.
    activas = (
        db.query(Categoria.id, Categoria.nombre)
        .filter(Categoria.activo == True)
        .order_by(Categoria.id)
        .all()
    )

    lotes, unidades = (
        db.query(func.count(Lote.id), func.sum(Lote.cantidad_actual))
        .filter(Lote.activo == True)
        .one()
    )

    return {
        "productos": firma(Producto, Producto.activo == True),
        "categorias": {
            "cantidad": len(activas),
            "detalle": "|".join(f"{c.id}:{c.nombre}" for c in activas),
        },
        "ofertas": firma(Oferta, Oferta.activo == True),
        # El total de unidades es la red de seguridad: cualquier venta lo mueve
        # aunque ninguna otra tabla cambie.
        "stock": {"lotes": int(lotes or 0), "unidades": float(unidades or 0)},
    }


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
    """El catálogo entero, con la fecha y la versión con que se armó, para guardar en el navegador."""
    # Se importan acá adentro: estos módulos cuelgan de app.services, cuyo
    # __init__ importa producto_service, que importa los modelos. Importarlos
    # arriba del todo arma un circuito.
    from app.routers.ofertas import _oferta_to_dict
    from app.services import oferta_service, producto_service

    # La versión se calcula ANTES de listar. Si se calculara después, una venta
    # que llegara mientras se arma el snapshot quedaría registrada como "ya está
    # al día" y ese cambio no se volvería a bajar nunca.
    version = version_local(db)

    productos, total_productos = producto_service.listar_productos(
        db, solo_activos=True, page=1, page_size=100000,
    )
    ofertas, total_ofertas = oferta_service.listar_ofertas(
        db, page=1, page_size=100000,
    )

    return {
        "version": version,
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
