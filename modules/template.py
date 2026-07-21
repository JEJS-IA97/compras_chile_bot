# modules/template.py

import os
from datetime import datetime
from zoneinfo import ZoneInfo

CL_TZ = ZoneInfo("America/Santiago")

# ============================================================
# CONFIGURACIÓN DE CATEGORÍAS
# ============================================================
CATEGORY_CONFIG = {
    "induwork": {
        "primary_color": "#E8720C",
        "banner": "induwork.jpg",      # OJO: sin 'k' en "work"
        "titulo": "INDUWORK — OPORTUNIDADES TÁCTICAS",
        "empresa": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "primary_color": "#56BF75",
        "banner": "coimsa.jpg",
        "titulo": "COIMSA — OPORTUNIDADES DE ASEO",
        "empresa": "Coimsa",
        "logo_clave": "COIMSASPA",
    },
    "especial": {
        "primary_color": "#C9A227",
        "banner": "inversiones.jpg",
        "titulo": "MVI — OPORTUNIDADES SOCIALES",
        "empresa": "MVI",
        "logo_clave": "MVI",
    },
}

# ============================================================
# RUTAS DE ASSETS (con DEBUG)
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "src", "assets", "images")
BANNERS_DIR = os.path.join(ASSETS_DIR, "banners")

# DEBUG: imprimir rutas al iniciar
print(f"🔍 BASE_DIR: {BASE_DIR}")
print(f"🔍 ASSETS_DIR: {ASSETS_DIR}")
print(f"🔍 BANNERS_DIR: {BANNERS_DIR}")
print(f"🔍 ¿Existe BANNERS_DIR? {os.path.exists(BANNERS_DIR)}")
if os.path.exists(BANNERS_DIR):
    print(f"🔍 Archivos en BANNERS_DIR: {os.listdir(BANNERS_DIR)}")


def _get_banner_path(categoria: str) -> str:
    """
    Busca el banner correspondiente en src/assets/images/banners/
    Con DEBUG para ver qué está pasando.
    """
    config = CATEGORY_CONFIG.get(categoria)
    if not config:
        print(f"⚠️ Categoría no encontrada: {categoria}")
        return ""
    
    banner_name = config["banner"]
    banner_path = os.path.join(BANNERS_DIR, banner_name)
    
    print(f"🔍 Buscando banner para {categoria}: {banner_path}")
    print(f"🔍 ¿Existe? {os.path.exists(banner_path)}")
    
    if os.path.exists(banner_path):
        print(f"✅ Banner encontrado: {banner_path}")
        return banner_path
    
    # Fallback: buscar cualquier archivo que contenga el nombre
    if os.path.exists(BANNERS_DIR):
        for fname in os.listdir(BANNERS_DIR):
            print(f"🔍 Comparando: '{banner_name.lower()}' vs '{fname.lower().replace(' ', '')}'")
            if banner_name.lower() in fname.lower().replace(" ", ""):
                found_path = os.path.join(BANNERS_DIR, fname)
                print(f"✅ Banner encontrado por fallback: {found_path}")
                return found_path
    
    print(f"❌ Banner NO encontrado para {categoria}")
    return ""


def _get_logo_path(clave: str) -> str:
    """Busca el logo en src/assets/images/ por clave (con DEBUG)"""
    if not os.path.isdir(ASSETS_DIR):
        print(f"⚠️ ASSETS_DIR no existe: {ASSETS_DIR}")
        return ""
    
    print(f"🔍 Buscando logo para clave: {clave} en {ASSETS_DIR}")
    for fname in os.listdir(ASSETS_DIR):
        # Ignorar la carpeta banners
        if os.path.isdir(os.path.join(ASSETS_DIR, fname)):
            continue
        print(f"🔍 Comparando: '{clave.lower()}' vs '{fname.lower().replace(' ', '')}'")
        if clave.lower() in fname.lower().replace(" ", ""):
            found_path = os.path.join(ASSETS_DIR, fname)
            print(f"✅ Logo encontrado: {found_path}")
            return found_path
    
    print(f"❌ Logo NO encontrado para {clave}")
    return ""


def generar_html_correo(
    categoria: str,
    licitaciones: list,
    es_alerta_urgente: bool = False,
    cuerpo_extra_html: str = "",
) -> str:
    """
    Genera el HTML completo del correo con:
    - Banner completo (imagen)
    - Título
    - Tabla de licitaciones
    - Footer con feedback
    """
    config = CATEGORY_CONFIG.get(categoria, CATEGORY_CONFIG["induwork"])
    
    primary_color = "#d9534f" if es_alerta_urgente else config["primary_color"]
    titulo = f"🚨 ALERTA URGENTE: {config['titulo']}" if es_alerta_urgente else config['titulo']

    # Buscar banner
    banner_path = _get_banner_path(categoria)
    banner_cid = "banner" if banner_path else ""
    
    # Si no hay banner, usar un color de fondo como fallback
    banner_html = ""
    if banner_path:
        banner_html = f'<img src="cid:{banner_cid}" alt="{config["empresa"]}" style="width: 100%; height: auto; display: block; border-radius: 12px 12px 0 0;">'
    else:
        # Fallback: mostrar un div con el color de la empresa
        banner_html = f'<div style="width: 100%; height: 120px; background-color: {primary_color}; border-radius: 12px 12px 0 0; display: flex; align-items: center; justify-content: center;">'
        banner_html += f'<span style="color: white; font-size: 24px; font-weight: bold;">{config["empresa"]}</span>'
        banner_html += '</div>'
        print(f"⚠️ Usando fallback de color para {categoria} porque no se encontró banner")

    # Construir la tabla HTML
    tabla_html = _generar_tabla_html(licitaciones, primary_color) if licitaciones else ""

    if not licitaciones and cuerpo_extra_html:
        tabla_html = cuerpo_extra_html

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{config['titulo']}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5;">

        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 700px; background-color: #ffffff; margin: 20px auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
            <tr>
                <td style="padding: 0;">

                    <!-- ============================================ -->
                    <!-- BANNER (imagen completa o fallback)          -->
                    <!-- ============================================ -->
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="padding: 0;">
                                {banner_html}
                            </td>
                        </tr>
                    </table>

                    <!-- ============================================ -->
                    <!-- TÍTULO (solo el título)                     -->
                    <!-- ============================================ -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {primary_color}; padding: 14px 20px;">
                        <tr>
                            <td style="text-align: center;">
                                <h2 style="color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">
                                    {titulo}
                                </h2>
                            </td>
                        </tr>
                    </table>

                    <!-- ============================================ -->
                    <!-- CUERPO (tabla de licitaciones)               -->
                    <!-- ============================================ -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="padding: 20px 24px 10px 24px;">
                        <tr>
                            <td style="color: #333333; font-size: 14px; line-height: 1.6;">
                                {tabla_html}
                                <br>
                                <p style="font-size: 12px; color: #999999; text-align: center; border-top: 1px solid #eee; padding-top: 14px; margin-top: 10px;">
                                    🤖 Correo automático generado por el Bot de Adquisiciones MVI
                                </p>
                            </td>
                        </tr>
                    </table>

                    <!-- ============================================ -->
                    <!-- FOOTER (feedback)                            -->
                    <!-- ============================================ -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {primary_color}; padding: 16px 20px; border-radius: 0 0 12px 12px;">
                        <tr>
                            <td style="text-align: center;">
                                <p style="margin: 0 0 4px 0; color: #ffffff; font-weight: 600; font-size: 13px;">
                                    ¿Este filtro está funcionando bien?
                                </p>
                                <p style="margin: 0 0 10px 0; color: rgba(255,255,255,0.85); font-size: 12px;">
                                    Reporta licitaciones que <b>no corresponden</b> o sugiere nuevas palabras clave.
                                </p>
                                <a href="https://forms.gle/TU-FORMULARIO-ID" 
                                   style="display: inline-block; background-color: #ffffff; color: {primary_color}; 
                                          padding: 9px 28px; text-decoration: none; font-weight: 700; 
                                          border-radius: 30px; font-size: 13px; margin-bottom: 6px;">
                                    ✍️ Enviar Feedback
                                </a>
                                <p style="margin: 6px 0 0 0; color: rgba(255,255,255,0.7); font-size: 10px;">
                                    © {datetime.now(CL_TZ).year} · {config['empresa']} · Bot automatizado
                                </p>
                            </td>
                        </tr>
                    </table>

                </td>
            </tr>
        </table>

    </body>
    </html>
    """
    return html


def _generar_tabla_html(licitaciones: list, primary_color: str = "#E8720C") -> str:
    """Genera la tabla HTML con todas las licitaciones."""
    if not licitaciones:
        return ""

    filas = ""
    for l in licitaciones:
        enlace = l.get("link", "https://www.mercadopublico.cl")
        filas += f"""
        <tr>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 12px; text-align: center;">
                <b>{l.get('id', '')}</b>
            </td>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 12px;">
                {l.get('nombre', '')[:60]}{'...' if len(l.get('nombre', '')) > 60 else ''}
            </td>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px; color: #555;">
                {l.get('organismo', '')}
            </td>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px; text-align: center;">
                {l.get('region', '')}
            </td>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 12px; text-align: center; color: #d9534f; font-weight: 600;">
                {l.get('fecha_cierre', '')}
            </td>
            <td style="padding: 8px 6px; border: 1px solid #e0e0e0; text-align: center;">
                <a href="{enlace}" style="background-color: {primary_color}; color: white; padding: 4px 12px; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block;" target="_blank">
                    Ver
                </a>
            </td>
        </tr>
        """

    return f"""
    <p style="font-weight: 600; color: {primary_color}; font-size: 15px; margin: 0 0 10px 0;">
        📋 Oportunidades detectadas ({len(licitaciones)})
    </p>
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 12px; margin-top: 4px;">
        <thead>
            <tr style="background-color: #f4f4f4; text-align: left;">
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px;">ID</th>
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px;">Nombre</th>
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px;">Institución</th>
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px;">Región</th>
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px;">Cierra</th>
                <th style="padding: 8px 6px; border: 1px solid #e0e0e0; font-size: 11px; text-align: center;">Link</th>
            </tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    """


def obtener_imagenes_para_cid(categoria: str) -> dict:
    """
    Devuelve un diccionario con las rutas de las imágenes que deben
    incrustarse como CID en el correo.
    """
    return {
        "banner": _get_banner_path(categoria),
    }