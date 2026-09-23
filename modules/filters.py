KEYWORDS_COIMSA = [
    "limpieza", "aseo", "sanitizacion", "sanitización",
    "fumigacion", "fumigación", "desinfeccion", "desinfección",
]

# Términos usados por Induwork para la búsqueda manual diaria.
# Se evita agregar términos genéricos como "seguridad", "vigilancia",
# "sistema", "equipo", "alarma" o "cámara" porque generan falsos positivos.
KEYWORDS_INDUWORK = [
    "anticorte",
    "anticortes",
    "anti corte",
    "anti cortes",
    "anti punzon",
    "antipunzon",
    "antipunzonamiento",
    "anti punzonamiento",
    "tactica",
    "tacticas",
    "táctica",
    "tácticas",
    "tactico",
    "tacticos",
    "táctico",
    "tácticos",
    "antibala",
    "antibalas",
    "anti bala",
    "anti balas",
    "balistico",
    "balisticos",
    "balístico",
    "balísticos",
    "balistica",
    "balisticas",
    "balística",
    "balísticas",
]

KEYWORDS_ESPECIALES = [
    "actividad social", "proyecto social", "programa social",
    "desarrollo informatico", "desarrollo informático",
]

TODAS_LAS_KEYWORDS = KEYWORDS_COIMSA + KEYWORDS_INDUWORK + KEYWORDS_ESPECIALES


def contiene_keyword_induwork(texto: str) -> bool:
    """Detecta coincidencias con las búsquedas manuales de Induwork."""
    texto = (texto or "").lower()
    return any(kw in texto for kw in KEYWORDS_INDUWORK)


def posible_relevante(texto: str) -> bool:
    """Prefiltro rápido para evitar detalles de licitaciones irrelevantes."""
    texto = (texto or "").lower()
    return any(kw in texto for kw in TODAS_LAS_KEYWORDS)


def evaluar_licitacion(licitacion: dict) -> dict:
    nombre = licitacion.get("nombre", "").lower()
    descripcion = licitacion.get("descripcion", "").lower()
    region = licitacion.get("region", "").lower()
    texto = f"{nombre} {descripcion}"

    es_rm = (
        "metropolitana" in region
        or "santiago" in region
        or region.strip() == "rm"
    )

    coimsa = es_rm and any(k in texto for k in KEYWORDS_COIMSA)
    induwork = contiene_keyword_induwork(texto)
    especial = any(k in texto for k in KEYWORDS_ESPECIALES)

    return {
        "coimsa": coimsa,
        "induwork": induwork,
        "especial": especial,
    }
