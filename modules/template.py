# modules/mailer.py

import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from modules.template import generar_html_correo, obtener_imagenes_para_cid

SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.inversionesmvi.cl")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ============================================================
# DESTINATARIOS POR TIPO DE TAREA (MODO PRUEBA)
# ============================================================
DEST_PRUEBA_GERENCIA = "gerencia@induwork.cl"
DEST_PRUEBA_SOPORTE = "soporte@induwork.cl"

# Destinatarios originales (para cuando se quiera volver a producción)
DEST_INDUWORK_ORIGINAL = os.getenv("DEST_INDUWORK", "asaravia@induwork.cl")
DEST_COIMSA_ORIGINAL = os.getenv("DEST_COIMSA", "asaravia@induwork.cl")
DEST_ESPECIAL_ORIGINAL = os.getenv("DEST_ESPECIAL", "proyectos@induwork.cl")

# ============================================================
# CONFIGURACIÓN POR CATEGORÍA
# ============================================================
CONFIG_CATEGORIAS = {
    "induwork": {
        "destinatario": DEST_PRUEBA_GERENCIA,
        "remitente_nombre": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "destinatario": DEST_PRUEBA_GERENCIA,
        "remitente_nombre": "Coimsa",
        "logo_clave": "COIMSASPA",
    },
    "especial": {
        "destinatario": DEST_PRUEBA_GERENCIA,
        "remitente_nombre": "MVI",
        "logo_clave": "MVI",
    },
}


def enviar_correo_categoria(
    categoria: str,
    asunto: str,
    licitaciones: list,
    es_alerta_urgente: bool = False,
    cuerpo_extra_html: str = "",
    destinatario_override: str = None,
) -> bool:
    """
    Envía un correo con la plantilla dinámica correspondiente a la categoría.
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
    destinatario = destinatario_override or cfg["destinatario"]

    # Generar el HTML con la plantilla dinámica
    html_content = generar_html_correo(
        categoria=categoria,
        licitaciones=licitaciones,
        es_alerta_urgente=es_alerta_urgente,
        cuerpo_extra_html=cuerpo_extra_html,
    )

    # Construir el mensaje
    msg = MIMEMultipart("related")
    msg["Subject"] = asunto
    msg["From"] = f"{cfg['remitente_nombre']} - Bot Mercado Público <{EMAIL_USER}>"
    msg["To"] = destinatario

    # Adjuntar HTML
    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(html_content, "html", "utf-8"))

    # Obtener imágenes y adjuntarlas como CID
    imagenes = obtener_imagenes_para_cid(categoria)
    for cid, ruta in imagenes.items():
        if ruta and os.path.exists(ruta):
            _adjuntar_imagen_como_cid(msg, ruta, cid)

    # Enviar
    exito = _enviar_smtp(msg, destinatario)
    if exito:
        print(f"✅ Correo [{categoria}] enviado exitosamente a {destinatario}")
        if destinatario != cfg["destinatario"]:
            print(f"   📌 (Override: destinatario original era {cfg['destinatario']})")
    return exito


def _adjuntar_imagen_como_cid(msg, ruta, cid):
    """
    Adjunta una imagen con CID para insertar en el HTML.
    Especifica explícitamente el tipo MIME para evitar errores.
    """
    try:
        # Determinar el tipo MIME basado en la extensión
        ext = os.path.splitext(ruta)[1].lower()
        if ext == '.jpg' or ext == '.jpeg':
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.gif':
            mime_type = 'image/gif'
        else:
            # Intentar adivinar automáticamente
            mime_type = mimetypes.guess_type(ruta)[0] or 'image/jpeg'
        
        print(f"📎 Adjuntando {ruta} como {mime_type}")
        
        with open(ruta, "rb") as f:
            img_data = f.read()
        
        # Crear MIMEImage con el tipo específico
        img = MIMEImage(img_data, _subtype=mime_type.split('/')[-1])
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=os.path.basename(ruta))
        msg.attach(img)
        print(f"✅ Imagen adjuntada: {os.path.basename(ruta)} como {cid}")
        return True
    except Exception as e:
        print(f"⚠️ No se pudo adjuntar {ruta}: {e}")
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


# ============================================================
# FUNCIONES DE AYUDA PARA CAMBIAR MODO (PRUEBA / PRODUCCIÓN)
# ============================================================

def set_modo_prueba():
    """Cambia todos los destinatarios a gerencia@induwork.cl"""
    for categoria in CONFIG_CATEGORIAS:
        CONFIG_CATEGORIAS[categoria]["destinatario"] = DEST_PRUEBA_GERENCIA
    print("🔧 Modo PRUEBA activado: todos los correos van a gerencia@induwork.cl")


def set_modo_produccion():
    """Restaura los destinatarios originales"""
    CONFIG_CATEGORIAS["induwork"]["destinatario"] = DEST_INDUWORK_ORIGINAL
    CONFIG_CATEGORIAS["coimsa"]["destinatario"] = DEST_COIMSA_ORIGINAL
    CONFIG_CATEGORIAS["especial"]["destinatario"] = DEST_ESPECIAL_ORIGINAL
    print("🔧 Modo PRODUCCIÓN activado: correos a destinatarios originales")