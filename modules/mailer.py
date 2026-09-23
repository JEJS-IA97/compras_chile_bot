# modules/mailer.py

import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from modules.template import (
    generar_html_correo,
    obtener_imagenes_para_cid,
)


SMTP_SERVER = os.getenv(
    "SMTP_SERVER",
    "mail.inversionesmvi.cl",
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        465,
    )
)

EMAIL_USER = os.getenv(
    "EMAIL_USER"
)

EMAIL_PASS = os.getenv(
    "EMAIL_PASS"
)


# ============================================================
# DESTINATARIOS
# ============================================================

DEST_INDUWORK = os.getenv(
    "DEST_INDUWORK",
)

DEST_COIMSA = os.getenv(
    "DEST_COIMSA",
)

DEST_ESPECIAL = os.getenv(
    "DEST_ESPECIAL",
)

# Destinatario utilizado únicamente para el reenvío manual
# completo de la base de datos durante las pruebas.
DEST_PRUEBA_SOPORTE = "soporte@induwork.cl"


# ============================================================
# VALIDACIÓN DE DESTINATARIOS
# ============================================================

def _mostrar_configuracion():

    print(
        "📧 Configuración de destinatarios:"
    )

    print(
        "   INDUWORK: "
        f"{DEST_INDUWORK or 'NO CONFIGURADO'}"
    )

    print(
        "   COIMSA: "
        f"{DEST_COIMSA or 'NO CONFIGURADO'}"
    )

    print(
        "   ESPECIAL: "
        f"{DEST_ESPECIAL or 'NO CONFIGURADO'}"
    )


# ============================================================
# CONFIGURACIÓN POR CATEGORÍA
# ============================================================

CONFIG_CATEGORIAS = {
    "induwork": {
        "destinatario": DEST_INDUWORK,
        "remitente_nombre": "Induwork",
        "logo_clave": "INDUWORK",
    },
    "coimsa": {
        "destinatario": DEST_COIMSA,
        "remitente_nombre": "Coimsa",
        "logo_clave": "COIMSASPA",
    },
    "especial": {
        "destinatario": DEST_ESPECIAL,
        "remitente_nombre": "MVI",
        "logo_clave": "MVI",
    },
}


_mostrar_configuracion()


# ============================================================
# ENVÍO POR CATEGORÍA
# ============================================================

def enviar_correo_categoria(
    categoria: str,
    asunto: str,
    licitaciones: list,
    es_alerta_urgente: bool = False,
    cuerpo_extra_html: str = "",
    destinatario_override: str = None,
    nuevas_licitaciones: list = None,
    activas_anteriores: list = None,
) -> bool:

    if categoria not in CONFIG_CATEGORIAS:

        print(
            f"❌ Categoría desconocida: {categoria}"
        )

        return False

    if not licitaciones and not cuerpo_extra_html:

        print(
            f"ℹ️ No hay contenido para enviar "
            f"en categoría {categoria}."
        )

        return False

    if not EMAIL_USER:

        print(
            "❌ EMAIL_USER no está configurado."
        )

        return False

    if not EMAIL_PASS:

        print(
            "❌ EMAIL_PASS no está configurado."
        )

        return False

    cfg = CONFIG_CATEGORIAS[
        categoria
    ]

    destinatario = (
        destinatario_override
        or cfg["destinatario"]
    )

    if not destinatario:

        print(
            f"❌ No hay destinatario configurado "
            f"para la categoría {categoria}."
        )

        return False

    print(
        f"📨 Preparando correo "
        f"[{categoria}] → {destinatario}"
    )

    html_content = generar_html_correo(
        categoria=categoria,
        licitaciones=licitaciones,
        es_alerta_urgente=es_alerta_urgente,
        cuerpo_extra_html=cuerpo_extra_html,
        nuevas_licitaciones=nuevas_licitaciones,
        activas_anteriores=activas_anteriores,
    )

    msg = MIMEMultipart(
        "related"
    )

    msg["Subject"] = asunto

    msg["From"] = (
        f"{cfg['remitente_nombre']} "
        f"- Bot Mercado Público "
        f"<{EMAIL_USER}>"
    )

    msg["To"] = destinatario

    alt = MIMEMultipart(
        "alternative"
    )

    msg.attach(alt)

    alt.attach(
        MIMEText(
            html_content,
            "html",
            "utf-8",
        )
    )

    # ========================================================
    # IMÁGENES
    # ========================================================

    imagenes = obtener_imagenes_para_cid(
        categoria
    )

    for cid, ruta in imagenes.items():

        if ruta and os.path.exists(ruta):

            _adjuntar_imagen_como_cid(
                msg,
                ruta,
                cid,
            )

    # ========================================================
    # SMTP
    # ========================================================

    exito = _enviar_smtp(
        msg,
        destinatario,
    )

    if exito:

        print(
            f"✅ Correo [{categoria}] "
            f"enviado exitosamente a "
            f"{destinatario}"
        )

    else:

        print(
            f"❌ No se pudo enviar "
            f"el correo [{categoria}] "
            f"a {destinatario}"
        )

    return exito


# ============================================================
# ADJUNTAR IMAGEN
# ============================================================

def _adjuntar_imagen_como_cid(
    msg,
    ruta,
    cid,
):

    try:

        ext = (
            os.path.splitext(
                ruta
            )[1]
            .lower()
        )

        if ext in (
            ".jpg",
            ".jpeg",
        ):

            mime_type = (
                "image/jpeg"
            )

        elif ext == ".png":

            mime_type = (
                "image/png"
            )

        elif ext == ".gif":

            mime_type = (
                "image/gif"
            )

        else:

            mime_type = (
                mimetypes.guess_type(
                    ruta
                )[0]
                or "image/jpeg"
            )

        print(
            f"📎 Adjuntando {ruta} "
            f"como {mime_type}"
        )

        with open(
            ruta,
            "rb",
        ) as f:

            img_data = f.read()

        img = MIMEImage(
            img_data,
            _subtype=mime_type.split(
                "/"
            )[-1],
        )

        img.add_header(
            "Content-ID",
            f"<{cid}>",
        )

        img.add_header(
            "Content-Disposition",
            "inline",
            filename=os.path.basename(
                ruta
            ),
        )

        msg.attach(
            img
        )

        print(
            f"✅ Imagen adjuntada: "
            f"{os.path.basename(ruta)} "
            f"como {cid}"
        )

        return True

    except Exception as e:

        print(
            f"⚠️ No se pudo adjuntar "
            f"{ruta}: {e}"
        )

        return False


# ============================================================
# ENVÍO SMTP
# ============================================================

def _enviar_smtp(
    msg,
    destinatario,
):

    try:

        print(
            "📡 Conectando SMTP:"
        )

        print(
            f"   Servidor: {SMTP_SERVER}"
        )

        print(
            f"   Puerto: {SMTP_PORT}"
        )

        print(
            f"   Remitente: {EMAIL_USER}"
        )

        print(
            f"   Destinatario: {destinatario}"
        )

        if SMTP_PORT == 465:

            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                SMTP_PORT,
                timeout=30,
            ) as server:

                print(
                    "🔐 Autenticando SMTP..."
                )

                server.login(
                    EMAIL_USER,
                    EMAIL_PASS,
                )

                print(
                    "📤 Enviando correo..."
                )

                server.sendmail(
                    EMAIL_USER,
                    destinatario,
                    msg.as_string(),
                )

        else:

            with smtplib.SMTP(
                SMTP_SERVER,
                SMTP_PORT,
                timeout=30,
            ) as server:

                print(
                    "🔐 Iniciando STARTTLS..."
                )

                server.starttls()

                print(
                    "🔐 Autenticando SMTP..."
                )

                server.login(
                    EMAIL_USER,
                    EMAIL_PASS,
                )

                print(
                    "📤 Enviando correo..."
                )

                server.sendmail(
                    EMAIL_USER,
                    destinatario,
                    msg.as_string(),
                )

        print(
            "✅ SMTP aceptó el correo."
        )

        return True

    except (
        smtplib.SMTPAuthenticationError
    ) as e:

        print(
            "❌ Error de autenticación SMTP: "
            f"{e}"
        )

        return False

    except (
        smtplib.SMTPConnectError
    ) as e:

        print(
            "❌ No se pudo conectar al "
            f"servidor SMTP: {e}"
        )

        return False

    except (
        smtplib.SMTPException
    ) as e:

        print(
            f"❌ Error SMTP: {e}"
        )

        return False

    except (
        OSError
    ) as e:

        print(
            "❌ Error de red/DNS al "
            f"conectar con SMTP: {e}"
        )

        return False

    except Exception as e:

        print(
            f"❌ Error inesperado enviando "
            f"correo: {e}"
        )

        return False


# ============================================================
# MODO PRUEBA
# ============================================================

def set_modo_prueba():
    """
    Fuerza temporalmente las tres categorías a soporte.
    No se utiliza automáticamente.
    """

    for categoria in CONFIG_CATEGORIAS:

        CONFIG_CATEGORIAS[
            categoria
        ]["destinatario"] = (
            DEST_PRUEBA_SOPORTE
        )

    print(
        "🔧 Modo PRUEBA activado: "
        "todos los correos van a "
        "soporte@induwork.cl"
    )


# ============================================================
# MODO PRODUCCIÓN
# ============================================================

def set_modo_produccion():
    """
    Restaura los destinatarios configurados
    mediante variables de entorno.
    """

    CONFIG_CATEGORIAS[
        "induwork"
    ]["destinatario"] = DEST_INDUWORK

    CONFIG_CATEGORIAS[
        "coimsa"
    ]["destinatario"] = DEST_COIMSA

    CONFIG_CATEGORIAS[
        "especial"
    ]["destinatario"] = DEST_ESPECIAL

    print(
        "🔧 Modo PRODUCCIÓN activado "
        "con destinatarios de entorno."
    )