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
        "banner": "induwork.jpg",
        "titulo_general": "LICITACIONES",
        "empresa": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "primary_color": "#56BF75",      # Verde
        "banner": "coimsa.jpg",
        "titulo_general": "LICITACIONES",
        "empresa": "Coimsa",
        "logo_clave": "COIMSASPA",
    },
    "especial": {
        "primary_color": "#C9A227",      # Dorado
        "banner": "inversiones.jpg",
        "titulo_general": "LICITACIONES",
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
    
    if os.path.exists(BANNERS_DIR):
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
    Genera el HTML completo del correo con tablas compatibles con Outlook.
    """
    config = CATEGORY_CONFIG.get(categoria, CATEGORY_CONFIG["induwork"])
    
    primary_color = "#d9534f" if es_alerta_urgente else config["primary_color"]
    
    if es_alerta_urgente:
        titulo = "🚨 ALERTA URGENTE: COMPRAS ÁGILES"
    else:
        titulo = config["titulo_general"]

    # Buscar banner
    banner_path = _get_banner_path(categoria)
    banner_cid = "banner" if banner_path else ""
    
    banner_html = ""
    if banner_path:
        banner_html = f'<img src="cid:{banner_cid}" alt="{config["empresa"]}" style="width: 100%; height: auto; display: block;">'
    else:
        banner_html = f'<div style="width: 100%; height: 80px; background-color: {primary_color};"></div>'

    # Construir la tabla HTML (pasamos el color primario)
    tabla_html = _generar_tabla_html(licitaciones, primary_color) if licitaciones else ""

    if not licitaciones and cuerpo_extra_html:
        tabla_html = cuerpo_extra_html

    contador_html = ""
    if licitaciones:
        contador_html = f"""
        <tr>
            <td style="text-align: center; padding: 10px 0 5px 0; font-size: 14px; color: #666666;">
                <b style="color: {primary_color};">Total de oportunidades: {len(licitaciones)}</b>
            </td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config['empresa']} - {titulo}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5;">

    <!-- CONTENEDOR PRINCIPAL -->
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 700px; background-color: #ffffff; margin: 20px auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
        <tr>
            <td style="padding: 0;">

                <!-- ========================================== -->
                <!-- BANNER                                    -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding: 0;">
                            {banner_html}
                        </td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- FILA ESPACIO SUPERIOR (para padding)      -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="height: 20px; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- TÍTULO (sin fondo, solo texto)            -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="text-align: center; padding: 0 20px 0 20px;">
                            <h2 style="color: #1A1A2E; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px;">
                                {titulo}
                            </h2>
                        </td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- FILA ESPACIO (entre título y tabla)       -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="height: 15px; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- TABLA DE LICITACIONES                     -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="padding: 0 20px 0 20px;">
                    <tr>
                        <td style="padding: 0;">
                            {tabla_html}
                        </td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- CONTADOR (debajo de la tabla)             -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    {contador_html}
                </table>

                <!-- ========================================== -->
                <!-- FILA ESPACIO (entre contador y footer)    -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="height: 15px; font-size: 0; line-height: 0;">&nbsp;</td>
                    </tr>
                </table>

                <!-- ========================================== -->
                <!-- FOOTER (con padding explícito)            -->
                <!-- ========================================== -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: {primary_color}; border-radius: 0 0 12px 12px;">
                    <tr>
                        <td style="padding: 16px 20px 16px 20px; text-align: center;">
                            <p style="margin: 0 0 4px 0; color: #ffffff; font-weight: 600; font-size: 13px;">
                                ¿Este filtro está funcionando bien?
                            </p>
                            <p style="margin: 0 0 10px 0; color: rgba(255,255,255,0.85); font-size: 12px;">
                                Reporta licitaciones que <b>no corresponden</b> o sugiere nuevas palabras clave.
                            </p>
                            <a href="https://forms.gle/9WScZHxP9xaJCMYq9" 
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
    """
    Genera la tabla HTML con todas las licitaciones.
    La cabecera y los botones usan el color primario.
    """
    if not licitaciones:
        return ""

    filas = ""
    for l in licitaciones:
        enlace = l.get("link", "https://www.mercadopublico.cl")
        filas += f"""
        <tr>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; font-size: 12px; text-align: center;">
                <b>{l.get('id', '')}</b>
            </td>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; font-size: 12px;">
                {l.get('nombre', '')[:50]}{'...' if len(l.get('nombre', '')) > 50 else ''}
            </td>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; font-size: 11px; color: #555;">
                {l.get('organismo', '')}
            </td>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; font-size: 11px; text-align: center;">
                {l.get('region', '')}
            </td>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; font-size: 12px; text-align: center; color: #d9534f; font-weight: 600;">
                {l.get('fecha_cierre', '')}
            </td>
            <td style="padding: 10px 8px; border: 1px solid #e0e0e0; text-align: center;">
                <a href="{enlace}" style="background-color: {primary_color}; color: white; padding: 5px 14px; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block;" target="_blank">
                    Ver
                </a>
            </td>
        </tr>
        """

    return f"""
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px;">
        <thead>
            <tr style="background-color: {primary_color};">
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: center; color: #ffffff;">ID</th>
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: left; color: #ffffff;">Nombre</th>
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: left; color: #ffffff;">Institución</th>
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: center; color: #ffffff;">Región</th>
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: center; color: #ffffff;">Cierra</th>
                <th style="padding: 10px 8px; border: 1px solid {primary_color}; font-size: 11px; font-weight: 600; text-align: center; color: #ffffff;">Link</th>
            </tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    """


def obtener_imagenes_para_cid(categoria: str) -> dict:
    """Devuelve un diccionario con las rutas de las imágenes que deben incrustarse como CID."""
    return {
        "banner": _get_banner_path(categoria),
    }