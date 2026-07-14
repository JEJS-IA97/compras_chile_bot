KEYWORDS_COIMSA = [
    "limpieza", "aseo", "sanitizacion", "sanitización",
    "fumigacion", "fumigación", "desinfeccion", "desinfección",
]

KEYWORDS_INDUWORK = [
    "balistico", "balístico", "anticorte", "tactico", "táctico",
    "chaleco", "casco", "uniforme", "policial",
    "equipamiento tactico", "equipamiento táctico",
    "equipos de seguridad", "vestuario tactico", "vestuario táctico",
    "seguridad",
]

KEYWORDS_ESPECIALES = [
    "actividad social", "proyecto social", "programa social",
    "desarrollo informatico", "desarrollo informático",
]

# Unión de todas las palabras clave, usada como prefiltro rápido sobre el
# nombre básico que entrega la API por fecha, ANTES de pedir el detalle
# completo por código (para no gastar cuota de API en licitaciones irrelevantes).
TODAS_LAS_KEYWORDS = KEYWORDS_COIMSA + KEYWORDS_INDUWORK + KEYWORDS_ESPECIALES


def posible_relevante(texto: str) -> bool:
    """Prefiltro barato: ¿el texto contiene alguna palabra clave, de cualquier categoría?"""
    texto = (texto or "").lower()
    return any(kw in texto for kw in TODAS_LAS_KEYWORDS)


def evaluar_licitacion(licitacion: dict) -> dict:
    nombre = licitacion.get("nombre", "").lower()
    descripcion = licitacion.get("descripcion", "").lower()
    region = licitacion.get("region", "").lower()

    texto = f"{nombre} {descripcion}"

    es_rm = (
        "metropolitana" in region or
        "santiago" in region or
        region.strip() == "rm"
    )

    return {
        "coimsa": es_rm and any(k in texto for k in KEYWORDS_COIMSA),
        "induwork": any(k in texto for k in KEYWORDS_INDUWORK),
        "especial": any(k in texto for k in KEYWORDS_ESPECIALES),
    }