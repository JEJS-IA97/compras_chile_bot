# modules/ai_classifier.py

import json

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY

MODEL_NAME = "gemini-3.5-flash-lite"

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"✅ Gemini configurado correctamente ({MODEL_NAME}).")
    except Exception as e:
        print(f"❌ Error al configurar Gemini: {e}")
else:
    print("⚠️ GEMINI_API_KEY no configurada. La validación IA de Induwork estará deshabilitada.")


def _respuesta_vacia() -> dict:
    return {
        "coimsa": False,
        "induwork": False,
        "especial": False,
        "motivo": "",
        "terminos_detectados": [],
    }


def clasificar_con_gemini(nombre: str, descripcion: str) -> dict:
    """
    Valida estrictamente si una licitación candidata por keywords
    realmente corresponde a productos/equipamiento de Induwork.

    Fail-closed: si Gemini no está disponible o falla, Induwork no se aprueba.
    """
    if client is None:
        return _respuesta_vacia()

    prompt = f"""
Eres un clasificador estricto de licitaciones públicas de Chile para INDUWORK.

INDUWORK busca oportunidades de compra de equipamiento físico relacionado con:
- protección anticorte;
- protección antipunzón o antipunzonamiento;
- equipamiento táctico;
- protección antibala;
- equipamiento balístico;
- chalecos, cascos, prendas o equipos de protección personal
  cuando formen parte de ese tipo de equipamiento.

La licitación llegó a esta etapa porque el título o descripción contiene
uno de los términos de búsqueda manual de Induwork. Esa coincidencia NO
significa que sea relevante.

Aprueba como RELEVANTE solamente si la licitación solicita comprar, adquirir,
suministrar, proveer o entregar productos/equipamiento de ese tipo.

Rechaza como NO RELEVANTE cuando:
- solo menciona seguridad, protección, vigilancia u otros conceptos genéricos;
- solicita servicios de vigilancia, guardias o seguridad;
- solicita cámaras, CCTV, alarmas, sensores o sistemas de control de acceso;
- solicita instalación, reparación, mantenimiento o monitoreo de sistemas;
- solicita capacitación, cursos, entrenamiento, consultoría o asesoría;
- usa "táctico", "táctica" o similares para describir operaciones, estrategias,
  procedimientos o servicios en lugar de equipamiento físico;
- el término aparece de manera incidental y el objeto real de la compra es otro.

TÍTULO:
{nombre}

DESCRIPCIÓN:
{descripcion[:2500]}

Responde ÚNICAMENTE un JSON válido:
{{
  "relevante": true,
  "motivo": "explicación breve",
  "terminos_detectados": ["termino"]
}}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=250,
                temperature=0,
            ),
        )

        texto = (response.text or "").strip()
        if not texto:
            return _respuesta_vacia()

        datos = json.loads(texto)
        terminos = datos.get("terminos_detectados", [])

        if not isinstance(terminos, list):
            terminos = []

        return {
            "coimsa": False,
            "induwork": bool(datos.get("relevante", False)),
            "especial": False,
            "motivo": str(datos.get("motivo", "") or "").strip(),
            "terminos_detectados": [str(t).strip() for t in terminos[:10]],
        }

    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"⚠️ Respuesta inválida de Gemini: {e}")
        return _respuesta_vacia()
    except Exception as e:
        print(f"⚠️ Error al consultar Gemini para Induwork: {e}")
        return _respuesta_vacia()
