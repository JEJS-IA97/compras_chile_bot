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
        "primary_color": "#E8720C",      # Naranjo
        "secondary_color": "#1A1A2E",    # Azul oscuro
        "banner": "induwork.jpg",       
        "title": "INDUWORK — OPORTUNIDADES TÁCTICAS",
        "empresa": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "primary_color": "#56BF75",      # Verde Coimsa
        "secondary_color": "#56BF75",
        "banner": "coimsa.jpg",
        "title": "COIMSA — OPORTUNIDADES DE ASEO",
        "empresa": "Coimsa",
        "logo_clave": "COIMSASPA",       # Tu logo se llama COIMSASPA.png
    },
    "especial": {
        "primary_color": "#C9A227",      # Dorado
        "secondary_color": "#1A1A2E",    # Azul oscuro
        "banner": "inversiones.jpg",
        "title": "MVI — OPORTUNIDADES SOCIALES",
        "empresa": "MVI",
        "logo_clave": "MVI",
    },
}

# ============================================================
# RUTAS DE ASSETS
# ============================================================
# Ruta base del proyecto (subimos 2 niveles desde modules/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "src", "assets", "images")
BANNERS_DIR = os.path.join(ASSETS_DIR, "banners")


def _get_banner_path(categoria: str) -> str:
    """Busca el banner correspondiente a la categoría en src/assets/images/banners/"""
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
    """Busca el logo en src/assets/images/ por clave (ej: INDUWORK, COIMSASPA, MVI)"""
    if not os.path.isdir(ASSETS_DIR):
        return ""
    for fname in os.listdir(ASSETS_DIR):
        # Ignorar la carpeta banners
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
    Genera el HTML completo del correo con estilos inline,
    banner, colores, logos y tabla de licitaciones.
    """
    config = CATEGORY_CONFIG.get(categoria, CATEGORY_CONFIG["induwork"])
    primary_color = "#d9534f" if es_alerta_urgente else config["primary_color"]
    secondary_color = config["secondary_color"]
    titulo_banner = f"🚨 ALERTA URGENTE: {config['title']}" if es_alerta_urgente else f"📋 {config['title']}"

    # Buscar banner y logos en el sistema de archivos local
    banner_path = _get_banner_path(categoria)
    logo_empresa_path = _get_logo_path(config["logo_clave"])
    logo_mvi_path = _get_logo_path("MVI")

    # Convertir rutas locales a URLs para incrustar como CID
    # (Usaremos Content-ID para incrustar las imágenes en el correo)
    banner_cid = "banner" if banner_path else ""
    logo_empresa_cid = "logo_empresa" if logo_empresa_path else ""
    logo_mvi_cid = "logo_mvi" if logo_mvi_path else ""

    # Fecha actual
    fecha_actual = datetime.now(CL_TZ).strftime("%d/%m/%Y %H:%M")

    # Construir la tabla HTML
    tabla_html = _generar_tabla_html(licitaciones, primary_color) if licitaciones else ""

    # Texto de extra si no hay licitaciones pero hay cuerpo_extra_html (reportes)
    if not licitaciones and cuerpo_extra_html:
        tabla_html = cuerpo_extra_html

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{config['title']}</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5;">

        <!-- Contenedor principal -->
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 680px; background-color: #ffffff; margin: 0 auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
            <tr>
                <td style="padding: 0;">

                    <!-- BANNER -->
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="padding: 0;">
                                {f'<img src="cid:{banner_cid}" alt="{config["empresa"]}" style="width: 100%; height: auto; display: block; border-radius: 12px 12px 0 0;">' if banner_path else ''}
                            </td>
                        </tr>
                    </table>

                    <!-- HEADER con título y logos -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {secondary_color}; padding: 18px 20px;">
                        <tr>
                            <td style="text-align: center; padding: 0 20px;">
                                <div style="display: flex; align-items: center; justify-content: center; gap: 12px; flex-wrap: wrap;">
                                    {f'<img src="cid:{logo_empresa_cid}" alt="{config["empresa"]}" style="height: 40px; vertical-align: middle;">' if logo_empresa_path else ''}
                                    {f'<img src="cid:{logo_mvi_cid}" alt="MVI" style="height: 32px; vertical-align: middle;">' if logo_mvi_path else ''}
                                </div>
                                <h2 style="color: #ffffff; margin: 10px 0 0 0; font-size: 20px; font-weight: 700; letter-spacing: 0.3px;">
                                    {titulo_banner}
                                </h2>
                                <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0 0; font-size: 13px;">
                                    Filtros automatizados · {fecha_actual} (hora Chile)
                                </p>
                            </td>
                        </tr>
                    </table>

                    <!-- CUERPO -->
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

                    <!-- FOOTER con feedback -->
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: {primary_color}; padding: 16px 20px; border-radius: 0 0 12px 12px;">
                        <tr>
                            <td style="text-align: center;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="text-align: center; color: #ffffff; font-size: 13px; line-height: 1.5;">
                                            <p style="margin: 0 0 4px 0; font-weight: 600;">¿Estos filtros están funcionando bien?</p>
                                            <p style="margin: 0 0 10px 0; font-size: 12px; opacity: 0.9;">
                                                Reporta licitaciones que <b>no corresponden</b> o sugiere nuevas palabras clave.
                                            </p>
                                            <a href="https://forms.gle/TU-FORMULARIO-ID" 
                                               style="display: inline-block; background-color: #ffffff; color: {primary_color}; 
                                                      padding: 9px 28px; text-decoration: none; font-weight: 700; 
                                                      border-radius: 30px; font-size: 13px; margin-bottom: 8px;">
                                                ✍️ Enviar Feedback
                                            </a>
                                            <p style="margin: 6px 0 0 0; font-size: 11px; opacity: 0.75;">
                                                Tu opinión nos ayuda a mejorar los filtros para todos.
                                            </p>
                                            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.15); margin: 10px 0;">
                                            <p style="margin: 0; font-size: 10px; opacity: 0.7;">
                                                © {datetime.now(CL_TZ).year} · {config['empresa']} &amp; MVI · Bot automatizado
                                            </p>
                                        </td>
                                    </tr>
                                </table>
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
        📌 Oportunidades detectadas ({len(licitaciones)})
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
    config = CATEGORY_CONFIG.get(categoria, CATEGORY_CONFIG["induwork"])
    return {
        "banner": _get_banner_path(categoria),
        "logo_empresa": _get_logo_path(config["logo_clave"]),
        "logo_mvi": _get_logo_path("MVI"),
    }