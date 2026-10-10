"""Normalización de texto para productos (Title Case en español)."""

STOPWORDS_ES = {
    "a", "al", "algun", "alguna", "algunas", "alguno", "algunos",
    "ante", "antes", "aquel", "aquella", "aquellas", "aquellos", "aqui",
    "asi", "aun", "aunque", "bajo", "bien", "cada", "casi", "como",
    "con", "contra", "cual", "cuales", "cuando", "cuanto", "cuantos",
    "de", "del", "demas", "demas", "dentro", "desde", "donde", "dos",
    "durante", "e", "el", "ella", "ellas", "ello", "ellos", "en",
    "entonces", "entre", "era", "eran", "eres", "es", "esa", "esas",
    "ese", "eso", "esos", "esta", "estaba", "estan", "estar", "estas",
    "este", "esto", "estos", "fue", "fueron", "ha", "habia", "han",
    "hasta", "hay", "incluso", "la", "las", "le", "les", "lo", "los",
    "mas", "me", "mi", "mientras", "mis", "mucho", "muchos", "muy",
    "nada", "ni", "no", "nos", "nosotros", "nuestra", "nuestro", "o",
    "otra", "otras", "otro", "otros", "para", "pero", "poco", "por",
    "porque", "que", "quien", "quienes", "se", "segun", "ser", "si",
    "sin", "sobre", "son", "su", "sus", "tambien", "tan", "tanto",
    "te", "tiene", "todo", "todos", "tras", "tu", "tus", "un", "una",
    "unas", "uno", "unos", "y", "ya", "yo",
}


def title_case_es(texto: str | None) -> str | None:
    """Convierte a Title Case respetando stop-words en español.

    Ejemplos:
        "cAFÉ DE BRASIL" → "Café de Brasil"
        "GASEOSA COCA COLA 500ML" → "Gaseosa Coca Cola 500ml"
        "salsa de tomate natural" → "Salsa de Tomate Natural"
    """
    if not texto or not texto.strip():
        return texto

    palabras = texto.strip().split()
    resultado = []
    for i, palabra in enumerate(palabras):
        lower = palabra.lower()
        # Primera palabra siempre con mayúscula
        if i == 0:
            resultado.append(palabra.capitalize())
        # Stop-words entre palabras van en minúscula
        elif lower in STOPWORDS_ES:
            resultado.append(lower)
        # Números y códigos (500ml, 750cc, etc.) se dejan como están
        elif any(ch.isdigit() for ch in palabra):
            resultado.append(palabra)
        else:
            resultado.append(palabra.capitalize())

    return " ".join(resultado)


def normalizar_producto_campos(data: dict) -> dict:
    """Aplica title_case_es a los campos de texto de un producto."""
    for campo in ("nombre", "marca", "descripcion"):
        if campo in data and isinstance(data[campo], str):
            data[campo] = title_case_es(data[campo])
    return data
