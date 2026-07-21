# modules/template.py

import os
from datetime import datetime
from zoneinfo import ZoneInfo

CL_TZ = ZoneInfo("America/Santiago")

# ============================================================
# CONFIGURACIÓN DE CATEGORÍAS (SOLO COLORES Y TEXTOS)
# ============================================================
CATEGORY_CONFIG = {
    "induwork": {
        "primary_color": "#E8720C",      # Naranjo
        "banner": "induwrok.jpg",
        "titulo": "INDUWORK — OPORTUNIDADES TÁCTICAS",
        "empresa": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "primary_color": "#56BF75",      # Verde Coimsa
        "banner": "coimsa.jpg",
        "titulo": "COIMSA — OPORTUNIDADES DE ASEO",
        "empresa": "Coimsa",
        "logo_clave": "COIMSASPA",
    },
    "especial": {
        "primary_color": "#C9A227",      # Dorado
        "banner": "inversiones.jpg",
        "titulo": "MVI — OPORTUNIDADES SOCIALES",
        "empresa": "MVI",
        "logo_clave": "MVI",
    },
}

# ============================================================
# RUTAS DE ASSETS
# ============================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "src", "assets", "images")
BANNERS_DIR = os.path.join(ASSETS_DIR, "banners")


def _get_banner_path(categoria: str) -> str:
    """Busca el banner correspondiente en src/assets/images/banners/"""
    config = CATEGORY_CONFIG.get(categoria)
    if not config:
        return ""
    banner_name = config["banner"]
    banner_path = os.path.join(BANNERS_DIR, banner_name)
    if os.path.exists(banner_path):
        return banner_path
    # Fallback: buscar cualquier archivo que contenga el nombre
    for fname in os.listdir(BANNERS_DIR):
        if banner_name.lower() in fname.lower().replace(" ", ""):
            return os.path.join(BANNERS_DIR, fname)
    return ""


def _get_logo_path(clave: str) -> str:
    """Busca el logo en src/assets/images/ por clave"""
    if not os.path.isdir(ASSETS_DIR):
        return ""
    for fname in os.listdir(ASSETS_DIR):
        if os.path.isdir(os.path.join(ASSETS_DIR, fname)):
            continue
        if clave.lower() in fname.lower().replace(" ", ""):
            return os.path.join(ASSETS_DIR, fname)
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
    
    # Color: si es alerta urgente, rojo; si no, el color de la categoría
    primary_color = "#d9534f" if es_alerta_urgente else config["primary_color"]
    
    # Título: si es alerta urgente, agregar 🚨
    titulo = f"🚨 ALERTA URGENTE: {config['titulo']}" if es_alerta_urgente else config['titulo']
    
    # Tipo de oportunidad (para mostrar en el título de la tabla)
    tipo_oportunidad = "COMPRAS ÁGILES URGENTES" if es_alerta_urgente else "LICITACIONES"

    # Buscar banner
    banner_path = _get_banner_path(categoria)
    banner_cid = "banner" if banner_path else ""

    # Contador de oportunidades
    total_oportunidades = len(licitaciones)

    # Construir la tabla HTML
    tabla_html = _generar_tabla_html(licitaciones, primary_color) if licitaciones else ""

    # Si no hay licitaciones pero hay cuerpo_extra_html (reportes)
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
                    <!-- BANNER (imagen completa, sin texto adicional) -->
                    <!-- ============================================ -->
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="padding: 0;">
                                <img src="cid:{banner_cid}" alt="{config['empresa']}" style="width: 100%; height: auto; display: block; border-radius: 12px 12px 0 0;">
                            </td>
                        </tr>
                    </table>

                    <!-- ============================================ -->
                    <!-- TÍTULO (solo el título, sin logos ni fechas) -->
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