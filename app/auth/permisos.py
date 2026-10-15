"""Permisos: qué puede hacer cada rol, y los permisos especiales por persona.

Toda la lista de "quién puede qué" vivía escrita a mano en tres sitios
distintos: los `require_role(...)` de cada router, los `meta.roles` del router
del frontend y el `allowed()` del sidebar. Tres listas que, con el tiempo,
terminaron divergiendo en catorce puntos concretos — el repositor veía
"Cargar Mercadería" y el backend le devolvía 403 al confirmar; el cajero abría
la pantalla de Caja y los reportes de caja lo rechazaban; el sidebar trataba a
un usuario sin datos cargados como si fuera `admin` y le mostraba todo el menú.

De acá salen `GET /api/permisos`, la matriz en modo lectura de la pestaña de
Usuarios y el aviso de permisos especiales. El `require_role` de
`app/auth/dependencies.py` usa `PERMISOS_ESPECIALES` para dejar pasar a quien
tenga el pase extra.

Un permiso especial es un "pase suelto" que el dueño le otorga a una persona
puntual desde la pestaña de Usuarios, sin tener que cambiarle el rol. Sirve
para lo que no amerita inventar un rol nuevo: que un cajero vea los reportes,
que un repositor pueda anular una venta, que alguien vea los movimientos de
caja sin ser encargado.
"""

import json

from fastapi import HTTPException

ROLES = ("admin", "encargado", "cajero", "repositor")

NOMBRE_ROL = {
    "admin": "Dueño / Administrador",
    "encargado": "Encargado",
    "cajero": "Cajero",
    "repositor": "Repositor",
}

# Cada permiso especial: la clave que se guarda en la base, cómo se llama en
# pantalla, qué deja hacer y qué roles ya lo tienen por defecto. `por_defecto`
# es lo que ya hace el rol sin tocar nada; el checkbox lo que hace es agregar
# ese derecho a alguien que no lo tiene.
PERMISOS_ESPECIALES = (
    {
        "clave": "ver_reportes",
        "etiqueta": "Ver los reportes",
        "descripcion": "Ver la pantalla de Reportes, con las ventas y el stock por categoría.",
        "por_defecto": ("admin", "encargado"),
        "abre": "Reportes",
    },
    {
        "clave": "gestionar_clientes",
        "etiqueta": "Dar de alta y editar clientes",
        "descripcion": "Crear y editar la ficha de un cliente. Ver la lista puede cualquiera, porque el POS la necesita para cobrar.",
        "por_defecto": ("admin", "encargado"),
        "abre": "Clientes",
    },
    {
        "clave": "ver_caja",
        "etiqueta": "Ver los movimientos y el calendario de caja",
        "descripcion": "Ver qué pasó en la caja: el calendario, el día y los movimientos. Abrir y cerrar caja no lo da este permiso.",
        "por_defecto": ("admin", "encargado"),
        "abre": "Caja",
    },
    {
        "clave": "anular_ventas",
        "etiqueta": "Anular una venta cobrada",
        "descripcion": "Anular una venta que ya se cobró. Ojo: esto borra el dinero de la caja del día.",
        "por_defecto": ("admin", "encargado", "cajero"),
        "abre": "Ventas",
    },
)

_CLAVES = {p["clave"] for p in PERMISOS_ESPECIALES}


def claves_permisos() -> set:
    """Las claves de permiso especiales que existen hoy."""
    return set(_CLAVES)

# La matriz en modo lectura: lo que el dueño lee para entender qué hace cada
# rol. Las acciones marcan `permiso` cuando además se le puede dar suelto a
# una persona concreta.
MATRIZ = (
    {
        "area": "Ventas",
        "icono": "fa-solid fa-cash-register",
        "acciones": (
            {"accion": "Cobrar en el POS", "roles": ("admin", "cajero")},
            {"accion": "Ver la lista de ventas", "roles": ROLES},
            {"accion": "Anular una venta cobrada", "roles": ("admin", "encargado", "cajero"), "permiso": "anular_ventas"},
        ),
    },
    {
        "area": "Caja",
        "icono": "fa-solid fa-vault",
        "acciones": (
            {"accion": "Abrir y cerrar caja, ingresos y egresos", "roles": ("admin", "cajero")},
            {"accion": "Ver el calendario, el día y los movimientos de caja", "roles": ("admin", "encargado"), "permiso": "ver_caja"},
            {"accion": "Ver los arqueos y configurar la caja", "roles": ("admin", "encargado")},
        ),
    },
    {
        "area": "Productos e inventario",
        "icono": "fa-solid fa-boxes-stacked",
        "acciones": (
            {"accion": "Ver productos, precios y etiquetas", "roles": ROLES},
            {"accion": "Ver los precios online y el análisis de precios", "roles": ("admin", "encargado", "repositor")},
            {"accion": "Crear y editar productos", "roles": ("admin", "encargado")},
            {"accion": "Ajustar el stock y cargar lotes", "roles": ("admin", "encargado")},
            {"accion": "Dar de baja un producto", "roles": ("admin",)},
        ),
    },
    {
        "area": "Compras y proveedores",
        "icono": "fa-solid fa-truck-ramp-box",
        "acciones": (
            {"accion": "Ver compras, proveedores y su estado de cuenta", "roles": ROLES},
            {"accion": "Cargar y recibir compras", "roles": ("admin", "encargado")},
            {"accion": "Crear y editar proveedores y deudas", "roles": ("admin", "encargado")},
            {"accion": "Comentar en una orden de compra", "roles": ("admin", "encargado", "cajero")},
            {"accion": "Registrar pagos a proveedores (del cajón)", "roles": ("admin", "encargado", "cajero")},
        ),
    },
    {
        "area": "Clientes",
        "icono": "fa-solid fa-address-book",
        "acciones": (
            {"accion": "Ver la lista de clientes (la necesita el POS)", "roles": ROLES},
            {"accion": "Dar de alta y editar clientes", "roles": ("admin", "encargado"), "permiso": "gestionar_clientes"},
        ),
    },
    {
        "area": "Reportes",
        "icono": "fa-solid fa-chart-column",
        "acciones": (
            {"accion": "Ver los reportes de ventas y stock", "roles": ("admin", "encargado"), "permiso": "ver_reportes"},
            {"accion": "Ver el dashboard del día", "roles": ROLES},
        ),
    },
    {
        "area": "Sistema",
        "icono": "fa-solid fa-gears",
        "acciones": (
            {"accion": "Ver los ajustes", "roles": ("admin", "encargado")},
            {"accion": "Cambiar los ajustes del sistema", "roles": ("admin",)},
            {"accion": "Crear, editar y desactivar usuarios", "roles": ("admin",)},
            {"accion": "Licencias, auditoría y respaldos", "roles": ("admin",)},
            {"accion": "Respaldos: también descargarlos", "roles": ("admin", "encargado")},
            {"accion": "Facturación AFIP y certificados", "roles": ("admin", "encargado")},
            {"accion": "Categorías, sectores, ofertas y configuración", "roles": ("admin", "encargado")},
        ),
    },
)


def permisos_de(usuario) -> list:
    """Los permisos especiales otorgados a una persona.

    Devuelve solo claves conocidas: si en la base quedó guardado un permiso
    que ya no existe, no se cuelga de él ni tira error al leerlo.
    """
    bruto = getattr(usuario, "permisos", None)
    if not bruto:
        return []
    try:
        valores = json.loads(bruto)
    except (TypeError, ValueError):
        return []
    if not isinstance(valores, list):
        return []
    return sorted({v for v in valores if isinstance(v, str) and v in _CLAVES})


def tiene_permiso(usuario, clave: str) -> bool:
    """True si la persona puede hacer `clave`.

    El dueño (rol admin) tiene todo sin necesitar ningún checkbox: así el
    dueño nunca se queda afuera de su propio sistema por un detalle de carga.
    """
    if usuario is None:
        return False
    if (getattr(usuario, "rol", "") or "").lower() == "admin":
        return True
    return clave in permisos_de(usuario)


def validar_permisos(claves) -> list:
    """Normaliza la lista que mandó el cliente y la compara contra las claves
    conocidas. Devuelve 400 con el nombre del permiso si alguno no existe, en
    vez de guardárselo y que después no haga nada sin aviso."""
    if not claves:
        return []
    desconocidos = sorted({c for c in claves if c not in _CLAVES})
    if desconocidos:
        raise HTTPException(
            status_code=400,
            detail=f"Permiso desconocido: {', '.join(desconocidos)}",
        )
    return sorted(set(claves))


def a_dict() -> dict:
    """La matriz completa para `GET /api/permisos`."""
    return {
        "roles": [{"clave": r, "etiqueta": NOMBRE_ROL[r]} for r in ROLES],
        "permisos_especiales": [dict(p) for p in PERMISOS_ESPECIALES],
        "matriz": [
            {
                "area": a["area"],
                "icono": a["icono"],
                "acciones": [dict(x) for x in a["acciones"]],
            }
            for a in MATRIZ
        ],
    }
