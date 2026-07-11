import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


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
    Envía el reporte de oportunidades vía SMTP (Gmail u otro proveedor).
    Pensado para correr desde GitHub Actions, donde no hay bloqueo de puertos SMTP
    (a diferencia del plan gratis de Render).
    """
    if not licitaciones:
        print(f"ℹ️ No hay licitaciones para enviar a {destinatario}.")
        return False

    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Error: EMAIL_USER o EMAIL_PASS no están configurados.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"Bot Mercado Público <{EMAIL_USER}>"
    msg["To"] = destinatario

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
                <p style="font-size: 12px; color: #777;">Este es un correo automático generado por su bot de adquisición (GitHub Actions).</p>
            </div>
        </body>
    </html>
    """

    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, destinatario, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, destinatario, msg.as_string())

        print(f"✅ Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar el correo a {destinatario}: {e}")
        return False