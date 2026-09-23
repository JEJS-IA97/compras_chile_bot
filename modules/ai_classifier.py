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
    organismo: str = "",
    region: str = "",
) -> str:

    organismo_txt = (
        organismo.strip()
        or "No informado"
    )

    region_txt = (
        region.strip()
        or "No informada"
    )

    return f"""
Eres un clasificador de oportunidades de compra pública
para INDUWORK.

Tu única tarea es decidir si el OBJETO REAL de la compra
es compatible con la línea comercial de Induwork:
equipo táctico, balístico y de seguridad PARA GUARDIAS
Y VIGILANTES (no uniformes de oficina ni de hospitales).

La oportunidad ya pasó un pre-filtro.

IMPORTANTE:
NO decidas solamente por una palabra.

Analiza el contexto completo:
- título;
- descripción;
- productos solicitados;
- destino real de los productos;
- organismo o unidad compradora;
- si realmente se compra un BIEN FÍSICO.

Organismo comprador: {organismo_txt}
Región: {region_txt}

============================================================
LÍNEA COMERCIAL DE INDUWORK
============================================================

Induwork trabaja principalmente con:

PROTECCIÓN BALÍSTICA / ANTICORTE

- chalecos anticorte y antibalas;
- paneles anticorte y antibalas;
- cascos y lentes balísticos.

EQUIPAMIENTO TÁCTICO

- chalecos, cascos y uniformes tácticos;
- pantalones, poleras, chaquetas y guantes tácticos;
- cinturones, mochilas y accesorios MOLLE;
- bastones retráctiles, pistoleras, portarevólveres;
- esposas y porta esposes.

VESTUARIO DE SEGURIDAD (solo guardias/vigilantes)

- uniformes y vestuario PARA guardias o vigilantes;
- pantalones y casacas de vigilancia;
- gorros y kepis de seguridad;
- chalecos y arneses reflectantes.

CALZADO (solo operativo/seguridad)

- botas tácticas, militares o SWAT;
- botas para guardias o vigilantes.

PRODUCTOS ADICIONALES

- chaleco geólogo o de terreno;
- equipamiento físico para personal de seguridad.

============================================================
REGLA PRINCIPAL
============================================================

APRUEBA solo si el OBJETO REAL es un PRODUCTO FÍSICO
que Induwork pueda suministrar dentro de su línea
(táctico, balístico o vestuario de seguridad).

============================================================
NO RELEVANTE — RECHAZA EXPLÍCITAMENTE
============================================================

Uniformes o vestuario para:

- hospitales, clínicas, consultorios;
- personal de salud, enfermeras, médicos;
- funcionarios administrativos u oficinas;
- juntas municipales o establecimientos educacionales;
- personal de aseo, cocina o atención al público;

aunque el texto diga "uniforme", "vestuario", "prenda",
"funcionario" o "institucional".

También NO RELEVANTE:

- servicios de vigilancia o contratación de guardias;
- cámaras, CCTV, alarmas, sensores;
- software, consultoría, capacitaciones, cursos;
- obras y servicios administrativos;
- cualquier producto completamente ajeno
  a seguridad, vigilancia o equipamiento táctico.

"Seguridad" sola NO basta si el bien no es táctico
ni de vigilancia (ej. uniforme de hospital "de seguridad").

Servicios disfrazados de producto también NO:

- "Curso táctico" => NO.
- "Capacitación táctica" => NO.
- "Entrenamiento táctico" => NO.

============================================================
CASOS SÍ RELEVANTES
============================================================

- "Botas tácticas para personal" => SÍ.
- "Chalecos antibalas para patrulleros" => SÍ.
- "Uniformes para guardias de seguridad" => SÍ.
- "Vestuario de vigilancia para inspectores" => SÍ.
- "Paneles anticorte" => SÍ.
- "Chaleco geólogo con logos" => SÍ.

============================================================
CASOS NO RELEVANTES
============================================================

- "Uniformes para funcionarios del hospital" => NO.
- "Ropa de trabajo para personal asistencial" => NO.
- "Uniformes médicos para clínica" => NO.
- "Servicio de vigilancia 24/7" => NO.

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

Determina el OBJETO REAL de compra y a quién va destinado.
Si es vestuario/uniforme sin vínculo con guardias,
vigilancia o táctico, responde relevante=false.

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
    organismo: str = "",
    region: str = "",
):

    prompt = _crear_prompt(
        nombre,
        descripcion,
        organismo,
        region,
    )

    return client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=800,
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
    organismo: str = "",
    region: str = "",
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
                organismo,
                region,
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
                organismo,
                region,
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