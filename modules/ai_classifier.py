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

MAX_RETRIES = 3

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

    texto = (
        f"{nombre} {descripcion}"
    ).lower()

    patrones_fuertes = [

        # ====================================================
        # PROTECCIÓN
        # ====================================================

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

        # ====================================================
        # CHALECOS
        # ====================================================

        "chaleco tactico",
        "chaleco táctico",
        "chalecos tacticos",
        "chalecos tácticos",

        "chaleco geologo",
        "chalecos geologos",

        "chaleco geólogo",
        "chalecos geólogos",

        "chaleco reflectante",
        "chalecos reflectantes",

        # ====================================================
        # BOTAS
        # ====================================================

        "botas tacticas",
        "botas tácticas",

        "bota tactica",
        "bota táctica",

        "botas militares",
        "bota militar",

        "botas swat",

        # ====================================================
        # UNIFORMES / VIGILANCIA
        # ====================================================

        "uniforme para guardias",
        "uniformes para guardias",

        "uniforme de guardias",
        "uniformes de guardias",

        "uniforme para vigilantes",
        "uniformes para vigilantes",

        "uniforme de vigilantes",
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

        # ====================================================
        # BASTONES
        # ====================================================

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

        # ====================================================
        # PORTAREVÓLVERES / FUNDAS
        # ====================================================

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

        # ====================================================
        # EQUIPAMIENTO
        # ====================================================

        "equipamiento tactico",
        "equipamiento táctico",

        "equipo tactico",
        "equipo táctico",

        "equipos tacticos",
        "equipos tácticos",

        "elementos tacticos",
        "elementos tácticos",

        # ====================================================
        # REFLECTANTES
        # ====================================================

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
Eres un clasificador de oportunidades de compra pública
para INDUWORK.

Tu única tarea es decidir si el OBJETO REAL de la compra
representa una oportunidad comercial razonablemente compatible
con la línea de productos de Induwork.

La oportunidad ya pasó un pre-filtro.

IMPORTANTE:
NO debes decidir solamente por una palabra.

Debes analizar el contexto completo, especialmente:

- título;
- descripción;
- productos solicitados;
- destino de los productos;
- organismo o unidad compradora cuando aparezca;
- si realmente se compra un BIEN FÍSICO.

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
- botas SWAT;
- botas para guardias;
- botas para vigilantes;
- botas de seguridad relacionadas con
  seguridad, vigilancia o equipamiento táctico.

PRODUCTOS ADICIONALES COMPATIBLES

También puede interesar un producto que no esté
literalmente en el catálogo actual si pertenece claramente
a la misma familia comercial.

Ejemplos:

- chaleco geólogo;
- chaleco de terreno;
- chaleco institucional;
- prendas físicas utilizadas por inspectores;
- vestuario físico para personal operativo;
- equipamiento físico para personal de seguridad;
- accesorios de portación relacionados con seguridad.

El catálogo actual es una REFERENCIA, NO una lista cerrada.

============================================================
REGLA PRINCIPAL
============================================================

APRUEBA cuando el OBJETO REAL sea adquirir un PRODUCTO FÍSICO
que razonablemente pueda ser vendido o suministrado por
Induwork o conseguido por Induwork dentro de su misma línea.

No es necesario que el nombre del producto coincida
exactamente con el catálogo.

============================================================
CASO IMPORTANTE: CHALECO GEÓLOGO
============================================================

Una compra como:

"Se solicita cotizar chaleco geólogo con logos bordados
para uso director de control"

puede ser RELEVANTE.

No rechaces una oportunidad simplemente porque diga
"geólogo".

Debes entender que el objeto real es un CHALECO FÍSICO.

Analiza además el destino institucional y el uso del producto.

============================================================
BOTAS
============================================================

Son RELEVANTES:

- botas tácticas;
- botas militares;
- botas SWAT;
- botas para guardias;
- botas para vigilantes;
- botas de seguridad destinadas a personal operativo,
  seguridad pública, vigilancia o similares.

Ejemplo:

Título:
"COMPRA DE BOTAS TACTICAS PROFESIONAL"

=> RELEVANTE.

Descripción:
"Solicitud de compra de botas tácticas para personal."

=> RELEVANTE.

Incluso si la descripción dice simplemente
"botas de seguridad", analiza el contexto completo.

============================================================
UNIFORMES
============================================================

RELEVANTE:

- uniformes para guardias;
- uniformes para vigilantes;
- vestuario de vigilancia;
- pantalones para guardias;
- casacas para vigilantes;
- camisas para vigilantes;
- prendas físicas institucionales para personal operativo.

============================================================
BASTONES
============================================================

RELEVANTE:

- bastones retráctiles;
- bastones tácticos;
- bastones de protección personal;
- porta bastones.

============================================================
PORTAREVÓLVERES / FUNDAS
============================================================

RELEVANTE:

- portarevólveres;
- fundas para revólver;
- pistoleras;
- fundas tácticas;
- accesorios de portación para personal de seguridad.

============================================================
REFLECTANTES
============================================================

RELEVANTE cuando sean prendas físicas:

- chalecos reflectantes;
- arneses reflectantes;
- prendas reflectantes;
- vestuario reflectante.

Especialmente para seguridad, vigilancia, inspectores,
trabajo operativo o actividades institucionales.

============================================================
TÁCTICO / TÁCTICA
============================================================

Las variantes:

- tactica;
- tacticas;
- táctica;
- tácticas;
- tactico;
- tacticos;
- táctico;
- tácticos;

pueden representar productos o servicios.

PRODUCTO:

"Botas tácticas"
=> RELEVANTE.

"Chalecos tácticos"
=> RELEVANTE.

"Uniformes tácticos"
=> RELEVANTE.

"Bastón táctico"
=> RELEVANTE.

"Equipamiento táctico"
=> RELEVANTE si corresponde a bienes físicos.

SERVICIO:

"Curso táctico"
=> NO RELEVANTE.

"Capacitación táctica"
=> NO RELEVANTE.

"Entrenamiento táctico"
=> NO RELEVANTE.

"Planificación táctica"
=> NO RELEVANTE.

"Servicio táctico"
=> NO RELEVANTE.

============================================================
SEGURIDAD
============================================================

La palabra "seguridad" sola NO es suficiente.

NO RELEVANTE:

"Servicio de seguridad para edificio."

RELEVANTE:

"Adquisición de botas de seguridad para Seguridad Pública."

RELEVANTE:

"Chalecos para inspectores de seguridad."

La diferencia es que debemos identificar el BIEN FÍSICO.

============================================================
NO RELEVANTE
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
- transporte;
- cualquier producto completamente ajeno.

============================================================
TÍTULO
============================================================

{nombre}

============================================================
DESCRIPCIÓN
============================================================

{descripcion[:6000]}

============================================================
DECISIÓN
============================================================

Sé permisivo cuando exista un PRODUCTO FÍSICO compatible
con la línea comercial de Induwork.

No seas excesivamente restrictivo.

Un producto nuevo puede ser relevante.

Pero no apruebes una oportunidad únicamente porque mencione
"seguridad", "protección", "táctico" o "vigilancia".

Determina el OBJETO REAL de compra.

============================================================
RESPUESTA
============================================================

Responde ÚNICAMENTE JSON válido:

{{
    "relevante": true,
    "motivo": "explicación breve y concreta",
    "terminos_detectados": ["término"]
}}

o:

{{
    "relevante": false,
    "motivo": "explicación breve y concreta",
    "terminos_detectados": ["término"]
}}

No agregues texto fuera del JSON.
"""


# ============================================================
# ERROR TRANSITORIO
# ============================================================

def _es_error_transitorio(
    error,
) -> bool:

    mensaje = str(
        error
    ).upper()

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
# CONSULTA GEMINI
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

    if client is None:

        print(
            "⚠️ Gemini no disponible. "
            "Aplicando fallback local."
        )

        return _fallback_local(
            nombre,
            descripcion,
        )

    # ========================================================
    # MODELO PRINCIPAL
    # ========================================================

    print(
        f"🤖 Gemini: intentando "
        f"{PRIMARY_MODEL}..."
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

            if not _es_error_transitorio(
                e
            ):

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
                    "devolvió error transitorio. "
                    f"Reintentando en {espera}s..."
                )

                time.sleep(
                    espera
                )

            else:

                print(
                    f"⚠️ {PRIMARY_MODEL} "
                    "agotó los reintentos."
                )

    # ========================================================
    # MODELO DE RESPALDO
    # ========================================================

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

            if not _es_error_transitorio(
                e
            ):

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
                    "devolvió error transitorio. "
                    f"Reintentando en {espera}s..."
                )

                time.sleep(
                    espera
                )

            else:

                print(
                    f"⚠️ {FALLBACK_MODEL} "
                    "agotó los reintentos."
                )

    # ========================================================
    # FALLBACK LOCAL
    # ========================================================

    print(
        "🛟 Gemini no respondió después "
        "de los reintentos. Aplicando "
        "fallback local."
    )

    resultado_local = _fallback_local(
        nombre,
        descripcion,
    )

    if resultado_local["induwork"]:

        print(
            "✅ Fallback local APROBÓ "
            "la oportunidad."
        )

    else:

        print(
            "⛔ Fallback local no encontró "
            "un patrón suficientemente fuerte."
        )

    return resultado_local