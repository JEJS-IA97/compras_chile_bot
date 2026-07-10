import os
import requests

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Remitente verificado en Brevo (Settings → Senders, Domains & Dedicated IPs)
REMITENTE_EMAIL = os.getenv("EMAIL_USER", "soporte@induwork.cl")
REMITENTE_NOMBRE = "Bot Mercado Público"


def generar_tabla_html(licitaciones):
    """Genera una estructura de tabla HTML limpia para el contenido del correo."""
    filas = ""
    for l in licitaciones:
        enlace = f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?id={l['id']}"
        if "CA-" in l["id"]:
            enlace = "https://buscador.mercadopublico.cl/compra-agil"

        filas += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><b>{l['id']}</b></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l['nombre']}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l['organismo']}</td>
            <td style="padding: 10px; border: 1px solid #ddd; color: #d9534f;"><b>{l['fecha_cierre']}</b></td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                <a href="{enlace}" style="background-color: #0275d8; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px;" target="_blank">Ver Oferta</a>
            </td>
        </tr>
        """

    html = f"""
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;">
        <thead>
            <tr style="background-color: #f4f4f4; text-align: left;">
                <th style="padding: 10px; border: 1px solid #ddd;">ID</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Nombre / Descripción</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Institución</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Cierra El</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Acción</th>
            </tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    """
    return html


def enviar_correo_oportunidades(destinatario, asunto, licitaciones, es_alerta_urgente=False):
    """
    Envía el reporte de oportunidades usando la API HTTPS de Brevo (puerto 443),
    en vez de SMTP directo (puertos 25/465/587), porque Render bloquea esos
    puertos salientes en el plan gratuito.
    """
    if not licitaciones:
        print(f"ℹ️ No hay licitaciones para enviar a {destinatario}.")
        return False

    if not BREVO_API_KEY:
        print("❌ Error: No se ha configurado BREVO_API_KEY en las variables de entorno.")
        return False

    color_banner = "#d9534f" if es_alerta_urgente else "#1b365d"
    titulo_banner = "🚨 ALERTA URGENTE: COMPRA ÁGIL" if es_alerta_urgente else "📋 REPORTE DIARIO DE OPORTUNIDADES"

    tabla_html = generar_tabla_html(licitaciones)

    cuerpo_html = f"""
    <html>
        <body>
            <div style="background-color: {color_banner}; color: white; padding: 20px; font-family: Arial, sans-serif; text-align: center;">
                <h2 style="margin: 0;">{titulo_banner}</h2>
                <p style="margin: 5px 0 0 0;">Filtros automatizados para tu rubro comercial</p>
            </div>
            <div style="padding: 20px; font-family: Arial, sans-serif;">
                <p>Hola equipo, el bot ha detectado las siguientes ofertas disponibles en Mercado Público:</p>
                {tabla_html}
                <br>
                <p style="font-size: 12px; color: #777;">Este es un correo automático generado por su bot de adquisición hospedado en Render.</p>
            </div>
        </body>
    </html>
    """

    payload = {
        "sender": {"name": REMITENTE_NOMBRE, "email": REMITENTE_EMAIL},
        "to": [{"email": destinatario}],
        "subject": asunto,
        "htmlContent": cuerpo_html
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)

        if response.status_code in (200, 201):
            print(f"✅ Correo enviado exitosamente a {destinatario} (Brevo messageId: {response.json().get('messageId')})")
            return True
        else:
            print(f"❌ Error al enviar el correo a {destinatario}: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error al enviar el correo a {destinatario}: {e}")
        return False