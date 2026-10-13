"""Recategorización de productos: motor local de palabras clave + puente a la IA.

Nada de esto mueve un producto por su cuenta. Todo lo que hace acá es
**proponer**; la decisión la toma siempre una persona desde el panel, que envía
los cambios a `aplicar()`.

Dos fuentes de sugerencia:

- `sugerir_local()`: sin costo, sin red, sync. Tira de un diccionario de
  palabras clave del rubro argentino (almacén / kiosco) y de que el nombre de
  una categoría existente aparezca en el texto del producto.
- La IA: el router arma lotes de a `TAMANO_LOTE_IA`, arma el prompt con
  `prompt_ia()`, llama a `ia.completar()` y limpia la respuesta con
  `interpretar_ia()` — siempre contra el catálogo real del cliente.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.categoria import Categoria
from app.models.producto import Producto

# Límite de productos por llamada a la IA. El panel arma los lotes y muestra
# una barra de progreso: mejor 5 llamadas de 20 que una gigante que se corta.
TAMANO_LOTE_IA = 20

# Los motores no sugieren el cajón de entrada.
CATEGORIA_NEUTRA = {"general", "sin categoria", "sin categorias", "otro", "otros", "varios"}

# Qué entra en cada categoría. Clave ya normalizada (minúsculas y sin tildes),
# así se compara directo contra `normalizar(nombre)`. Le damos al modelo el
# contenido de la categoría porque el nombre solo no alcanza: "Golosinas" para
# un kiosco incluye los snacks salados, y eso no se deduce del título.
RUBROS: dict[str, str] = {
    "golosinas": "chocolates, caramelos, galletitas dulces, chicles, snacks dulces y salados",
    "almacen": "aceites, conservas, enlatados, pastas, harinas, arroz, legumbres, "
               "especias, aderezos, salsa de tomate, café de máquina",
    "bebidas": "gaseosas, aguas, jugos, energizantes, infusiones frías, cervezas sin alcohol",
    "bebidas alcoholicas": "vinos, cervezas, destilados, espumantes",
    "frescos": "lácteos, quesos, fiambre, carnes, aves, frutas y verduras, huevos",
    "lacteos": "leche, yogurt, manteca, crema, quesos",
    "limpieza": "detergente, lavandina, jabón, desinfectante, esponjas, bolsas de residuo",
    "papeleria": "resmas, tintas, cartuchos",
    "cafeteria": "café en grano y molido, yerba, té, azúcar, endulzantes, saquitos",
    "libreria": "útiles escolares, libretas, lapiceras, lapices, gomas, compases",
    "perfumeria": "perfumes, desodorantes, cremas, shampoo, acondicionador, "
                  "maquillaje, cuidado personal",
    "kiosco": "revistas, diarios, cigarrillos, fichas, tarjetas, artículos de regalo",
    "panaderia": "pan, facturas, bizcochitos, massas",
    "helados": "helado, paletas, postres congelados",
}


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------

def normalizar(texto: Optional[str]) -> str:
    """Minúsculas, sin acentos, espacios colapsados. Base de toda comparación."""
    if not texto:
        return ""
    sin_tildes = "".join(
        ch
        for ch in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def _encontrar(texto: str, frase: str) -> bool:
    """Coincidencia por frase completa sobre el texto espaciado en los bordes.

    Así "pan" pega en "pan lactal" pero no en "panuelo".
    """
    return f" {frase} " in f" {texto} "


# ---------------------------------------------------------------------------
# Diccionario local (nombre canónico -> palabras que lo delatan)
# ---------------------------------------------------------------------------
# El canónico es con lo que se intenta casar contra el catálogo del cliente:
# "Bebidas" encaja con "Bebidas", "Bebidas frías", "Bebidas sin alcohol", etc.
# Las palabras son expresiones normilizadas (sin tildes, minúsculas).

SINONIMOS: dict[str, tuple[str, ...]] = {
    "Bebidas": (
        "bebida", "gaseosa", "refresco", "jugo", "nectar", "limonada", "agua mineral",
        "agua saborizada", "soda", "energetica", "isotonica", "agua de sabor",
    ),
    "Bebidas alcoholicas": (
        "cerveza", "birra", "vino", "espumante", "whisky", "wisky", "vodka", "ron",
        "ginebra", "gin", "fernet", "aperol", "licor", "cerveza artesanal",
        "sidra", "chandon", "quilsen", "stella", "corona", "heineken",
    ),
    "Lacteos": (
        "leche", "queso", "mantequilla", "manteca", "yogur", "yoghurt", "crema de leche",
        "dulce de leche", "flan", "ricotta", "mozzarella", "queso cremoso",
    ),
    "Carnes": (
        "carne", "pollo", "cerdo", "chorizo", "jamon", "salchicha", "milanesa",
        "hamburguesa", "pavo", "cordero", "bondiola", "nalga", "peceto", "tapa de asado",
    ),
    "Frutas y verduras": (
        "fruta", "frutas", "verdura", "verduras", "manzana", "banana", "naranja",
        "papa", "papas", "tomate", "cebolla", "lechuga", "zanahoria", "uva", "pera",
        "mandarina", "limon", "sandia", "melon", "palta", "broccoli", "zanahoria",
    ),
    "Panaderia": (
        "pan", "pan lactal", "pan dulce", "factura", "medialuna", "bizcocho",
        "bizcochito", "tostada", "criollita", "masa madre", "flauta", "baguette",
    ),
    "Golosinas": (
        "golosina", "golosinas", "gominola", "gomitas", "chicle", "chupetin",
        "caramelo", "caramelos", "bombon", "bombones", "chocolate", "alfajor",
        "galletita", "galletitas", "snack", "snacks",
    ),
    "Snacks salados": (
        "papas fritas", "papas snacks", "nachos", "palitos salados", "manises",
        "manjarroz", "porotos grados", "chipa", "picante",
    ),
    "Congelados": (
        "congelado", "congelados", "helado", "pizza congelada", "nuggets",
        "papas congeladas", "verduras congeladas", "pesce", "empanadas congeladas",
    ),
    "Cafe e infusiones": (
        "cafe", "cafetera", "te", "infusion", "infusiones", "mate cocido",
        "saquito", "sobres de te", "cappuccino", "chocolate en polvo",
    ),
    "Almacen y secos": (
        "arroz", "fideos", "pasta", "harina", "azucar", "aceite", "conserva",
        "conservas", "lenteja", "lentejas", "garbanzo", "garbanzos", "polenta",
        "atun", "enlatado", "enlatados", "salsa de tomate", "caldo", "especias",
        "sal fina", "pimienta", "mayonesa", "mostaza", "ketchup", "puré",
    ),
    "Limpieza": (
        "detergente", "lavandina", "cloro", "lavandraga", "desinfectante", "amoniaco",
        "esponja", "guantes", "jabon en polvo", "suavizante", "flores", "lejia",
    ),
    "Higiene personal": (
        "jabon", "shampoo", "shampu", "acondicionador", "pasta de dientes",
        "crema dental", "cepillo de dientes", "desodorante", "toallita", "toallitas",
        "papel higienico", "gel", "locion", "maquillaje", "aparato de afeitar",
    ),
    "Bebes": (
        "panal", "panales", "leche infantil", "mamadera", "papilla", "bebé",
        "bebe", "toallitas humedas", "crema para panal",
    ),
    "Mascotas": (
        "perro", "gato", "balanceado", "alimento para perro", "alimento para gato",
        "michi", "pienso", "arenas sanitarias",
    ),
    "Tabaco": (
        "cigarrillo", "cigarrillos", "tabaco", "fumo", "sustituto de tabaco",
    ),
}


# ---------------------------------------------------------------------------
# Catálogo y resolución de categoría
# ---------------------------------------------------------------------------

def catalogo(db: Session) -> list[tuple[int, str]]:
    """Categorías activas como (id, nombre)."""
    filas = (
        db.query(Categoria.id, Categoria.nombre)
        .filter(Categoria.activo == True)  # noqa: E712
        .order_by(Categoria.nombre)
        .all()
    )
    return [(int(i), str(n)) for i, n in filas]


def _resolver(canonical: str, cat: list[tuple[int, str]]) -> Optional[tuple[int, str]]:
    """Casa el nombre canónico con una categoría real del cliente.

    Acepta igualdad o contención (el canónico "Bebidas" cubre "Bebidas frías"),
    pero la contención solo vale si el texto tiene largo razonable: si no,
    "sal" termina casando con "Salón de eventos".
    """
    objetivo = normalizar(canonical)
    if not objetivo:
        return None
    for cid, nombre in cat:
        n = normalizar(nombre)
        if not n or n in CATEGORIA_NEUTRA:
            continue
        if n == objetivo:
            return cid, nombre
    if len(objetivo) < 4:
        return None
    for cid, nombre in cat:
        n = normalizar(nombre)
        if not n or n in CATEGORIA_NEUTRA:
            continue
        if objetivo in n or (len(n) >= 4 and n in objetivo):
            return cid, nombre
    return None


# ---------------------------------------------------------------------------
# Sugerencia local
# ---------------------------------------------------------------------------

def sugerir_local(
    producto: Producto,
    cat: list[tuple[int, str]],
) -> Optional[dict[str, Any]]:
    """Propone una categoría por palabras clave. `None` si no hay pista."""
    nombre = normalizar(f"{producto.nombre} {producto.marca or ''}")
    texto_completo = f"{nombre} {normalizar(producto.descripcion)}"
    actual_id = producto.categoria_id

    mejor: Optional[dict[str, Any]] = None

    # 1) La categoría aparece escrita en el producto: la señal más fuerte.
    for cid, nombre_cat in cat:
        n = normalizar(nombre_cat)
        if not n or n in CATEGORIA_NEUTRA or len(n) < 4:
            continue
        if cid == actual_id:
            continue
        if _encontrar(nombre, n):
            mejor = {
                "categoria_id": cid,
                "categoria_nombre": nombre_cat,
                "confianza": 0.92,
                "motivo": f"el nombre contiene \"{nombre_cat}\"",
            }
            break

    # 2) Palabras clave del rubro. Se puntúa por dónde aparece la pista:
    #    en el nombre pesa más que solo en la descripción.
    for canonical, palabras in SINONIMOS.items():
        destino = _resolver(canonical, cat)
        if not destino:
            continue
        if destino[0] == actual_id:
            continue
        en_nombre = next((p for p in palabras if _encontrar(nombre, p)), None)
        if en_nombre:
            puntaje = 2
            pista = en_nombre
        else:
            pista = next((p for p in palabras if _encontrar(texto_completo, p)), None)
            puntaje = 1 if pista else 0
        if not pista:
            continue
        confianza = min(0.88, 0.45 + 0.15 * puntaje)
        candidato = {
            "categoria_id": destino[0],
            "categoria_nombre": destino[1],
            "confianza": round(confianza, 2),
            "motivo": f"palabra clave \"{pista}\"",
        }
        if mejor is None or candidato["confianza"] > mejor["confianza"]:
            mejor = candidato

    return mejor


# ---------------------------------------------------------------------------
# Candidatos (lo que muestra el panel)
# ---------------------------------------------------------------------------

MODOS = ("pendientes", "sin_categoria", "general", "todos")


def _query_candidatos(db: Session, *, modo: str, q: str):
    """Filtro compartido: la lista paginada y el "Seleccionar todo" ven lo mismo."""
    if modo not in MODOS:
        modo = "pendientes"

    query = db.query(Producto).filter(Producto.activo == True)  # noqa: E712

    if modo == "sin_categoria":
        query = query.filter(Producto.categoria_id.is_(None))
    elif modo == "general":
        query = (
            query.join(Categoria, Producto.categoria_id == Categoria.id)
            .filter(func.lower(Categoria.nombre) == "general")
        )
    elif modo == "pendientes":
        query = query.outerjoin(Categoria, Producto.categoria_id == Categoria.id).filter(
            (Producto.categoria_id.is_(None)) | (func.lower(Categoria.nombre) == "general")
        )

    # `ilike` sin normalizar: si normalizás acá el texto y la columna no está
    # normalizada, "cafe" deja de encontrar "Café" y se pierde lo poco que
    # funcionaba.
    texto = q.strip()
    if texto:
        like = f"%{texto}%"
        query = query.filter(
            Producto.nombre.ilike(like)
            | Producto.marca.ilike(like)
            | Producto.descripcion.ilike(like)
            | Producto.codigo_barras.ilike(like)
        )
    return query


def ids_candidatos(
    db: Session,
    *,
    modo: str = "pendientes",
    q: str = "",
) -> tuple[list[int], int]:
    """Todos los ids del filtro, no sólo la página que se está viendo.

    El "Seleccionar todo" del panel tiene que alcanzar a las otras páginas, y
    para eso necesita los ids sueltos: las filas vienen paginadas y traen la
    sugerencia local ya calculada, que acá no hace falta.
    """
    query = _query_candidatos(db, modo=modo, q=q)
    total = query.count()
    ids = [
        pid
        for (pid,) in query.with_entities(Producto.id).order_by(Producto.nombre).all()
    ]
    return ids, total


def candidatos(
    db: Session,
    *,
    modo: str = "pendientes",
    q: str = "",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Lista productos a revisar con la sugerencia local ya calculada."""
    query = _query_candidatos(db, modo=modo, q=q)

    total = query.count()
    query = query.order_by(Producto.nombre).offset((page - 1) * page_size).limit(page_size)
    productos = query.all()

    cat = catalogo(db)
    nombre_por_id = dict(cat)
    filas: list[dict[str, Any]] = []
    for p in productos:
        s = sugerir_local(p, cat)
        # Sin cambio no es sugerencia: solo entorpece la revisión.
        if s and s["categoria_id"] == p.categoria_id:
            s = None
        filas.append(_fila(p, nombre_por_id, s))
    return filas, total


def _fila(
    p: Producto,
    nombre_por_id: dict[int, str],
    s: Optional[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "producto_id": p.id,
        "nombre": p.nombre,
        "marca": p.marca,
        "codigo_barras": p.codigo_barras,
        "descripcion": p.descripcion,
        "categoria_actual_id": p.categoria_id,
        "categoria_actual": nombre_por_id.get(p.categoria_id) if p.categoria_id else None,
        "sugerencia": s,
        # El destino arranca en la sugerencia si hay, si no en lo que ya tiene.
        "destino_id": (s or {}).get("categoria_id") or p.categoria_id,
    }


def detalle(db: Session, productos_ids: list[int]) -> tuple[list[dict], dict[int, str]]:
    """Filas para los productos seleccionados (los que se mandan a la IA)."""
    if not productos_ids:
        return [], {}
    productos = (
        db.query(Producto)
        .filter(Producto.id.in_(productos_ids), Producto.activo == True)  # noqa: E712
        .all()
    )
    cat = catalogo(db)
    nombre_por_id = dict(cat)
    orden = {pid: i for i, pid in enumerate(productos_ids)}
    productos.sort(key=lambda p: orden.get(p.id, 0))
    return [_fila(p, nombre_por_id, sugerir_local(p, cat)) for p in productos], nombre_por_id


# ---------------------------------------------------------------------------
# Sugerencia por IA
# ---------------------------------------------------------------------------

SISTEMA_IA = (
    "Sos el clasificador de productos de un almacén y kiosco argentino. "
    "Para cada producto del listado elegí UNA categoría del catálogo que le "
    "corresponda por tipo de producto.\n"
    "Respondé SOLO con un objeto JSON con la clave \"sugerencias\", una lista "
    "con un elemento por producto, en el mismo orden en que llegaron:\n"
    "{\"sugerencias\":[{\"producto_id\":12,\"categoria_id\":5,"
    "\"nueva_categoria\":null,\"confianza\":0.9,\"motivo\":\"...\"}]}\n"
    "Reglas:\n"
    "- categoria_id debe ser un id exacto del catálogo, o null si ninguna encaja.\n"
    "- Si no estás seguro, devolvé categoria_id null y nueva_categoria null: es "
    "mejor no proponer nada que mandar un producto a la categoría equivocada.\n"
    "- \"confianza\" es tu certeza real entre 0 y 1. Bajala cuando el nombre es "
    "ambiguo, la marca no ayuda o la descripción viene vacía.\n"
    "- Evitá las categorías de relleno (General, Otros, Varios) salvo que nada "
    "de lo anterior encaje.\n"
    "- \"nueva_categoria\" solo si el producto es claramente de un rubro que falta "
    "en el catálogo: nombre corto, sin tildes, mayúscula inicial (ej. \"Electrónica\"); "
    "si usás una, dejá categoria_id en null.\n"
    "- Nunca uses ids que no estén en el catálogo.\n"
    "- \"motivo\" es una frase corta y concreta en español que cite la pista que "
    "usaste (nombre, marca o descripción).\n"
    "- No escribas nada fuera del JSON.\n"
    "Ejemplos:\n"
    "- \"Coca Cola 500ml | Coca-Cola | gaseosa sabor cola\" -> la categoría "
    "\"Bebidas\" del catálogo, confianza 0.95, motivo \"gaseosa sabor cola\".\n"
    "- \"Aceite Girasol 1.5L Natura | Natura |\" -> la categoría \"Almacén\", "
    "confianza 0.9, motivo \"aceite comestible\".\n"
    "- \"Papas Fritas 45g | McCorn |\" -> la categoría \"Golosinas\", confianza "
    "0.85, motivo \"snack salado, entra en golosinas\".\n"
    "- \"2 por Mil 2x1000 | Promo | combo promocional\" -> categoria_id null, "
    "confianza 0.2, motivo \"nombre de promo, no indica rubro\"."
)


def prompt_ia(
    productos: list[dict[str, Any]],
    cat: list[tuple[int, str]],
    *,
    incluir_actual: bool = True,
) -> str:
    """Catálogo con su contenido + productos con toda la pista disponible.

    `incluir_actual=False` esconde la categoría que el producto ya tiene: es lo
    que usa el test de precisión para pedir el veredicto a ciegas, sin que el
    modelo se copie de la respuesta.
    """
    catalogo_lineas = []
    for cid, nombre in cat:
        rubro = RUBROS.get(normalizar(nombre))
        catalogo_lineas.append(
            f"{cid} | {nombre}" + (f" | qué entra: {rubro}" if rubro else "")
        )
    catalogo_txt = "\n".join(catalogo_lineas) or "(vacío)"

    lineas = []
    for p in productos:
        desc = (p.get("descripcion") or "").strip()[:120]
        marca = (p.get("marca") or "").strip() or "-"
        barras = (p.get("codigo_barras") or "").strip() or "-"
        fila = f"{p['producto_id']} | {p['nombre']} | {marca} | {barras}"
        if incluir_actual:
            fila += f" | actual: {p.get('categoria_actual') or 'sin categoría'}"
        lineas.append(f"{fila} | {desc}")

    cabecera = "Productos (id | nombre | marca | código de barras"
    if incluir_actual:
        cabecera += " | categoría actual"
    cabecera += " | descripción):"

    return (
        f"Catálogo (id | categoría | contenido):\n{catalogo_txt}\n\n"
        f"{cabecera}\n{chr(10).join(lineas)}"
    )


def interpretar_ia(
    crudo: Any,
    productos: list[dict[str, Any]],
    cat: list[tuple[int, str]],
) -> list[dict[str, Any]]:
    """Limpia lo que devolvió el modelo: ids inventados afuera, orden y tipos."""
    from app.services.ia.openai_compat import extraer_json

    if isinstance(crudo, str):
        crudo = extraer_json(crudo)
    if not isinstance(crudo, dict):
        raise ValueError("la IA no devolvió un objeto JSON")
    items = crudo.get("sugerencias")
    if not isinstance(items, list):
        raise ValueError("falta la lista \"sugerencias\"")

    ids_validos = {cid for cid, _ in cat}
    pedidos = {p["producto_id"] for p in productos}
    nombres = {p["producto_id"]: p for p in productos}

    salida = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            pid = int(it.get("producto_id"))
        except (TypeError, ValueError):
            continue
        if pid not in pedidos:
            continue
        cat_id = it.get("categoria_id")
        try:
            cat_id = int(cat_id) if cat_id is not None else None
        except (TypeError, ValueError):
            cat_id = None
        if cat_id is not None and cat_id not in ids_validos:
            cat_id = None

        nueva = it.get("nueva_categoria")
        nueva = str(nueva).strip()[:60] if nueva else None
        if nueva and normalizar(nueva) in CATEGORIA_NEUTRA:
            nueva = None
        if cat_id is not None:
            nueva = None
        if cat_id is None and not nueva:
            continue

        # Si el modelo no manda confianza, 0.5: ni para preseleccionar ni para
        # descartar. Se recorta al rango para que la UI pueda comparar tranquila.
        try:
            confianza = float(it.get("confianza"))
        except (TypeError, ValueError):
            confianza = 0.5
        confianza = round(min(1.0, max(0.0, confianza)), 2)

        motivo = str(it.get("motivo") or "").strip()[:140]
        salida.append({
            "producto_id": pid,
            "nombre": nombres[pid]["nombre"],
            "categoria_actual_id": nombres[pid]["categoria_actual_id"],
            "categoria_actual": nombres[pid]["categoria_actual"],
            "categoria_id": cat_id,
            "categoria_nombre": dict(cat).get(cat_id) if cat_id else None,
            "nueva_categoria": nueva,
            "confianza": confianza,
            "motivo": motivo or "IA",
        })
    return salida


# ---------------------------------------------------------------------------
# Aplicación (aquí recién se toca un producto)
# ---------------------------------------------------------------------------

def _obtener_o_crear_categoria(db: Session, nombre: str) -> tuple[int, str, bool]:
    """Devuelve (id, nombre, creada_ahora). Dedup exacto y sin tildes."""
    limpio = " ".join(str(nombre).split())[:100]
    if not limpio:
        raise ValueError("nombre de categoría vacío")
    objetivo = normalizar(limpio)

    todas = db.query(Categoria).all()
    for cat in todas:
        if normalizar(cat.nombre) == objetivo:
            # Elegirl explícitamente la reactiva: un producto no puede quedar
            # apuntando a una categoría que el panel no muestra.
            cat.activo = True
            return cat.id, cat.nombre, False

    nueva = Categoria(nombre=limpio, activo=True)
    db.add(nueva)
    # El `unique` de la DB es binario y el chequeo de arriba ya cubre las
    # variantes de tildes y mayúsculas, así que no debería colisionar.
    db.flush()
    return nueva.id, nueva.nombre, True


def aplicar(
    db: Session,
    cambios: list[dict[str, Any]],
) -> dict[str, Any]:
    """Asigna las categorías elegidas por la persona. Es el único punto de escritura."""
    # Incluye las inactivas: si alguien elige una a mano, se puede usar (y se
    # reactiva al asignarla).
    validos = {cid for cid, in db.query(Categoria.id).all()}
    creadas: list[dict[str, Any]] = []
    aplicados = 0
    errores: list[dict[str, Any]] = []

    for cambio in cambios or []:
        try:
            pid = int(cambio.get("producto_id"))
        except (TypeError, ValueError):
            errores.append({"producto_id": None, "motivo": "producto_id inválido"})
            continue

        prod = (
            db.query(Producto)
            .filter(Producto.id == pid, Producto.activo == True)  # noqa: E712
            .first()
        )
        if not prod:
            errores.append({"producto_id": pid, "motivo": "producto no encontrado"})
            continue

        cat_id = cambio.get("categoria_id")
        try:
            cat_id = int(cat_id) if cat_id is not None else None
        except (TypeError, ValueError):
            cat_id = None

        nueva = (cambio.get("nueva_categoria") or "").strip()
        if cat_id is None and nueva:
            try:
                cat_id, cat_nombre, creada = _obtener_o_crear_categoria(db, nueva)
            except ValueError as err:
                errores.append({"producto_id": pid, "motivo": str(err)})
                continue
            if creada:
                creadas.append({"id": cat_id, "nombre": cat_nombre})
        elif cat_id is not None and cat_id not in validos:
            errores.append({"producto_id": pid, "motivo": "categoría inexistente"})
            continue

        if cat_id is None:
            errores.append({"producto_id": pid, "motivo": "sin categoría destino"})
            continue

        if prod.categoria_id != cat_id:
            prod.categoria_id = cat_id
            aplicados += 1

    db.commit()
    return {
        "aplicados": aplicados,
        "categorias_creadas": creadas,
        "errores": errores,
    }
