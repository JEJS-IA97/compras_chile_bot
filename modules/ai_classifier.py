# modules/ia_clasificador.py

import google.generativeai as genai
from config.settings import GEMINI_API_KEY

# Configurar Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        print("✅ Gemini configurado correctamente.")
    except Exception as e:
        print(f"❌ Error al configurar Gemini: {e}")
        model = None
else:
    print("⚠️ GEMINI_API_KEY no configurada. La IA no estará disponible.")
    model = None


def clasificar_con_gemini(nombre: str, descripcion: str) -> dict:
    """
    Usa Gemini para clasificar una licitación en coimsa, induwork o especial.
    Retorna un diccionario con las mismas claves que evaluar_licitacion.
    """
    if not model:
        return {"coimsa": False, "induwork": False, "especial": False}

    prompt = f"""
    Eres un experto en clasificación de licitaciones públicas de Chile.
    Analiza la siguiente licitación y decide si es relevante para alguna de estas categorías:

    - COIMSA: servicios de aseo, limpieza, sanitización, desinfección, fumigación (solo si es en la Región Metropolitana).
    - INDUWORK: equipamiento de protección personal (chalecos, cascos, anticorte, antibalas, ropa de seguridad, calzado de seguridad), uniformes tácticos, equipos de seguridad personal, y también sistemas de videovigilancia, cámaras de seguridad, alarmas, circuitos cerrados de televisión (CCTV), todo lo relacionado con seguridad personal y vigilancia.
    - ESPECIAL: proyectos sociales, programas sociales, desarrollo informático.

    Si no es relevante para ninguna, responde "ninguna".

    Título: {nombre}
    Descripción: {descripcion[:1000]}

    Responde ÚNICAMENTE con una de estas palabras: coimsa, induwork, especial, ninguna.
    """

    try:
        response = model.generate_content(prompt)
        respuesta = response.text.strip().lower()

        if "coimsa" in respuesta:
            return {"coimsa": True, "induwork": False, "especial": False}
        elif "induwork" in respuesta:
            return {"coimsa": False, "induwork": True, "especial": False}
        elif "especial" in respuesta:
            return {"coimsa": False, "induwork": False, "especial": True}
        else:
            return {"coimsa": False, "induwork": False, "especial": False}
    except Exception as e:
        print(f"⚠️ Error al consultar Gemini: {e}")
        return {"coimsa": False, "induwork": False, "especial": False}