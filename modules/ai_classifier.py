# modules/ai_classifier.py

import json
import time

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY


# ============================================================
# MODELOS
# ============================================================

PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.1-flash-lite"

# Reintentos para errores temporales.
MAX_RETRIES = 3

# Backoff progresivo.
RETRY_DELAYS = [
    2,
    5,
    10,
]


# ============================================================
# CLIENTE GEMINI
# ============================================================

client = None


if GEMINI_API_KEY:
    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        print(
            "✅ Gemini configurado correctamente "
            f"({PRIMARY_MODEL})."
        )

    except Exception as e:

        print(
            f"❌ Error al configurar Gemini: {e}"
        )

else:

    print(
        "⚠️ GEMINI_API_KEY no configurada. "
        "La validación IA de Induwork estará deshabilitada."
    )


# ============================================================
# RESPUESTA VACÍA
# ============================================================

def _respuesta_vacia() -> dict:
    """
    Respuesta segura cuando la IA no puede clasificar.
    """

    return {
        "coimsa": False,
        "induwork": False,
        "especial": False,
        "motivo": "",
        "terminos_detectados": [],
    }


# ============================================================
# FALLBACK LOCAL
# ============================================================

def _fallback_local(
    nombre: str,
    descripcion: str,
) -> dict:
    """
    Fallback determinístico para evitar perder oportunidades
    muy claras cuando Gemini no está disponible.

    SOLO aprueba coincidencias que representan productos
    claramente relacionados con la línea comercial de Induwork.
    """

    texto = (
        f"{nombre} {descripcion}"
    ).lower()

    patrones_fuertes = [
        # Protección
        "chaleco antibala",
        "chalecos antibalas",
        "chaleco balistico",
        "chalecos balisticos",
        "chaleco balístico",
        "chalecos balísticos",
        "chaleco anticorte",
        "chalecos anticorte",
        "panel antibala",
        "paneles antibalas",
        "panel balistico",
        "paneles balisticos",
        "panel balístico",
        "paneles balísticos",
        "casco balistico",
        "cascos balisticos",
        "casco balístico",
        "cascos balísticos",
        "casco tactico",
        "cascos tacticos",
        "casco táctico",
        "cascos tácticos",

        # Botas
        "botas tacticas",
        "botas tácticas",
        "bota tactica",
        "bota táctica",
        "botas militares",
        "botas swat",

        # Uniformes / vigilancia
        "uniforme para guardias",
        "uniformes para guardias",
        "uniforme de guardias",
        "uniformes de guardias",
        "uniforme para vigilantes",
        "uniformes para vigilantes",
        "uniforme de vigilante",
        "uniformes de vigilantes",
        "vestuario para guardias",
        "vestuario de guardias",
        "vestuario para vigilantes",
        "vestuario de vigilantes",
        "pantalon de vigilancia",
        "pantalón de vigilancia",
        "casaca de vigilancia",
        "camisa de vigilante",
        "camisa para vigilante",

        # Bastones
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

        # Portarevólver / fundas
        "portarevolver",
        "portarevólver",
        "porta revolver",
        "porta revólver",
        "funda para revolver",
        "funda para revólver",
        "funda de paleta para revolver",
        "funda de paleta para revólver",
        "pistolera tactica",
        "pistolera táctica",
        "pistolera militar",
        "pistoleras tacticas",
        "pistoleras tácticas",

        # Equipamiento táctico
        "equipamiento tactico",
        "equipamiento táctico",
        "equipo tactico",
        "equipo táctico",
        "equipos tacticos",
        "equipos tácticos",
        "elementos tacticos",
        "elementos tácticos",

        # Chalecos tácticos
        "chaleco tactico",
        "chaleco táctico",
        "chalecos tacticos",
        "chalecos tácticos",

        # Guantes tácticos
        "guante tactico",
        "guante táctico",
        "guantes tacticos",
        "guantes tácticos",

        # Cinturones tácticos
        "cinturon tactico",
        "cinturón táctico",
        "cinturones tacticos",
        "cinturones tácticos",

        # Mochilas tácticas
        "mochila tactica",
        "mochila táctica",
        "mochilas tacticas",
        "mochilas tácticas",

        # Reflectantes
        "chaleco reflectante",
        "chalecos reflectantes",
        "arnes reflectante",
        "arnés reflectante",
        "arneses reflectantes",
    ]

    patrones_encontrados = [
        patron
        for patron in patrones_fuertes
        if patron in texto
    ]

    if not patrones_encontrados:
        return _respuesta_vacia()

    return {
        "coimsa": False,
        "induwork": True,
        "especial": False,
        "motivo": (
            "Fallback local: se detectó un producto "
            "claramente relacionado con la línea comercial "
            "de Induwork."
        ),
        "terminos_detectados": (
            patrones_encontrados[:10]
        ),
    }


# ============================================================
# PROMPT
# ============================================================

def _crear_prompt(
    nombre: str,
    descripcion: str,
) -> str:

    return f"""
Eres un clasificador de licitaciones públicas de Chile
para INDUWORK.

Tu tarea es determinar si una licitación puede ser una
oportunidad comercial razonablemente relevante para Induwork.

La licitación YA superó un primer filtro de palabras clave.
Tu trabajo ahora es interpretar el CONTEXTO y el OBJETO REAL
de la compra.

No necesitas que el producto aparezca literalmente en el
catálogo actual.

Induwork puede cotizar o conseguir productos nuevos siempre
que pertenezcan claramente a la misma línea comercial.

============================================================
LÍNEA COMERCIAL DE INDUWORK
============================================================

Induwork trabaja principalmente con:

PROTECCIÓN PERSONAL
- chalecos anticorte;
- chalecos antibalas;
- chalecos balísticos;
- paneles anticorte;
- paneles antibalas;
- paneles balísticos;
- cascos balísticos;
- lentes balísticos;
- fundas para chalecos.

EQUIPAMIENTO TÁCTICO
- chalecos tácticos;
- cascos tácticos;
- uniformes tácticos;
- pantalones tácticos;
- poleras tácticas;
- chaquetas tácticas;
- guantes tácticos;
- cinturones tácticos;
- mochilas tácticas;
- linternas tácticas;
- brújulas tácticas;
- accesorios MOLLE;
- pouch;
- porta bastones;
- bastones retráctiles;
- bastones de protección personal;
- esposas;
- porta esposas;
- pistoleras;
- portarevólveres;
- fundas para armas;
- accesorios tácticos.

VESTUARIO DE SEGURIDAD
- uniformes para guardias;
- uniformes para vigilantes;
- pantalones de vigilancia;
- casacas de vigilancia;
- camisas para vigilantes;
- gorros y kepis;
- prendas institucionales;
- chalecos reflectantes;
- arneses reflectantes.

CALZADO
- botas tácticas;
- botas militares;
- botas de seguridad relacionadas con
  seguridad, vigilancia o equipamiento táctico.

También puede interesar cualquier PRODUCTO NUEVO que sea
razonablemente equivalente, complementario o perteneciente
a estas mismas familias.

============================================================
REGLA PRINCIPAL
============================================================

APRUEBA si el objeto real de la licitación es comprar,
adquirir, suministrar, proveer o entregar un PRODUCTO FÍSICO
relacionado con:

- equipamiento táctico;
- protección personal;
- vestuario para guardias;
- vestuario para vigilantes;
- seguridad personal;
- protección balística;
- protección anticorte;
- protección antipunzón;
- calzado táctico o de seguridad;
- bastones de protección;
- portarevólveres;
- fundas;
- pistoleras;
- accesorios tácticos;
- productos equivalentes o complementarios.

============================================================
NO EXIJAS EL PRODUCTO EXACTO
============================================================

El catálogo actual es una REFERENCIA.

NO significa que Induwork solo pueda vender esos modelos.

Ejemplo:

Catálogo actual:
"Botas Tácticas Militares Delta"

Licitación:
"Botas Tácticas marca X"

=> RELEVANTE.

Catálogo actual:
"Chaleco Balístico Molle IIIA"

Licitación:
"Chaleco antibalas nivel IIIA de otro fabricante"

=> RELEVANTE.

Catálogo actual:
"Funda de Paleta para Revólver"

Licitación:
"Portarevólver para personal de seguridad"

=> RELEVANTE.

============================================================
TÁCTICO / TÁCTICA
============================================================

La palabra "táctico" puede referirse a un producto o a
una actividad/servicio.

PRODUCTO:

"Botas tácticas"
=> RELEVANTE.

"Uniformes tácticos"
=> RELEVANTE.

"Chalecos tácticos"
=> RELEVANTE.

"Guantes tácticos"
=> RELEVANTE.

"Bastón táctico"
=> RELEVANTE.

"Equipamiento táctico"
=> RELEVANTE si se refiere a bienes físicos.

ACTIVIDAD O SERVICIO:

"Capacitación táctica"
=> NO RELEVANTE.

"Curso táctico"
=> NO RELEVANTE.

"Entrenamiento táctico"
=> NO RELEVANTE.

"Planificación táctica"
=> NO RELEVANTE.

"Operación táctica"
=> NO RELEVANTE.

"Servicio táctico"
=> NO RELEVANTE.

============================================================
BOTAS
============================================================

Las botas son relevantes para Induwork cuando son:

- botas tácticas;
- botas militares;
- botas SWAT;
- botas para guardias;
- botas para vigilantes;
- botas de seguridad destinadas a personal operativo,
  seguridad pública, vigilancia o similares.

IMPORTANTE:

No rechaces una licitación de botas tácticas porque la
descripción use una denominación más genérica como
"botas de seguridad".

Ejemplo:

Título:
"Botas Tácticas para DISEPT"

Descripción:
"Adquisición de botas de seguridad para la Dirección
de Seguridad Pública y Territorial."

=> RELEVANTE.

============================================================
UNIFORMES DE GUARDIAS Y VIGILANTES
============================================================

Las licitaciones de vestuario físico para guardias,
vigilantes o personal de seguridad son RELEVANTES.

Ejemplos:

"Adquisición de uniformes para guardias"
=> RELEVANTE.

"Uniformes para vigilantes"
=> RELEVANTE.

"Pantalones para guardias"
=> RELEVANTE.

"Casacas para vigilantes"
=> RELEVANTE.

"Camisas institucionales para vigilantes"
=> RELEVANTE.

============================================================
BASTONES Y PORTAREVÓLVERES
============================================================

Son productos relevantes:

- bastones retráctiles;
- bastones tácticos;
- bastones de protección personal;
- porta bastones;
- portarevólveres;
- fundas para revólver;
- pistoleras;
- fundas tácticas;
- accesorios para portar equipamiento.

============================================================
REFLECTANTES
============================================================

Pueden ser relevantes:

- chalecos reflectantes;
- arneses reflectantes;
- prendas reflectantes;
- vestuario reflectante.

Especialmente cuando están destinados a personal
de seguridad, vigilancia, trabajo operativo o similares.

============================================================
SEGURIDAD
============================================================

La palabra "seguridad" por sí sola NO es suficiente.

NO RELEVANTE:

"Servicio de seguridad para edificio."

Pero:

"Adquisición de botas de seguridad para personal
de Seguridad Pública."

=> RELEVANTE si el contexto identifica las botas
como producto físico compatible con la línea.

============================================================
CASOS QUE DEBES RECHAZAR
============================================================

Rechaza:

- servicios de vigilancia;
- contratación de guardias;
- monitoreo;
- cámaras;
- CCTV;
- alarmas;
- sensores;
- instalación de sistemas;
- mantenimiento de sistemas;
- consultoría;
- asesorías;
- capacitaciones;
- cursos;
- entrenamiento como servicio;
- software;
- desarrollo informático;
- obras;
- servicios administrativos;
- servicios de transporte;
- productos completamente ajenos a la línea.

============================================================
TÍTULO
============================================================

{nombre}

============================================================
DESCRIPCIÓN
============================================================

{descripcion[:4000]}

============================================================
DECISIÓN
============================================================

Responde RELEVANTE cuando exista una relación comercial
clara con la línea de Induwork.

No seas excesivamente restrictivo.

Un producto nuevo puede ser relevante si pertenece
claramente a la misma familia comercial.

Tampoco apruebes una licitación solo porque mencione
"seguridad", "táctica" o "protección" incidentalmente.

Analiza el objeto real de compra.

============================================================
RESPUESTA
============================================================

Responde ÚNICAMENTE JSON válido:

{{
    "relevante": true,
    "motivo": "explicación breve y concreta",
    "terminos_detectados": [
        "término"
    ]
}}

o:

{{
    "relevante": false,
    "motivo": "explicación breve y concreta",
    "terminos_detectados": [
        "término"
    ]
}}

No agregues ningún texto fuera del JSON.
"""


# ============================================================
# DETECTAR ERROR TRANSITORIO
# ============================================================

def _es_error_transitorio(
    error,
) -> bool:

    mensaje = str(error).upper()

    return any(
        codigo in mensaje
        for codigo in (
            "503",
            "UNAVAILABLE",
            "429",
            "RESOURCE_EXHAUSTED",
            "500",
            "INTERNAL",
            "504",
            "DEADLINE_EXCEEDED",
        )
    )


# ============================================================
# LLAMADA A GEMINI
# ============================================================

def _consultar_modelo(
    model_name: str,
    nombre: str,
    descripcion: str,
):

    prompt = _crear_prompt(
        nombre,
        descripcion,
    )

    return client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=300,
        ),
    )


# ============================================================
# PROCESAR RESPUESTA
# ============================================================

def _procesar_respuesta(
    response,
) -> dict:

    texto = (
        response.text or ""
    ).strip()

    if not texto:
        return _respuesta_vacia()

    datos = json.loads(
        texto
    )

    relevante = bool(
        datos.get(
            "relevante",
            False,
        )
    )

    motivo = str(
        datos.get(
            "motivo",
            "",
        )
        or ""
    ).strip()

    terminos = datos.get(
        "terminos_detectados",
        [],
    )

    if not isinstance(
        terminos,
        list,
    ):
        terminos = []

    return {
        "coimsa": False,
        "induwork": relevante,
        "especial": False,
        "motivo": motivo,
        "terminos_detectados": [
            str(termino).strip()
            for termino in terminos[:10]
        ],
    }


# ============================================================
# CLASIFICACIÓN PRINCIPAL
# ============================================================

def clasificar_con_gemini(
    nombre: str,
    descripcion: str,
) -> dict:

    # --------------------------------------------------------
    # Si no hay cliente, utilizar fallback local.
    # --------------------------------------------------------

    if client is None:

        print(
            "⚠️ Gemini no disponible. "
            "Aplicando fallback local."
        )

        return _fallback_local(
            nombre,
            descripcion,
        )

    # --------------------------------------------------------
    # PRIMER MODELO
    # --------------------------------------------------------

    print(
        f"🤖 Gemini: intentando {PRIMARY_MODEL}..."
    )

    for intento in range(
        MAX_RETRIES
    ):

        try:

            response = _consultar_modelo(
                PRIMARY_MODEL,
                nombre,
                descripcion,
            )

            return _procesar_respuesta(
                response
            )

        except Exception as e:

            if not _es_error_transitorio(e):

                print(
                    "⚠️ Error no transitorio "
                    f"de Gemini: {e}"
                )

                break

            if intento < MAX_RETRIES - 1:

                espera = RETRY_DELAYS[
                    intento
                ]

                print(
                    f"⚠️ {PRIMARY_MODEL} "
                    f"devolvió error transitorio "
                    f"({e}). "
                    f"Reintentando en "
                    f"{espera}s..."
                )

                time.sleep(
                    espera
                )

            else:

                print(
                    f"⚠️ {PRIMARY_MODEL} "
                    "agotó los reintentos."
                )

    # --------------------------------------------------------
    # MODELO DE RESPALDO
    # --------------------------------------------------------

    print(
        f"🔄 Gemini: intentando modelo "
        f"de respaldo {FALLBACK_MODEL}..."
    )

    for intento in range(
        MAX_RETRIES
    ):

        try:

            response = _consultar_modelo(
                FALLBACK_MODEL,
                nombre,
                descripcion,
            )

            print(
                f"✅ Clasificación obtenida "
                f"con {FALLBACK_MODEL}."
            )

            return _procesar_respuesta(
                response
            )

        except Exception as e:

            if not _es_error_transitorio(e):

                print(
                    "⚠️ Error no transitorio "
                    f"en {FALLBACK_MODEL}: {e}"
                )

                break

            if intento < MAX_RETRIES - 1:

                espera = RETRY_DELAYS[
                    intento
                ]

                print(
                    f"⚠️ {FALLBACK_MODEL} "
                    f"devolvió error transitorio. "
                    f"Reintentando en "
                    f"{espera}s..."
                )

                time.sleep(
                    espera
                )

            else:

                print(
                    f"⚠️ {FALLBACK_MODEL} "
                    "agotó los reintentos."
                )

    # --------------------------------------------------------
    # FALLBACK LOCAL
    # --------------------------------------------------------

    print(
        "🛟 Gemini no respondió después de "
        "los reintentos. Aplicando fallback "
        "local para evitar perder una "
        "oportunidad claramente relevante."
    )

    resultado_local = _fallback_local(
        nombre,
        descripcion,
    )

    if resultado_local["induwork"]:

        print(
            "✅ Fallback local APROBÓ "
            "la licitación."
        )

        return resultado_local

    print(
        "⛔ Fallback local no encontró "
        "evidencia suficiente."
    )

    return _respuesta_vacia()