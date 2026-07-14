import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.inversionesmvi.cl")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
EMAIL_USER = os.getenv("EMAIL_USER")  # marketing@inversionesmvi.cl (autentica TODOS los envíos)
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Destinatarios por categoría (se pueden sobreescribir con variables de entorno del mismo nombre)
DEST_INDUWORK = os.getenv("DEST_INDUWORK", "asaravia@induwork.cl")
DEST_COIMSA = os.getenv("DEST_COIMSA", "asaravia@induwork.cl")
DEST_ESPECIAL = os.getenv("DEST_ESPECIAL", "proyectos@induwork.cl")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images")

CONFIG_CATEGORIAS = {
    "induwork": {
        "color": "#E8720C",  # naranjo
        "titulo": "INDUWORK — OPORTUNIDADES TÁCTICAS",
        "logo_clave": "induwork",
        "destinatario": DEST_INDUWORK,
        "remitente_nombre": "Induwork",
    },
    "coimsa": {
        "color": "#1565C0",  # azul
        "titulo": "COIMSA — OPORTUNIDADES DE ASEO",
        "logo_clave": "coimsa",
        "destinatario": DEST_COIMSA,
        "remitente_nombre": "Coimsa",
    },
    "especial": {
        "color": "#C9A227",  # dorado
        "titulo": "MVI — OPORTUNIDADES SOCIALES",
        "logo_clave": "mvi",
        "destinatario": DEST_ESPECIAL,
        "remitente_nombre": "MVI",
    },
}


def _buscar_logo(clave):
    """
    Busca en assets/images un archivo cuyo nombre contenga 'clave', sin importar
    mayúsculas/espacios (para tolerar cosas como 'COIMSASPA .png').
    Devuelve la ruta o None si no existe (ej: todavía no han subido el logo de MVI).
    """
    if not os.path.isdir(ASSETS_DIR):
        return None
    for fname in os.listdir(ASSETS_DIR):
        if clave.lower() in fname.lower().replace(" ", ""):
            return os.path.join(ASSETS_DIR, fname)
    return None


def generar_tabla_html(licitaciones):
    """Tabla HTML con toda la info disponible: ID, nombre/descripción, tipo, institución, región, cierre y link real."""
    filas = ""
    for l in licitaciones:
        enlace = l.get("link") or "https://www.mercadopublico.cl"
        filas += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd;"><b>{l.get('id','')}</b></td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l.get('nombre','')}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l.get('tipo','')}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l.get('organismo','Organismo Desconocido')}</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{l.get('region','')}</td>
            <td style="padding: 10px; border: 1px solid #ddd; color: #d9534f;"><b>{l.get('fecha_cierre','')}</b></td>
            <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">
                <a href="{enlace}" style="background-color: #0275d8; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px;" target="_blank">Ver Oferta</a>
            </td>
        </tr>
        """

    return f"""
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 13px;">
        <thead>
            <tr style="background-color: #f4f4f4; text-align: left;">
                <th style="padding: 10px; border: 1px solid #ddd;">ID</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Nombre</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Tipo</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Institución</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Región</th>
                <th style="padding: 10px; border: 1px solid #ddd;">Cierra El</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Acción</th>
            </tr>
        </thead>
        <tbody>{filas}</tbody>
    </table>
    """


def _adjuntar_logo(msg_related, clave, cid):
    ruta = _buscar_logo(clave)
    if not ruta:
        print(f"⚠️ No se encontró logo para '{clave}' en {ASSETS_DIR} (se omite en el correo).")
        return False
    try:
        with open(ruta, "rb") as f:
            img = MIMEImage(f.read())
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=os.path.basename(ruta))
        msg_related.attach(img)
        return True
    except Exception as e:
        print(f"⚠️ No se pudo adjuntar el logo '{clave}': {e}")
        return False


def _enviar_smtp(msg, destinatario):
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
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo a {destinatario}: {e}")
        return False


def enviar_correo_categoria(categoria, asunto, licitaciones, es_alerta_urgente=False, cuerpo_extra_html=""):
    """
    Envía un correo con el banner/logo/destinatario que corresponde a la categoría
    ('induwork', 'coimsa' o 'especial'). La cuenta que autentica siempre es la de
    MVI (EMAIL_USER); lo que cambia por categoría es el nombre del remitente visible,
    el color del banner, el logo y el destinatario.
    """
    if categoria not in CONFIG_CATEGORIAS:
        print(f"❌ Categoría desconocida: {categoria}")
        return False

    if not licitaciones and not cuerpo_extra_html:
        print(f"ℹ️ No hay contenido para enviar en categoría {categoria}.")
        return False

    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Error: EMAIL_USER o EMAIL_PASS no están configurados.")
        return False

    cfg = CONFIG_CATEGORIAS[categoria]
    destinatario = cfg["destinatario"]

    msg = MIMEMultipart("related")
    msg["Subject"] = asunto
    msg["From"] = f"{cfg['remitente_nombre']} - Bot Mercado Público <{EMAIL_USER}>"
    msg["To"] = destinatario

    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    color = "#d9534f" if es_alerta_urgente else cfg["color"]
    titulo_banner = f"🚨 ALERTA URGENTE: {cfg['titulo']}" if es_alerta_urgente else f"📋 {cfg['titulo']}"

    logo_mvi_ok = _buscar_logo("mvi") is not None
    logo_empresa_ok = cfg["logo_clave"] != "mvi" and _buscar_logo(cfg["logo_clave"]) is not None

    logos_html = ""
    if logo_mvi_ok:
        logos_html += '<img src="cid:logo_mvi" alt="MVI" style="height:40px; margin-right:15px; vertical-align:middle;">'
    if logo_empresa_ok:
        logos_html += f'<img src="cid:logo_empresa" alt="{cfg["remitente_nombre"]}" style="height:40px; vertical-align:middle;">'

    tabla_html = generar_tabla_html(licitaciones) if licitaciones else ""

    cuerpo_html = f"""
    <html>
        <body>
            <div style="background-color: {color}; color: white; padding: 20px; font-family: Arial, sans-serif; text-align: center;">
                <div style="margin-bottom: 12px;">{logos_html}</div>
                <h2 style="margin: 0;">{titulo_banner}</h2>
                <p style="margin: 5px 0 0 0;">Filtros automatizados para tu rubro comercial</p>
            </div>
            <div style="padding: 20px; font-family: Arial, sans-serif;">
                {cuerpo_extra_html}
                {"<p>Hola equipo, el bot ha detectado las siguientes ofertas disponibles en Mercado Público:</p>" + tabla_html if licitaciones else ""}
                <br>
                <p style="font-size: 12px; color: #777;">Correo automático — Bot de Adquisiciones MVI (GitHub Actions).</p>
            </div>
        </body>
    </html>
    """

    alt.attach(MIMEText(cuerpo_html, "html"))

    if logo_mvi_ok:
        _adjuntar_logo(msg, "mvi", "logo_mvi")
    if logo_empresa_ok:
        _adjuntar_logo(msg, cfg["logo_clave"], "logo_empresa")

    exito = _enviar_smtp(msg, destinatario)
    if exito:
        print(f"✅ Correo [{categoria}] enviado exitosamente a {destinatario}")
    return exito