KEYWORDS_COIMSA = [
    "limpieza",
    "aseo",
    "sanitizacion",
    "sanitización",
    "fumigacion",
    "fumigación",
    "desinfeccion",
    "desinfección",
]

# ============================================================
# BÚSQUEDAS MANUALES DE INDUWORK
# ============================================================

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

# ============================================================
# PALABRAS CLAVE ESPECIALES
# ============================================================

KEYWORDS_ESPECIALES = [
    "actividad social",
    "proyecto social",
    "programa social",
    "desarrollo informatico",
    "desarrollo informático",
]

# ============================================================
# TODAS LAS KEYWORDS
# ============================================================

TODAS_LAS_KEYWORDS = (
    KEYWORDS_COIMSA
    + KEYWORDS_INDUWORK
    + KEYWORDS_ESPECIALES
)


# ============================================================
# INDUWORK
# ============================================================

def contiene_keyword_induwork(texto: str) -> bool:
    """
    Determina si el texto contiene alguna de las
    28 búsquedas manuales de Induwork.
    """

    texto = (texto or "").lower()

    return any(
        keyword in texto
        for keyword in KEYWORDS_INDUWORK
    )


def keywords_induwork_detectadas(texto: str) -> list:
    """
    Devuelve todas las keywords de Induwork
    que aparecen dentro del texto.
    """

    texto = (texto or "").lower()

    return [
        keyword
        for keyword in KEYWORDS_INDUWORK
        if keyword in texto
    ]


# ============================================================
# PREFILTRO GENERAL
# ============================================================

def posible_relevante(texto: str) -> bool:
    """
    Prefiltro rápido.

    Determina si una licitación contiene alguna palabra
    relacionada con cualquiera de las categorías.
    """

    texto = (texto or "").lower()

    return any(
        keyword in texto
        for keyword in TODAS_LAS_KEYWORDS
    )


# ============================================================
# EVALUACIÓN DE LICITACIÓN
# ============================================================

def evaluar_licitacion(licitacion: dict) -> dict:
    """
    Evalúa una licitación utilizando las reglas
    de cada empresa.

    Induwork:
        Solo utiliza las 28 búsquedas manuales.

    Coimsa:
        Mantiene sus palabras actuales.

    Especial:
        Mantiene sus palabras actuales.
    """

    nombre = (
        licitacion.get(
            "nombre",
            "",
        )
        or ""
    ).lower()

    descripcion = (
        licitacion.get(
            "descripcion",
            "",
        )
        or ""
    ).lower()

    region = (
        licitacion.get(
            "region",
            "",
        )
        or ""
    ).lower()

    texto = (
        f"{nombre} {descripcion}"
    )

    # ========================================================
    # COIMSA
    # ========================================================

    es_rm = (
        "metropolitana" in region
        or "santiago" in region
        or region.strip() == "rm"
    )

    coimsa = (
        es_rm
        and any(
            keyword in texto
            for keyword in KEYWORDS_COIMSA
        )
    )

    # ========================================================
    # INDUWORK
    # ========================================================

    induwork = contiene_keyword_induwork(
        texto
    )

    # ========================================================
    # ESPECIAL
    # ========================================================

    especial = any(
        keyword in texto
        for keyword in KEYWORDS_ESPECIALES
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    return {
        "coimsa": coimsa,
        "induwork": induwork,
        "especial": especial,
    }