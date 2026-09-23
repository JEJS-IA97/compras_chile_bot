# modules/filters.py


# ============================================================
# COIMSA
# ============================================================

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

# IMPORTANTE:
# Estas 28 expresiones se mantienen exactamente porque
# corresponden a las búsquedas manuales que utiliza el usuario
# en Mercado Público.
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
# PRODUCTOS ADICIONALES INDUWORK
# ============================================================

# Estas palabras son ADICIONALES.
#
# NO reemplazan las 28 búsquedas originales.
#
# Tampoco significan que cualquier coincidencia sea relevante.
# Solo permiten que una oportunidad llegue al análisis cuando
# existe contexto comercial compatible con Induwork.
KEYWORDS_INDUWORK_PRODUCTOS = [
    # Chalecos
    "chaleco",
    "chalecos",
    "chaleco geologo",
    "chalecos geologos",
    "chaleco geólogo",
    "chalecos geólogos",

    # Calzado
    "bota",
    "botas",
    "calzado",

    # Vestuario
    "uniforme",
    "uniformes",
    "vestuario",
    "vestuarios",
    "prenda",
    "prendas",

    # Protección / equipamiento
    "casco",
    "cascos",
    "guante",
    "guantes",
    "gafa",
    "gafas",
    "lente",
    "lentes",

    # Bastones
    "baston",
    "bastones",
    "bastón",
    "bastones",
    "porta baston",
    "porta bastones",
    "portabaston",
    "portabastones",

    # Portación
    "portarevolver",
    "portarevólver",
    "porta revolver",
    "porta revólver",
    "pistolera",
    "pistoleras",
    "funda",
    "fundas",

    # Accesorios tácticos
    "mochila",
    "mochilas",
    "cinturon",
    "cinturón",
    "cinturones",
    "pouch",
    "molle",
    "linterna",
    "linternas",
    "radio",
    "radios",
    "esposa",
    "esposas",
    "porta esposas",

    # Reflectantes
    "reflectante",
    "reflectantes",
    "arnes",
    "arneses",
]


# ============================================================
# CONTEXTO INDUWORK
# ============================================================

# Para los términos adicionales exigimos contexto.
#
# Ejemplo:
#
# "Adquisición de botas"
# -> no basta por sí sola.
#
# "Adquisición de botas de seguridad para patrulleros"
# -> sí puede pasar a Gemini.
#
# "Chaleco geólogo con logos bordados para director de control"
# -> puede pasar porque "chaleco geólogo" es una combinación
#    de producto suficientemente específica.
KEYWORDS_CONTEXTO_INDUWORK = [
    "seguridad",
    "seguridad publica",
    "seguridad pública",
    "guardia",
    "guardias",
    "vigilante",
    "vigilantes",
    "patrullero",
    "patrulleros",
    "inspector",
    "inspectores",
    "inspeccion",
    "inspección",
    "fiscalizador",
    "fiscalizadores",
    "control",
    "personal",
    "funcionario",
    "funcionarios",
    "operativo",
    "operativos",
    "vigilancia",
    "proteccion",
    "protección",
    "policial",
    "policiales",
    "municipal",
    "municipales",
    "militar",
    "militares",
    "ejercito",
    "ejército",
    "fuerzas armadas",
    "seguridad publica e inspeccion municipal",
    "seguridad pública e inspección municipal",
]


# ============================================================
# COMBINACIONES FUERTES
# ============================================================

# Casos donde el propio producto ya describe una familia
# comercial suficientemente concreta.
#
# Igual pasan por Gemini posteriormente.
COMBINACIONES_INDUWORK_FUERTES = [
    "chaleco geologo",
    "chalecos geologos",
    "chaleco geólogo",
    "chalecos geólogos",

    "botas tacticas",
    "botas tácticas",
    "bota tactica",
    "bota táctica",

    "botas militares",
    "bota militar",
    "botas swat",

    "uniforme para guardias",
    "uniformes para guardias",
    "uniforme de guardias",
    "uniformes de guardias",

    "uniforme para vigilantes",
    "uniformes para vigilantes",
    "uniforme de vigilantes",
    "uniformes de vigilantes",

    "vestuario para guardias",
    "vestuario para vigilantes",

    "pantalon de vigilancia",
    "pantalón de vigilancia",

    "casaca de vigilancia",

    "camisa de vigilante",
    "camisa para vigilante",

    "chaleco reflectante",
    "chalecos reflectantes",

    "arnes reflectante",
    "arnés reflectante",

    "baston retractil",
    "bastón retráctil",

    "bastones retractiles",
    "bastones retráctiles",

    "baston tactico",
    "bastón táctico",

    "bastones tacticos",
    "bastones tácticos",

    "baston de proteccion",
    "bastón de protección",

    "bastones de proteccion",
    "bastones de protección",

    "portarevolver",
    "portarevólver",

    "porta revolver",
    "porta revólver",

    "pistolera tactica",
    "pistolera táctica",

    "pistolera militar",
    "pistoleras tacticas",
    "pistoleras tácticas",

    "funda para revolver",
    "funda para revólver",

    "funda de paleta para revolver",
    "funda de paleta para revólver",

    "equipamiento tactico",
    "equipamiento táctico",

    "equipo tactico",
    "equipo táctico",

    "equipos tacticos",
    "equipos tácticos",

    "elementos tacticos",
    "elementos tácticos",

    "chaleco tactico",
    "chaleco táctico",

    "chalecos tacticos",
    "chalecos tácticos",
]


# ============================================================
# ESPECIALES
# ============================================================

KEYWORDS_ESPECIALES = [
    "actividad social",
    "proyecto social",
    "programa social",
    "desarrollo informatico",
    "desarrollo informático",
]


# ============================================================
# UTILIDADES
# ============================================================

def _normalizar_texto(texto: str) -> str:
    return (
        str(texto or "")
        .lower()
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _contiene_alguna_keyword(
    texto: str,
    keywords: list,
) -> bool:
    texto = _normalizar_texto(texto)

    return any(
        keyword.lower() in texto
        for keyword in keywords
    )


def _keywords_detectadas(
    texto: str,
    keywords: list,
) -> list:
    texto = _normalizar_texto(texto)

    resultado = []

    for keyword in keywords:

        if keyword.lower() in texto:
            resultado.append(
                keyword
            )

    return resultado


# ============================================================
# CONTEXTO ADICIONAL INDUWORK
# ============================================================

def contiene_contexto_induwork(
    texto: str,
) -> bool:
    """
    Determina si existe contexto comercial compatible con
    Induwork para habilitar las keywords adicionales.
    """

    texto = _normalizar_texto(texto)

    return _contiene_alguna_keyword(
        texto,
        KEYWORDS_CONTEXTO_INDUWORK,
    )


def contiene_producto_adicional_induwork(
    texto: str,
) -> bool:
    """
    Determina si aparece un producto adicional de Induwork
    y además existe contexto compatible.

    Las 28 keywords originales NO utilizan esta función.
    """

    texto = _normalizar_texto(texto)

    producto = _contiene_alguna_keyword(
        texto,
        KEYWORDS_INDUWORK_PRODUCTOS,
    )

    if not producto:
        return False

    if _contiene_alguna_keyword(
        texto,
        COMBINACIONES_INDUWORK_FUERTES,
    ):
        return True

    return contiene_contexto_induwork(
        texto
    )


# ============================================================
# INDUWORK
# ============================================================

def contiene_keyword_induwork(
    texto: str,
) -> bool:
    """
    El resultado es verdadero cuando:

    1. aparece cualquiera de las 28 búsquedas manuales; o
    2. aparece un producto adicional + contexto Induwork; o
    3. aparece una combinación fuerte de producto.
    """

    texto = _normalizar_texto(texto)

    # --------------------------------------------------------
    # Las 28 originales tienen prioridad.
    # --------------------------------------------------------

    if _contiene_alguna_keyword(
        texto,
        KEYWORDS_INDUWORK,
    ):
        return True

    # --------------------------------------------------------
    # Segunda capa contextual.
    # --------------------------------------------------------

    return contiene_producto_adicional_induwork(
        texto
    )


def keywords_induwork_detectadas(
    texto: str,
) -> list:
    """
    Devuelve:

    - coincidencias de las 28 búsquedas originales;
    - coincidencias adicionales solo cuando el contexto
      también es compatible.
    """

    texto = _normalizar_texto(texto)

    resultado = _keywords_detectadas(
        texto,
        KEYWORDS_INDUWORK,
    )

    contexto_adicional = (
        contiene_producto_adicional_induwork(
            texto
        )
    )

    if contexto_adicional:

        adicionales = _keywords_detectadas(
            texto,
            KEYWORDS_INDUWORK_PRODUCTOS,
        )

        for keyword in adicionales:

            if keyword not in resultado:

                resultado.append(
                    keyword
                )

    return resultado


# ============================================================
# PREFILTRO GENERAL
# ============================================================

def posible_relevante(
    texto: str,
) -> bool:
    """
    Prefiltro general utilizado antes de solicitar detalle.

    Conserva las 28 búsquedas manuales y agrega únicamente
    productos adicionales cuando el contexto es Induwork.

    No representa una aprobación comercial.
    """

    texto = _normalizar_texto(texto)

    # --------------------------------------------------------
    # Coimsa / Especial / 28 originales
    # --------------------------------------------------------

    if _contiene_alguna_keyword(
        texto,
        KEYWORDS_COIMSA,
    ):
        return True

    if _contiene_alguna_keyword(
        texto,
        KEYWORDS_ESPECIALES,
    ):
        return True

    if _contiene_alguna_keyword(
        texto,
        KEYWORDS_INDUWORK,
    ):
        return True

    # --------------------------------------------------------
    # Productos adicionales Induwork.
    # --------------------------------------------------------

    return contiene_producto_adicional_induwork(
        texto
    )


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluar_licitacion(
    licitacion: dict,
) -> dict:

    nombre = _normalizar_texto(
        licitacion.get(
            "nombre",
            "",
        )
    )

    descripcion = _normalizar_texto(
        licitacion.get(
            "descripcion",
            "",
        )
    )

    region = _normalizar_texto(
        licitacion.get(
            "region",
            "",
        )
    )

    texto_productos = _normalizar_texto(
        licitacion.get(
            "texto_productos",
            "",
        )
    )

    texto = (
        f"{nombre} "
        f"{descripcion} "
        f"{texto_productos}"
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
        and _contiene_alguna_keyword(
            texto,
            KEYWORDS_COIMSA,
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

    especial = _contiene_alguna_keyword(
        texto,
        KEYWORDS_ESPECIALES,
    )

    return {
        "coimsa": coimsa,
        "induwork": induwork,
        "especial": especial,
    }