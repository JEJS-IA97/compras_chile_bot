KEYWORDS_COIMSA = [
    "limpieza", "aseo", "sanitizacion", "sanitización",
    "fumigacion", "fumigación", "desinfeccion", "desinfección",
]

KEYWORDS_INDUWORK = [
    # Términos centrales (muy específicos)
    "chaleco", "chalecos",
    "casco", "cascos",
    "anticorte", "anti corte", "anti-corte",
    "antibala", "anti bala", "anti balas", "antibalas",
    "balistico", "balístico",
    "tactico", "táctico",
    # Seguridad electrónica
    "cámara", "camara", "cámaras", "camaras",
    "videovigilancia", "televigilancia",
    "monitoreo",
    "circuito cerrado",
    "cctv",
    "alarma", "alarmas",
    "sensor", "sensores",
    "deteccion", "detección",
    "intrusion", "intrusión",
    "perimetro", "perímetro",
    # Frases compuestas (más precisas)
    "chaleco antibala", "chalecos antibalas",
    "chaleco anticorte", "chalecos anticorte",
    "casco balistico", "casco balístico",
    "uniforme tactico", "uniforme táctico",
    "equipamiento tactico", "equipamiento táctico",
    "chaleco anti-corte",
    "chaleco anti bala",
    "sistema de videovigilancia",
    "sistema de televigilancia",
    "camaras de seguridad", "cámaras de seguridad",
    "circuito cerrado de television", "circuito cerrado de televisión",
    "sistema de alarmas",
    "monitoreo de seguridad",
    "control de acceso",
    "seguridad perimetral",
    "sistema de seguridad",
    "equipo de seguridad",
    # Términos adicionales (pero menos genéricos)
    "blindaje", "blindado",
    "policial", "policiales",
    "vigilancia",
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

    # Coimsa (sin cambios)
    coimsa = es_rm and any(k in texto for k in KEYWORDS_COIMSA)

    # --- Induwork (nueva lógica con seguridad electrónica) ---
    # 1. Palabras muy específicas que por sí solas son suficientes
    palabras_especificas = [
        "chaleco", "chalecos",
        "casco", "cascos",
        "antibala", "anti bala", "anti balas", "antibalas",
        "balistico", "balístico",
        "anticorte", "anti corte", "anti-corte",
        # Seguridad electrónica
        "videovigilancia", "televigilancia",
        "cctv",
        "camara", "cámara", "camaras", "cámaras",
        "circuito cerrado",
        "alarma", "alarmas",
        "sensor", "sensores",
        "deteccion", "detección",
        "intrusion", "intrusión",
        "perimetro", "perímetro",
    ]
    tiene_palabra_especifica = any(k in texto for k in palabras_especificas)

    # 2. Frases compuestas (también suficientes por sí solas)
    frases_compuestas = [
        "chaleco antibala", "chalecos antibalas",
        "chaleco anticorte", "chalecos anticorte",
        "casco balistico", "casco balístico",
        "uniforme tactico", "uniforme táctico",
        "equipamiento tactico", "equipamiento táctico",
        "chaleco anti-corte",
        "chaleco anti bala",
        "sistema de videovigilancia",
        "sistema de televigilancia",
        "camaras de seguridad", "cámaras de seguridad",
        "circuito cerrado de television", "circuito cerrado de televisión",
        "sistema de alarmas",
        "monitoreo de seguridad",
        "control de acceso",
        "seguridad perimetral",
        "sistema de seguridad",
        "equipo de seguridad",
        "calzado de seguridad",
        "ropa de seguridad",
        "ropa de proteccion",
        "ropa de protección",
        "elementos de proteccion",
        "elementos de protección",
        "equipamiento de seguridad",
        "equipamiento de proteccion",
        "equipamiento de protección",
        "uniforme de seguridad",
        "uniforme de proteccion",
        "uniforme de protección",
    ]
    tiene_frase_compuesta = any(frase in texto for frase in frases_compuestas)

    # 3. Palabras complementarias que requieren acompañar a 'seguridad' o 'protección'
    palabras_complementarias = [
        "calzado", "ropa", "uniforme", "elementos",
        "equipamiento", "vestuario",
        # También añadimos "sistema" y "equipo" porque con "seguridad" suelen referirse a productos
        "sistema", "equipo"
    ]
    # Verificar si aparece alguna complementaria junto con seguridad o protección
    tiene_complementaria_con_seguridad = any(
        (palabra in texto) and ("seguridad" in texto or "proteccion" in texto or "protección" in texto)
        for palabra in palabras_complementarias
    )

    # Induwork = alguna de las condiciones se cumple
    induwork = (
        tiene_palabra_especifica or
        tiene_frase_compuesta or
        tiene_complementaria_con_seguridad
    )

    # Especial (sin cambios)
    especial = any(k in texto for k in KEYWORDS_ESPECIALES)

    return {
        "coimsa": coimsa,
        "induwork": induwork,
        "especial": especial,
    }