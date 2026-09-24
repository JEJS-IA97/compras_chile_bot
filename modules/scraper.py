# modules/scraper.py

import os
import re
import time
import datetime

from zoneinfo import ZoneInfo

import requests

from config.database import get_db

from modules.filters import (
    evaluar_licitacion,
    posible_relevante,
    contiene_keyword_induwork,
    keywords_induwork_detectadas,
)

from modules.ai_classifier import (
    clasificar_con_gemini,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

CL_TZ = ZoneInfo(
    "America/Santiago"
)

UTC_TZ = ZoneInfo(
    "UTC"
)

db = get_db()

TICKET = os.getenv(
    "CHILECOMPRA_TICKET"
)


# ============================================================
# API LICITACIONES V1
# ============================================================

BASE_URL_V1 = (
    "https://api.mercadopublico.cl/"
    "servicios/v1/publico"
)

HEADERS_V1 = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64)"
    ),
    "Accept": "application/json",
}


# ============================================================
# API COMPRA ÁGIL V2
# ============================================================

BASE_URL_V2 = (
    "https://api2.mercadopublico.cl"
)

ENDPOINT_COMPRA_AGIL = (
    f"{BASE_URL_V2}/v2/compra-agil"
)


# ============================================================
# PARÁMETROS
# ============================================================

HORAS_URGENTE_COMPRA_AGIL = 72

DETAIL_REQUEST_DELAY = 1.0

MAX_RETRIES_429 = 3

BACKOFF_429 = (
    3,
    8,
    15,
)

# La API v2 de Compra Ágil hace timeout (HTTP 504)
# con tamano_pagina >= 25. Size 10 responde 200 de forma
# confiable (~10–25s por página).
COMPRA_AGIL_TAMANO_PAGINA = 10

# Timeout por página: la API es lenta; el gateway corta ~30s.
COMPRA_AGIL_TIMEOUT_PAGINA = 90

# Máximo de páginas por consulta (con size 10 = hasta N*10 ítems).
# La recuperación de 14 días puede tener miles de resultados;
# no escaneamos todas las páginas en cada fast-check.
COMPRA_AGIL_MAX_PAGINAS_INCREMENTAL = 5
COMPRA_AGIL_MAX_PAGINAS_RECUPERACION = 30


# ============================================================
# RECUPERACIÓN COMPRA ÁGIL
# ============================================================

# Recuperamos oportunidades publicadas durante los
# últimos 14 días además del mecanismo incremental.
#
# Esto evita depender exclusivamente de ttl_cambio_ms,
# porque una Compra Ágil puede haberse publicado hace varios
# días y seguir abierta hoy.
COMPRA_AGIL_DIAS_RECUPERACION = 14


# ============================================================
# UTILIDADES
# ============================================================

def _url_licitacion(
    codigo,
):
    return (
        "https://www.mercadopublico.cl/"
        "Procurement/Modules/RFB/"
        f"DetailsAcquisition.aspx?idlicitacion={codigo}"
    )


def _parsear_fecha(
    valor,
):
    if not valor:
        return None

    if isinstance(
        valor,
        datetime.datetime,
    ):

        fecha = valor

        if fecha.tzinfo is not None:

            fecha = fecha.astimezone(
                CL_TZ
            ).replace(
                tzinfo=None
            )

        return fecha

    if not isinstance(
        valor,
        str,
    ):
        return None

    valor = valor.strip()

    if not valor:
        return None

    formatos = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
    )

    for formato in formatos:

        try:

            return datetime.datetime.strptime(
                valor,
                formato,
            )

        except ValueError:

            continue

    try:

        fecha = datetime.datetime.fromisoformat(
            valor.replace(
                "Z",
                "+00:00",
            )
        )

        if fecha.tzinfo is not None:

            fecha = fecha.astimezone(
                CL_TZ
            ).replace(
                tzinfo=None
            )

        return fecha

    except ValueError:

        return None


def _formatear_monto(
    monto,
    moneda,
):

    if monto in (
        None,
        "",
        0,
    ):

        return "No especificado"

    try:

        return (
            f"{moneda or 'CLP'} "
            f"{float(monto):,.0f}"
            .replace(
                ",",
                ".",
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        return (
            f"{moneda or ''} "
            f"{monto}"
        ).strip()


def _ahora_utc_naive():

    return datetime.datetime.now(
        datetime.timezone.utc
    ).replace(
        tzinfo=None
    )


def _ahora_chile_naive():

    return datetime.datetime.now(
        CL_TZ
    ).replace(
        tzinfo=None
    )


def _es_fecha_de_hoy_chile(
    valor,
):

    if not valor:
        return False

    if not isinstance(
        valor,
        datetime.datetime,
    ):
        return False

    fecha = valor

    if fecha.tzinfo is None:

        fecha = fecha.replace(
            tzinfo=datetime.timezone.utc
        )

    fecha_chile = fecha.astimezone(
        CL_TZ
    )

    hoy_chile = datetime.datetime.now(
        CL_TZ
    ).date()

    return (
        fecha_chile.date()
        == hoy_chile
    )


# ============================================================
# DETALLE V1
# ============================================================

def _esperar_entre_detalles():

    time.sleep(
        DETAIL_REQUEST_DELAY
    )


def _get_con_reintento_429(
    url,
    *,
    params=None,
    headers=None,
    timeout=30,
    es_detalle=False,
):

    for intento in range(
        MAX_RETRIES_429 + 1
    ):

        if es_detalle:
            _esperar_entre_detalles()

        try:

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )

        except requests.exceptions.Timeout:

            if intento >= MAX_RETRIES_429:

                raise

            espera = BACKOFF_429[
                min(
                    intento,
                    len(BACKOFF_429) - 1,
                )
            ]

            print(
                f"⚠️ Timeout. "
                f"Reintentando en {espera}s..."
            )

            time.sleep(
                espera
            )

            continue

        except requests.exceptions.RequestException:

            raise

        if response.status_code != 429:

            return response

        if intento >= MAX_RETRIES_429:

            return response

        retry_after = (
            response.headers.get(
                "Retry-After"
            )
        )

        if retry_after:

            try:

                espera = max(
                    float(retry_after),
                    BACKOFF_429[
                        min(
                            intento,
                            len(BACKOFF_429) - 1,
                        )
                    ],
                )

            except ValueError:

                espera = BACKOFF_429[
                    min(
                        intento,
                        len(BACKOFF_429) - 1,
                    )
                ]

        else:

            espera = BACKOFF_429[
                min(
                    intento,
                    len(BACKOFF_429) - 1,
                )
            ]

        print(
            f"⚠️ Mercado Público respondió "
            f"HTTP 429. Reintento "
            f"{intento + 1}/"
            f"{MAX_RETRIES_429} "
            f"en {espera}s..."
        )

        time.sleep(
            espera
        )

    return response


# ============================================================
# OBTENER LICITACIONES ACTIVAS
# ============================================================

def obtener_licitaciones_api_real():

    if not TICKET:

        print(
            "❌ Error: No se ha configurado "
            "CHILECOMPRA_TICKET."
        )

        return []

    url = (
        f"{BASE_URL_V1}/licitaciones.json"
    )

    params = {
        "estado": "activas",
        "ticket": TICKET,
    }

    try:

        print(
            "📡 Consultando TODAS las "
            "licitaciones activas actualmente "
            "en Mercado Público..."
        )

        response = _get_con_reintento_429(
            url,
            params=params,
            headers=HEADERS_V1,
            timeout=30,
        )

        if response.status_code == 200:

            listado = (
                response.json()
                .get(
                    "Listado",
                    [],
                )
            )

            print(
                f"🔎 {len(listado)} "
                "licitaciones activas "
                "recibidas desde "
                "Mercado Público."
            )

            return listado

        print(
            "⚠️ Error Mercado Público: "
            f"HTTP {response.status_code} - "
            f"{response.text[:500]}"
        )

        return []

    except requests.exceptions.Timeout:

        print(
            "❌ Timeout consultando "
            "licitaciones activas."
        )

        return []

    except requests.exceptions.RequestException as e:

        print(
            f"❌ Error HTTP consultando "
            f"Mercado Público: {e}"
        )

        return []

    except Exception as e:

        print(
            f"❌ Error inesperado consultando "
            f"Mercado Público: {e}"
        )

        return []


# ============================================================
# DETALLE LICITACIÓN
# ============================================================

def obtener_detalle_licitacion(
    codigo,
):

    url = (
        f"{BASE_URL_V1}/licitaciones.json"
    )

    params = {
        "codigo": codigo,
        "ticket": TICKET,
    }

    try:

        response = _get_con_reintento_429(
            url,
            params=params,
            headers=HEADERS_V1,
            timeout=30,
            es_detalle=True,
        )

        if response.status_code != 200:

            print(
                f"⚠️ Detalle {codigo} "
                "respondió HTTP "
                f"{response.status_code}"
            )

            return {}

        listado = (
            response.json()
            .get(
                "Listado",
                [],
            )
        )

        return (
            listado[0]
            if listado
            else {}
        )

    except requests.exceptions.Timeout:

        print(
            f"⚠️ Timeout obteniendo "
            f"detalle de {codigo}."
        )

        return {}

    except requests.exceptions.RequestException as e:

        print(
            f"⚠️ Error HTTP obteniendo "
            f"detalle de {codigo}: {e}"
        )

        return {}

    except Exception as e:

        print(
            f"⚠️ No se pudo obtener "
            f"detalle de {codigo}: {e}"
        )

        return {}


# ============================================================
# PRODUCTOS LICITACIÓN V1
# ============================================================

def _extraer_items_licitacion(
    detalle,
):

    if not isinstance(
        detalle,
        dict,
    ):

        return []

    items_container = (
        detalle.get(
            "Items"
        )
        or detalle.get(
            "items"
        )
        or {}
    )

    if not isinstance(
        items_container,
        dict,
    ):

        return []

    listado = (
        items_container.get(
            "Listado"
        )
        or items_container.get(
            "listado"
        )
        or {}
    )

    if not isinstance(
        listado,
        dict,
    ):

        return []

    items = (
        listado.get(
            "item"
        )
        or listado.get(
            "Item"
        )
        or []
    )

    if isinstance(
        items,
        dict,
    ):

        items = [
            items
        ]

    if not isinstance(
        items,
        list,
    ):

        return []

    productos = []

    for item in items:

        if not isinstance(
            item,
            dict,
        ):

            continue

        nombre = (
            item.get(
                "NombreProducto"
            )
            or item.get(
                "nombre"
            )
            or item.get(
                "Nombre"
            )
            or ""
        )

        descripcion = (
            item.get(
                "Descripcion"
            )
            or item.get(
                "descripcion"
            )
            or ""
        )

        categoria = (
            item.get(
                "Categoria"
            )
            or item.get(
                "categoria"
            )
            or ""
        )

        codigo_producto = (
            item.get(
                "CodigoProducto"
            )
            or item.get(
                "codigo_producto"
            )
            or ""
        )

        cantidad = (
            item.get(
                "Cantidad"
            )
            or item.get(
                "cantidad"
            )
        )

        unidad_medida = (
            item.get(
                "UnidadMedida"
            )
            or item.get(
                "unidad_medida"
            )
            or ""
        )

        producto = {
            "codigo_producto": codigo_producto,
            "nombre": nombre,
            "descripcion": descripcion,
            "categoria": categoria,
            "cantidad": cantidad,
            "unidad_medida": unidad_medida,
        }

        if any(
            (
                nombre,
                descripcion,
                categoria,
                codigo_producto,
            )
        ):

            productos.append(
                producto
            )

    return productos


def _texto_productos(
    productos,
):

    partes = []

    for producto in productos:

        partes.extend(
            [
                producto.get(
                    "nombre",
                    "",
                ),
                producto.get(
                    "descripcion",
                    "",
                ),
                producto.get(
                    "categoria",
                    "",
                ),
            ]
        )

    return " ".join(
        str(parte)
        for parte in partes
        if parte
    ).strip()


# ============================================================
# MONTO DESDE TEXTO
# ============================================================

def _extraer_monto_desde_texto(
    texto,
):

    if not texto:
        return None

    patrones = (

        r"\$\s*"
        r"([0-9]{1,3}"
        r"(?:\.[0-9]{3})+"
        r"(?:,[0-9]+)?)",

        r"(?i)"
        r"(?:presupuesto|monto|"
        r"valor|presupuesto máximo|"
        r"monto máximo)"
        r"[^0-9]{0,80}"
        r"([0-9]{1,3}"
        r"(?:\.[0-9]{3})+"
        r"(?:,[0-9]+)?)",
    )

    for patron in patrones:

        match = re.search(
            patron,
            str(texto),
        )

        if not match:
            continue

        valor = match.group(
            1
        )

        try:

            valor = (
                valor
                .replace(
                    ".",
                    "",
                )
                .replace(
                    ",",
                    ".",
                )
            )

            return float(
                valor
            )

        except (
            ValueError,
            TypeError,
        ):

            continue

    return None


def _extraer_monto_licitacion(
    detalle,
    lic_basico,
    texto_contexto,
):

    candidatos = (
        detalle.get(
            "MontoEstimado"
        ),
        detalle.get(
            "Monto"
        ),
        lic_basico.get(
            "MontoEstimado"
        ),
        lic_basico.get(
            "Monto"
        ),
    )

    monto = next(
        (
            valor
            for valor in candidatos
            if valor not in (
                None,
                "",
                0,
            )
        ),
        None,
    )

    if monto is None:

        monto = (
            _extraer_monto_desde_texto(
                texto_contexto
            )
        )

    return monto


# ============================================================
# MAPEO LICITACIÓN
# ============================================================

def _mapear_licitacion(
    lic_basico,
    detalle,
):

    codigo = (
        lic_basico.get(
            "CodigoExterno"
        )
        or detalle.get(
            "CodigoExterno"
        )
    )

    comprador = (
        detalle.get(
            "Comprador",
            {},
        )
        or {}
    )

    fechas = (
        detalle.get(
            "Fechas",
            {},
        )
        or {}
    )

    organismo = (
        comprador.get(
            "NombreOrganismo"
        )
        or detalle.get(
            "NombreOrganismo"
        )
        or detalle.get(
            "Organismo"
        )
        or "Organismo Desconocido"
    )

    region = (
        comprador.get(
            "RegionUnidad"
        )
        or detalle.get(
            "Region"
        )
        or "No Especificada"
    )

    descripcion = (
        detalle.get(
            "Descripcion"
        )
        or lic_basico.get(
            "Descripcion"
        )
        or detalle.get(
            "Nombre"
        )
        or lic_basico.get(
            "Nombre",
            "",
        )
    )

    productos = (
        _extraer_items_licitacion(
            detalle
        )
    )

    texto_productos = (
        _texto_productos(
            productos
        )
    )

    fecha_cierre = (
        fechas.get(
            "FechaCierre"
        )
        or detalle.get(
            "FechaCierre"
        )
        or lic_basico.get(
            "FechaCierre",
            "Sin fecha",
        )
    )

    fecha_publicacion = (
        fechas.get(
            "FechaPublicacion"
        )
        or detalle.get(
            "FechaPublicacion"
        )
        or lic_basico.get(
            "FechaPublicacion",
            "Sin fecha",
        )
        or "Sin fecha"
    )

    texto_contexto = (
        f"{detalle.get('Nombre', '')} "
        f"{lic_basico.get('Nombre', '')} "
        f"{descripcion} "
        f"{texto_productos}"
    )

    monto_estimado = (
        _extraer_monto_licitacion(
            detalle,
            lic_basico,
            texto_contexto,
        )
    )

    moneda = (
        detalle.get(
            "Moneda"
        )
        or lic_basico.get(
            "Moneda"
        )
        or "CLP"
    )

    return {
        "id": codigo,
        "nombre": (
            detalle.get(
                "Nombre"
            )
            or lic_basico.get(
                "Nombre",
                "Licitación sin título",
            )
        ),
        "descripcion": descripcion,
        "productos_solicitados": productos,
        "texto_productos": texto_productos,
        "region": region,
        "organismo": organismo,
        "fecha_cierre": fecha_cierre,
        "fecha_publicacion": fecha_publicacion,
        "link": _url_licitacion(
            codigo
        ),
        "tipo": "Licitación",
        "monto_estimado": monto_estimado,
        "moneda": moneda,
        "monto_formateado": (
            _formatear_monto(
                monto_estimado,
                moneda,
            )
        ),
        "visibilidad_monto": (
            detalle.get(
                "VisibilidadMonto"
            )
            or lic_basico.get(
                "VisibilidadMonto"
            )
        ),
        "requiere_garantia_seriedad": None,
        "monto_garantia_seriedad": None,
        "requiere_garantia_fiel_cumplimiento": None,
        "monto_garantia_fiel_cumplimiento": None,
    }


# ============================================================
# DB
# ============================================================

def _obtener_existente(
    codigo,
):

    if db is None:

        return None

    return db[
        "licitaciones"
    ].find_one(
        {
            "id": codigo
        }
    )


def _guardar_nueva(
    licitacion,
    clasificacion,
    ahora_utc,
):

    licitacion[
        "clasificacion"
    ] = clasificacion

    licitacion[
        "fecha_captura"
    ] = ahora_utc

    licitacion[
        "fecha_primera_deteccion"
    ] = ahora_utc

    licitacion[
        "ultima_verificacion"
    ] = ahora_utc

    licitacion[
        "activa"
    ] = True

    if db is None:

        return True

    try:

        db[
            "licitaciones"
        ].insert_one(
            licitacion.copy()
        )

        return True

    except Exception as e:

        print(
            f"⚠️ No se pudo guardar "
            f"{licitacion.get('id')}: {e}"
        )

        return False


def _actualizar_existente(
    codigo,
    licitacion,
    clasificacion,
    existente,
    ahora_utc,
):

    fecha_primera = (
        existente.get(
            "fecha_primera_deteccion"
        )
        or existente.get(
            "fecha_captura"
        )
    )

    licitacion_actualizada = (
        licitacion.copy()
    )

    licitacion_actualizada[
        "clasificacion"
    ] = clasificacion

    if clasificacion.get(
        "induwork"
    ) and existente.get(
        "validacion_ia_induwork"
    ):

        licitacion_actualizada[
            "validacion_ia_induwork"
        ] = existente[
            "validacion_ia_induwork"
        ]

    elif "validacion_ia_induwork" in licitacion_actualizada:

        licitacion_actualizada.pop(
            "validacion_ia_induwork",
            None,
        )

    licitacion_actualizada[
        "fecha_primera_deteccion"
    ] = fecha_primera

    licitacion_actualizada[
        "fecha_captura"
    ] = existente.get(
        "fecha_captura",
        fecha_primera,
    )

    licitacion_actualizada[
        "ultima_verificacion"
    ] = ahora_utc

    licitacion_actualizada[
        "activa"
    ] = True

    if db is not None:

        try:

            datos_actualizados = {
                key: value
                for key, value
                in licitacion_actualizada.items()
                if key != "id"
            }

            update_doc = {
                "$set": datos_actualizados
            }

            if (
                "validacion_ia_induwork"
                not in datos_actualizados
            ):

                update_doc[
                    "$unset"
                ] = {
                    "validacion_ia_induwork": "",
                }

            db[
                "licitaciones"
            ].update_one(
                {
                    "id": codigo
                },
                update_doc,
            )

        except Exception as e:

            print(
                f"⚠️ No se pudo actualizar "
                f"{codigo}: {e}"
            )

    return licitacion_actualizada


# ============================================================
# PROCESAR LICITACIONES
# ============================================================

def procesar_y_guardar_licitaciones():

    licitaciones_activas = (
        obtener_licitaciones_api_real()
    )

    resultado = {
        "nuevas": [],
        "activas_anteriores": [],
        "fallidos_detalles": [],
    }

    if not licitaciones_activas:

        print(
            "❌ API de licitaciones sin datos "
            "(fallo HTTP o listado vacío). "
            "NO se interpreta como 'sin oportunidades'."
        )

        return resultado

    candidatas = []
    fallidos_detalles = []

    for lic in licitaciones_activas:

        texto_basico = (
            f"{lic.get('Nombre', '')} "
            f"{lic.get('Descripcion', '')}"
        )

        if posible_relevante(
            texto_basico
        ):

            candidatas.append(
                lic
            )

    print(
        f"🔍 {len(candidatas)} "
        f"candidatas de "
        f"{len(licitaciones_activas)} "
        "licitaciones activas."
    )

    ahora_chile = (
        _ahora_chile_naive()
    )

    ahora_utc = (
        _ahora_utc_naive()
    )

    for indice, lic in enumerate(
        candidatas,
        start=1,
    ):

        codigo = lic.get(
            "CodigoExterno"
        )

        if not codigo:
            continue

        print(
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            f"🔎 Candidata "
            f"{indice}/{len(candidatas)}: "
            f"{codigo}"
        )

        detalle = (
            obtener_detalle_licitacion(
                codigo
            )
        )

        if not detalle:

            print(
                f"⚠️ Detalle de {codigo} vacío "
                "o fallido. Reintentando una vez..."
            )

            _esperar_entre_detalles()

            detalle = (
                obtener_detalle_licitacion(
                    codigo
                )
            )

        if not detalle:

            print(
                f"❌ ERROR DETALLE: {codigo} "
                "no se pudo obtener tras reintento. "
                "NO se omite en silencio — se contabiliza."
            )

            fallidos_detalles.append(
                codigo
            )

            continue

        licitacion_mapeada = (
            _mapear_licitacion(
                lic,
                detalle,
            )
        )

        fecha_cierre_dt = (
            _parsear_fecha(
                licitacion_mapeada[
                    "fecha_cierre"
                ]
            )
        )

        if (
            fecha_cierre_dt
            and fecha_cierre_dt
            < ahora_chile
        ):

            print(
                f"⏭️ {codigo} ya cerró "
                f"({licitacion_mapeada['fecha_cierre']})."
            )

            continue

        clasificacion = (
            evaluar_licitacion(
                licitacion_mapeada
            )
        )

        texto = (
            f"{licitacion_mapeada.get('nombre', '')} "
            f"{licitacion_mapeada.get('descripcion', '')} "
            f"{licitacion_mapeada.get('texto_productos', '')}"
        )

        existente = (
            _obtener_existente(
                codigo
            )
        )

        # ====================================================
        # INDUWORK
        # ====================================================

        if contiene_keyword_induwork(
            texto
        ):

            terminos = (
                keywords_induwork_detectadas(
                    texto
                )
            )

            print(
                "🎯 Coincidencia Induwork: "
                f"{terminos}"
            )

            debe_consultar_gemini = True

            if existente:

                clasificacion_existente = (
                    existente.get(
                        "clasificacion",
                        {},
                    )
                )

                validacion_existente = (
                    existente.get(
                        "validacion_ia_induwork"
                    )
                )

                if (
                    clasificacion_existente.get(
                        "induwork",
                        False,
                    )
                    and validacion_existente
                ):

                    debe_consultar_gemini = (
                        False
                    )

                    clasificacion[
                        "induwork"
                    ] = True

                    licitacion_mapeada[
                        "validacion_ia_induwork"
                    ] = (
                        validacion_existente
                    )

                    print(
                        "♻️ Ya validada anteriormente "
                        "por Gemini."
                    )

            if debe_consultar_gemini:

                print(
                    "🤖 Consultando Gemini "
                    "para validar relevancia..."
                )

                clasificacion_ia = (
                    clasificar_con_gemini(
                        licitacion_mapeada.get(
                            "nombre",
                            "",
                        ),
                        (
                            f"{licitacion_mapeada.get('descripcion', '')} "
                            f"Productos: "
                            f"{licitacion_mapeada.get('texto_productos', '')}"
                        ),
                        organismo=licitacion_mapeada.get(
                            "organismo",
                            "",
                        ),
                        region=licitacion_mapeada.get(
                            "region",
                            "",
                        ),
                    )
                )

                clasificacion[
                    "induwork"
                ] = (
                    clasificacion_ia[
                        "induwork"
                    ]
                )

                if (
                    clasificacion_ia[
                        "induwork"
                    ]
                ):

                    licitacion_mapeada[
                        "validacion_ia_induwork"
                    ] = {
                        "motivo": (
                            clasificacion_ia.get(
                                "motivo",
                                "",
                            )
                        ),
                        "terminos_detectados": (
                            clasificacion_ia.get(
                                "terminos_detectados",
                                [],
                            )
                        ),
                    }

                    print(
                        "✅ Gemini APROBÓ "
                        f"{codigo} para Induwork"
                    )

                    print(
                        "   Motivo: "
                        f"{clasificacion_ia.get('motivo', '')}"
                    )

                else:

                    print(
                        "⛔ Gemini DESCARTÓ "
                        f"{codigo} para Induwork."
                    )

                    if existente and db is not None:

                        try:

                            db[
                                "licitaciones"
                            ].update_one(
                                {
                                    "id": codigo
                                },
                                {
                                    "$set": {
                                        "clasificacion.induwork": False,
                                    },
                                    "$unset": {
                                        "validacion_ia_induwork": "",
                                    },
                                },
                            )

                            print(
                                "♻️ Rechazo persistido "
                                f"para {codigo}."
                            )

                        except Exception as e:

                            print(
                                "⚠️ No se pudo persistir "
                                f"el rechazo de {codigo}: {e}"
                            )

        # ====================================================
        # NINGUNA CATEGORÍA
        # ====================================================

        if not (
            clasificacion[
                "coimsa"
            ]
            or clasificacion[
                "induwork"
            ]
            or clasificacion[
                "especial"
            ]
        ):

            print(
                f"⏭️ {codigo} no clasifica "
                "para ninguna categoría."
            )

            if existente and db is not None:

                try:

                    db[
                        "licitaciones"
                    ].update_one(
                        {
                            "id": codigo
                        },
                        {
                            "$set": {
                                "clasificacion": clasificacion,
                                "ultima_verificacion": ahora_utc,
                            },
                            "$unset": {
                                "validacion_ia_induwork": "",
                            },
                        },
                    )

                    print(
                        "♻️ Clasificación actualizada "
                        f"para {codigo} (sin categoría)."
                    )

                except Exception as e:

                    print(
                        "⚠️ No se pudo actualizar "
                        f"{codigo}: {e}"
                    )

            continue

        # ====================================================
        # NUEVA
        # ====================================================

        if existente is None:

            guardada = _guardar_nueva(
                licitacion_mapeada,
                clasificacion,
                ahora_utc,
            )

            if guardada:

                resultado[
                    "nuevas"
                ].append(
                    licitacion_mapeada
                )

                print(
                    f"✨ [NUEVA] {codigo} "
                    "guardada en MongoDB."
                )

            continue

        # ====================================================
        # EXISTENTE
        # ====================================================

        licitacion_actualizada = (
            _actualizar_existente(
                codigo,
                licitacion_mapeada,
                clasificacion,
                existente,
                ahora_utc,
            )
        )

        fecha_primera = (
            licitacion_actualizada.get(
                "fecha_primera_deteccion"
            )
        )

        if _es_fecha_de_hoy_chile(
            fecha_primera
        ):

            resultado[
                "nuevas"
            ].append(
                licitacion_actualizada
            )

            print(
                f"🆕 [HOY] {codigo} "
                "corresponde a una detección de hoy."
            )

        else:

            resultado[
                "activas_anteriores"
            ].append(
                licitacion_actualizada
            )

            print(
                f"♻️ [ACTIVA ANTERIOR] "
                f"{codigo} continúa publicada."
            )

    print(
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "📊 RESULTADO DEL PROCESAMIENTO"
    )

    print(
        f"🆕 Nuevas hoy: "
        f"{len(resultado['nuevas'])}"
    )

    print(
        f"♻️ Activas anteriores: "
        f"{len(resultado['activas_anteriores'])}"
    )

    print(
        f"❌ Detalle fallido: "
        f"{len(fallidos_detalles)}"
    )

    if fallidos_detalles:

        print(
            "   Códigos: "
            + ", ".join(fallidos_detalles[:20])
        )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    resultado[
        "fallidos_detalles"
    ] = fallidos_detalles

    return resultado


# ============================================================
# COMPRA ÁGIL V2 - REQUEST
# ============================================================

def _request_compra_agil(
    url,
    headers,
    *,
    params=None,
    timeout=45,
    max_retries=1,
):
    """
    Realiza una consulta a la API v2 de Compra Ágil.

    IMPORTANTE:
    No hacemos varios reintentos largos para cada búsqueda.
    La API puede devolver 504 en determinadas consultas,
    especialmente cuando la búsqueda es demasiado pesada.

    Un error temporal se reintenta una sola vez y después
    se continúa con la siguiente búsqueda.
    """

    backoffs = (
        2,
        5,
    )

    for intento in range(
        max_retries + 1
    ):

        try:

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as error:

            if intento >= max_retries:

                raise

            espera = backoffs[
                min(
                    intento,
                    len(backoffs) - 1,
                )
            ]

            print(
                "⚠️ Error temporal de red "
                f"({error}). "
                f"Reintentando una vez en "
                f"{espera}s..."
            )

            time.sleep(
                espera
            )

            continue

        if response.status_code in (
            429,
            500,
            502,
            503,
            504,
        ):

            if intento >= max_retries:

                return response

            espera = backoffs[
                min(
                    intento,
                    len(backoffs) - 1,
                )
            ]

            print(
                "⚠️ Compra Ágil API respondió "
                f"HTTP {response.status_code}. "
                f"Reintentando en {espera}s..."
            )

            time.sleep(
                espera
            )

            continue

        return response

    raise RuntimeError(
        "No fue posible consultar "
        "Compra Ágil."
    )


# ============================================================
# NORMALIZAR QUERY PARA LA API
# ============================================================

def _normalizar_query_compra_agil(
    termino,
):
    """
    Convierte las variantes de las búsquedas manuales
    a una forma más estable para la API.

    La lista comercial NO cambia.

    Ejemplos:

        anti corte
        -> anticorte

        anti cortes
        -> anticortes

        anti punzon
        -> antipunzon

        anti bala
        -> antibala

        tácticas
        -> tacticas

    Esto evita enviar a la API búsquedas con espacios que
    hemos comprobado que pueden provocar HTTP 504.
    """

    import unicodedata

    texto = str(
        termino or ""
    ).strip().lower()

    texto = (
        unicodedata.normalize(
            "NFKD",
            texto,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii"
        )
    )

    texto = (
        texto
        .replace(
            " ",
            "",
        )
        .replace(
            "-",
            "",
        )
    )

    return texto


# ============================================================
# BÚSQUEDAS INDUWORK
# ============================================================

def _obtener_busquedas_compra_agil_induwork():
    """
    Mantiene las 28 búsquedas manuales originales.

    Luego agrega la segunda capa de productos.

    Las búsquedas originales conservan exactamente sus
    variantes conceptuales. Para la llamada HTTP se genera
    una versión normalizada y se eliminan duplicados.
    """

    busquedas_originales = [
        "anticorte",
        "anticortes",
        "anti corte",
        "anti cortes",
        "anti punzon",
        "antipunzon",
        "antipunzonamiento",
        "anti punzonamiento",
        "tactica",
        "tacticas",
        "táctica",
        "tácticas",
        "tactico",
        "tacticos",
        "táctico",
        "tácticos",
        "antibala",
        "antibalas",
        "anti bala",
        "anti balas",
        "balistico",
        "balisticos",
        "balístico",
        "balísticos",
        "balistica",
        "balisticas",
        "balística",
        "balísticas",
    ]

    # ========================================================
    # NUEVA SEGUNDA CAPA
    # ========================================================

    # Estas palabras sirven solamente para ampliar cobertura.
    #
    # NO representan aprobación automática.
    #
    # Después del detalle pasan por el contexto comercial
    # de Induwork y por Gemini.
    busquedas_adicionales = [
        "chaleco",
        "chalecos",
        "botas",
        "bota",
        "calzado",
        "uniforme",
        "uniformes",
        "reflectante",
        "reflectantes",
        "casco",
        "cascos",
        "baston",
        "bastones",
        "bastón",
        "portabaston",
        "portabastones",
        "portarevolver",
        "portarevólver",
        "porta revolver",
        "porta revólver",
        "pistolera",
        "pistoleras",
        "esposas",
        "porta esposas",
    ]

    return (
        busquedas_originales,
        busquedas_adicionales,
    )


# ============================================================
# PAGINACIÓN DE UNA BÚSQUEDA
# ============================================================

def _buscar_compra_agil_por_query(
    termino_original,
    tipo_busqueda,
    headers,
):
    """
    Busca una palabra/expresión mediante q.

    La API recibe la forma normalizada.

    Devuelve todos los items encontrados dentro de un límite
    razonable de páginas.
    """

    query_api = (
        _normalizar_query_compra_agil(
            termino_original
        )
    )

    if not query_api:

        return []

    print(
        "\n🔍 Compra Ágil "
        f"[{tipo_busqueda}] "
        f"q={termino_original}"
    )

    if (
        query_api
        != termino_original.lower().replace(
            " ",
            "",
        )
    ):

        print(
            f"   ↳ Consulta API: "
            f"q={query_api}"
        )

    resultados = []

    numero_pagina = 1

    max_paginas = 5

    while (
        numero_pagina
        <= max_paginas
    ):

        params = {
            "q": query_api,
            "estado": "publicada",
            "tamano_pagina": 50,
            "numero_pagina": numero_pagina,
        }

        try:

            response = _request_compra_agil(
                ENDPOINT_COMPRA_AGIL,
                headers,
                params=params,
                timeout=45,
                max_retries=1,
            )

        except requests.exceptions.RequestException as e:

            print(
                f"❌ q={termino_original} "
                f"falló: {e}"
            )

            return resultados

        if response.status_code != 200:

            print(
                f"⚠️ q={termino_original} "
                "respondió HTTP "
                f"{response.status_code}"
            )

            return resultados

        try:

            data = response.json()

        except ValueError:

            print(
                f"⚠️ q={termino_original} "
                "devolvió JSON inválido."
            )

            return resultados

        payload = (
            data.get(
                "payload",
                {},
            )
            or {}
        )

        items = (
            payload.get(
                "items",
                [],
            )
            or []
        )

        paginacion = (
            payload.get(
                "paginacion",
                {},
            )
            or {}
        )

        resultados.extend(
            items
        )

        print(
            f"   → página "
            f"{numero_pagina}: "
            f"{len(items)} resultado(s)"
        )

        total_paginas = int(
            paginacion.get(
                "total_paginas",
                1,
            )
            or 1
        )

        numero_respuesta = int(
            paginacion.get(
                "numero_pagina",
                numero_pagina,
            )
            or numero_pagina
        )

        if (
            not items
            or numero_respuesta
            >= total_paginas
        ):

            break

        numero_pagina += 1

        time.sleep(
            0.75
        )

    return resultados


# ============================================================
# DETALLE COMPRA ÁGIL
# ============================================================

def _obtener_detalle_compra_agil(
    codigo,
    headers,
):

    try:

        response = _request_compra_agil(
            ENDPOINT_COMPRA_AGIL,
            headers,
            params={
                "id": codigo,
            },
            timeout=45,
            max_retries=1,
        )

    except requests.exceptions.RequestException as e:

        print(
            f"⚠️ Error obteniendo detalle "
            f"de Compra Ágil "
            f"{codigo}: {e}"
        )

        return {}

    if response.status_code != 200:

        print(
            f"⚠️ Detalle Compra Ágil "
            f"{codigo} respondió HTTP "
            f"{response.status_code}"
        )

        return {}

    try:

        data = response.json()

    except ValueError:

        print(
            f"⚠️ Respuesta JSON inválida "
            f"para Compra Ágil {codigo}."
        )

        return {}

    return (
        data.get(
            "payload",
            {},
        )
        or {}
    )


# ============================================================
# FECHA DE CIERRE DESDE EL LISTADO
# ============================================================

def _fecha_cierre_item_compra_agil(
    item,
):

    fechas = (
        item.get(
            "fechas",
            {},
        )
        or {}
    )

    return (
        fechas.get(
            "fecha_cierre"
        )
        or item.get(
            "fecha_cierre"
        )
    )


# ============================================================
# MAPEAR COMPRA ÁGIL
# ============================================================

def _mapear_compra_agil(
    item,
    detalle,
):

    fechas = (
        detalle.get(
            "fechas",
            {},
        )
        or {}
    )

    convocatoria = (
        detalle.get(
            "convocatoria",
            {},
        )
        or {}
    )

    institucion = (
        detalle.get(
            "institucion",
            {},
        )
        or {}
    )

    productos = (
        detalle.get(
            "productos_solicitados",
            [],
        )
        or []
    )

    if not isinstance(
        productos,
        list,
    ):

        productos = []

    partes_productos = []

    productos_normalizados = []

    for producto in productos:

        if not isinstance(
            producto,
            dict,
        ):

            continue

        nombre_producto = (
            producto.get(
                "nombre"
            )
            or ""
        )

        descripcion_producto = (
            producto.get(
                "descripcion"
            )
            or ""
        )

        partes_productos.extend(
            [
                nombre_producto,
                descripcion_producto,
            ]
        )

        productos_normalizados.append(
            {
                "codigo_producto": (
                    producto.get(
                        "codigo_producto"
                    )
                ),
                "nombre": nombre_producto,
                "descripcion": (
                    descripcion_producto
                ),
                "cantidad": (
                    producto.get(
                        "cantidad"
                    )
                ),
                "unidad_medida": (
                    producto.get(
                        "unidad_medida"
                    )
                ),
            }
        )

    texto_productos = (
        " ".join(
            str(parte)
            for parte in partes_productos
            if parte
        )
        .strip()
    )

    nombre = (
        detalle.get(
            "nombre"
        )
        or item.get(
            "nombre",
            "Compra Ágil sin título",
        )
    )

    descripcion = (
        detalle.get(
            "descripcion"
        )
        or texto_productos
        or item.get(
            "nombre",
            "",
        )
    )

    presupuesto = (
        detalle.get(
            "presupuesto",
            {},
        )
        or {}
    )

    montos = (
        item.get(
            "montos",
            {},
        )
        or {}
    )

    monto = (
        presupuesto.get(
            "presupuesto_estimado"
        )
        or presupuesto.get(
            "monto_disponible"
        )
        or presupuesto.get(
            "monto_disponible_clp"
        )
        or montos.get(
            "monto_disponible"
        )
        or montos.get(
            "monto_disponible_clp"
        )
    )

    moneda = (
        presupuesto.get(
            "moneda"
        )
        or montos.get(
            "moneda"
        )
        or "CLP"
    )

    codigo = (
        detalle.get(
            "codigo"
        )
        or item.get(
            "codigo"
        )
    )

    fecha_cierre = (
        fechas.get(
            "fecha_cierre"
        )
        or _fecha_cierre_item_compra_agil(
            item
        )
    )

    return {
        "id": codigo,

        "nombre": nombre,

        "descripcion": descripcion,

        "productos_solicitados": (
            productos_normalizados
        ),

        "texto_productos": (
            texto_productos
        ),

        "region": (
            institucion.get(
                "nombre_region"
            )
            or "No Especificada"
        ),

        "region_codigo": (
            institucion.get(
                "region"
            )
        ),

        "organismo": (
            institucion.get(
                "organismo_comprador"
            )
            or "Organismo Desconocido"
        ),

        "rut_organismo": (
            institucion.get(
                "rut"
            )
        ),

        "unidad_compra": (
            institucion.get(
                "unidad_compra"
            )
        ),

        "fecha_publicacion": (
            fechas.get(
                "fecha_publicacion"
            )
            or item.get(
                "fecha_publicacion"
            )
            or "Sin fecha"
        ),

        "fecha_ultimo_cambio": (
            fechas.get(
                "fecha_ultimo_cambio"
            )
        ),

        "fecha_cierre": fecha_cierre,

        "link": (
            f"{ENDPOINT_COMPRA_AGIL}"
            f"?id={codigo}"
        ),

        "link_mercado_publico": (
            "https://buscador."
            "mercadopublico.cl/"
            "compra-agil"
        ),

        "tipo": "Compra Ágil",

        "monto_estimado": monto,

        "moneda": moneda,

        "monto_formateado": (
            _formatear_monto(
                monto,
                moneda,
            )
        ),

        "tipo_presupuesto": (
            presupuesto.get(
                "tipo_presupuesto"
            )
        ),

        "estado_convocatoria": (
            convocatoria.get(
                "estado_convocatoria"
            )
        ),

        "convocatoria": (
            convocatoria.get(
                "descripcion"
            )
        ),

        "fecha_cierre_primer_llamado": (
            convocatoria.get(
                "fecha_cierre_primer_llamado"
            )
        ),

        "fecha_cierre_segundo_llamado": (
            convocatoria.get(
                "fecha_cierre_segundo_llamado"
            )
        ),

        "requiere_garantia_seriedad": False,

        "requiere_garantia_fiel_cumplimiento": False,
    }


# ============================================================
# FAST CHECK COMPRA ÁGIL
# ============================================================

def simular_scraping_compra_agil_urgente():

    if not TICKET:

        print(
            "❌ Error: No se ha configurado "
            "CHILECOMPRA_TICKET para "
            "Compra Ágil v2."
        )

        return []

    headers = {
        "ticket": TICKET,
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64)"
        ),
        "Accept": "application/json",
    }

    ahora = (
        _ahora_chile_naive()
    )

    alertas_urgentes = []

    ids_procesados = set()

    consultas_ok = 0

    consultas_error = 0

    (
        busquedas_originales,
        busquedas_adicionales,
    ) = (
        _obtener_busquedas_compra_agil_induwork()
    )

    # ========================================================
    # COMBINAR Y DEDUPLICAR CONSULTAS API
    # ========================================================

    consultas = []

    claves_consulta = set()

    for tipo, lista in (
        (
            "ORIGINAL",
            busquedas_originales,
        ),
        (
            "ADICIONAL",
            busquedas_adicionales,
        ),
    ):

        for termino in lista:

            query_api = (
                _normalizar_query_compra_agil(
                    termino
                )
            )

            if not query_api:
                continue

            clave = (
                f"{tipo}:{query_api}"
            )

            if clave in claves_consulta:
                continue

            claves_consulta.add(
                clave
            )

            consultas.append(
                (
                    tipo,
                    termino,
                    query_api,
                )
            )

    # ========================================================
    # BÚSQUEDAS
    # ========================================================

    for tipo, termino, query_api in consultas:

        resultados = (
            _buscar_compra_agil_por_query(
                termino,
                tipo,
                headers,
            )
        )

        if resultados:

            consultas_ok += 1

        else:

            # No todo resultado vacío es un error.
            # Puede simplemente no haber coincidencias.
            pass

        # ====================================================
        # ITEMS ENCONTRADOS
        # ====================================================

        for item in resultados:

            codigo = item.get(
                "codigo"
            )

            if not codigo:
                continue

            if codigo in ids_procesados:

                continue

            ids_procesados.add(
                codigo
            )

            # =================================================
            # FECHA DE CIERRE DEL LISTADO
            # =================================================

            fecha_cierre_item = (
                _fecha_cierre_item_compra_agil(
                    item
                )
            )

            fecha_cierre_item_dt = (
                _parsear_fecha(
                    fecha_cierre_item
                )
            )

            # =================================================
            # SI YA ESTÁ CERRADA
            # =================================================

            if (
                fecha_cierre_item_dt
                and fecha_cierre_item_dt
                <= ahora
            ):

                continue

            # =================================================
            # SI TENEMOS FECHA Y NO ES URGENTE
            #
            # No pedimos detalle.
            #
            # Esto reduce muchísimo las consultas.
            # =================================================

            if fecha_cierre_item_dt:

                horas_restantes = (
                    (
                        fecha_cierre_item_dt
                        - ahora
                    ).total_seconds()
                    / 3600
                )

                if (
                    horas_restantes
                    > HORAS_URGENTE_COMPRA_AGIL
                ):

                    print(
                        f"⏭️ {codigo} "
                        f"cierra en "
                        f"{horas_restantes:.1f}h. "
                        "Fuera de ventana urgente."
                    )

                    continue

            # =================================================
            # DETALLE
            # =================================================

            detalle = (
                _obtener_detalle_compra_agil(
                    codigo,
                    headers,
                )
            )

            if not detalle:

                continue

            compra = (
                _mapear_compra_agil(
                    item,
                    detalle,
                )
            )

            fecha_cierre = (
                _parsear_fecha(
                    compra.get(
                        "fecha_cierre"
                    )
                )
            )

            if not fecha_cierre:

                print(
                    f"⚠️ Compra Ágil "
                    f"{codigo} sin fecha de "
                    "cierre interpretable."
                )

                continue

            horas_restantes = (
                (
                    fecha_cierre
                    - ahora
                ).total_seconds()
                / 3600
            )

            if (
                horas_restantes <= 0
                or horas_restantes
                > HORAS_URGENTE_COMPRA_AGIL
            ):

                continue

            # =================================================
            # CONTEXTO COMPLETO
            # =================================================

            texto = (
                f"{compra.get('nombre', '')} "
                f"{compra.get('descripcion', '')} "
                f"{compra.get('texto_productos', '')}"
            )

            # =================================================
            # FILTRO GENERAL
            # =================================================

            if not posible_relevante(
                texto
            ):

                continue

            # =================================================
            # CLASIFICACIÓN BASE
            # =================================================

            clasificacion = (
                evaluar_licitacion(
                    compra
                )
            )

            # =================================================
            # INDUWORK
            # =================================================

            if contiene_keyword_induwork(
                texto
            ):

                terminos_detectados = (
                    keywords_induwork_detectadas(
                        texto
                    )
                )

                print(
                    f"🎯 {codigo} "
                    "candidato Induwork "
                    f"| términos: "
                    f"{terminos_detectados}"
                )

                print(
                    "🤖 Consultando Gemini "
                    "para validar relevancia..."
                )

                clasificacion_ia = (
                    clasificar_con_gemini(
                        compra.get(
                            "nombre",
                            "",
                        ),
                        (
                            f"{compra.get('descripcion', '')} "
                            f"Productos: "
                            f"{compra.get('texto_productos', '')}"
                        ),
                    )
                )

                clasificacion[
                    "induwork"
                ] = (
                    clasificacion_ia[
                        "induwork"
                    ]
                )

                if (
                    clasificacion_ia[
                        "induwork"
                    ]
                ):

                    compra[
                        "validacion_ia_induwork"
                    ] = {
                        "motivo": (
                            clasificacion_ia.get(
                                "motivo",
                                "",
                            )
                        ),
                        "terminos_detectados": (
                            clasificacion_ia.get(
                                "terminos_detectados",
                                [],
                            )
                        ),
                    }

                    print(
                        "✅ Gemini APROBÓ "
                        f"{codigo} para "
                        "Induwork."
                    )

                    print(
                        f"   Cierra en: "
                        f"{horas_restantes:.1f}h"
                    )

                    print(
                        "   Monto: "
                        f"{compra.get('monto_formateado')}"
                    )

                else:

                    print(
                        "⛔ Gemini DESCARTÓ "
                        f"{codigo} para "
                        "Induwork."
                    )

            # =================================================
            # OTRAS CATEGORÍAS
            # =================================================

            if not (
                clasificacion[
                    "coimsa"
                ]
                or clasificacion[
                    "induwork"
                ]
                or clasificacion[
                    "especial"
                ]
            ):

                continue

            compra[
                "clasificacion"
            ] = clasificacion

            compra[
                "urgente"
            ] = True

            ahora_utc = (
                _ahora_utc_naive()
            )

            compra[
                "fecha_captura"
            ] = ahora_utc

            compra[
                "ultima_verificacion"
            ] = ahora_utc

            compra[
                "activa"
            ] = True

            # =================================================
            # BASE DE DATOS
            # =================================================

            if db is None:

                compra[
                    "fecha_primera_deteccion"
                ] = ahora_utc

                alertas_urgentes.append(
                    compra
                )

                continue

            existente = (
                db[
                    "licitaciones"
                ].find_one(
                    {
                        "id": codigo
                    }
                )
            )

            # =================================================
            # EXISTENTE
            # =================================================

            if existente:

                try:

                    campos_actuales = {
                        key: value
                        for key, value
                        in compra.items()
                        if key not in (
                            "id",
                            "fecha_captura",
                            "fecha_primera_deteccion",
                        )
                    }

                    db[
                        "licitaciones"
                    ].update_one(
                        {
                            "id": codigo
                        },
                        {
                            "$set":
                                campos_actuales
                        },
                    )

                except Exception as e:

                    print(
                        f"⚠️ No se pudo "
                        f"actualizar "
                        f"Compra Ágil "
                        f"{codigo}: {e}"
                    )

                print(
                    f"♻️ Compra Ágil "
                    f"{codigo} ya estaba "
                    "almacenada."
                )

                continue

            # =================================================
            # NUEVA
            # =================================================

            compra[
                "fecha_primera_deteccion"
            ] = ahora_utc

            try:

                db[
                    "licitaciones"
                ].insert_one(
                    compra.copy()
                )

                alertas_urgentes.append(
                    compra
                )

                print(
                    "✨ [COMPRA ÁGIL NUEVA] "
                    f"{codigo}"
                )

                print(
                    f"   Cierra en: "
                    f"{horas_restantes:.1f}h"
                )

                print(
                    f"   Monto: "
                    f"{compra.get('monto_formateado')}"
                )

                print(
                    f"   Nombre: "
                    f"{compra.get('nombre')}"
                )

            except Exception as e:

                print(
                    f"⚠️ No se pudo "
                    f"guardar {codigo}: {e}"
                )

    # ========================================================
    # RESUMEN
    # ========================================================

    print(
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "📊 FAST CHECK COMPRA ÁGIL"
    )

    print(
        f"🔎 IDs únicos encontrados: "
        f"{len(ids_procesados)}"
    )

    print(
        f"✅ Consultas con resultados: "
        f"{consultas_ok}"
    )

    print(
        f"🚨 Alertas urgentes nuevas: "
        f"{len(alertas_urgentes)}"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    return alertas_urgentes


# ============================================================
# ALMACENADAS
# ============================================================

def obtener_almacenadas(
    desde=None,
    hasta=None,
):

    if db is None:
        return []

    query = {}

    if desde or hasta:

        query[
            "fecha_captura"
        ] = {}

        if desde:

            query[
                "fecha_captura"
            ][
                "$gte"
            ] = desde

        if hasta:

            query[
                "fecha_captura"
            ][
                "$lte"
            ] = hasta

    documentos = list(
        db[
            "licitaciones"
        ].find(
            query
        ).sort(
            "fecha_captura",
            -1,
        )
    )

    for documento in documentos:

        documento.pop(
            "_id",
            None,
        )

    return documentos


# ============================================================
# AGRUPAR
# ============================================================

def agrupar_por_empresa(
    documentos,
):

    coimsa = [
        documento
        for documento in documentos
        if documento.get(
            "clasificacion",
            {},
        ).get(
            "coimsa"
        )
    ]

    induwork = [
        documento
        for documento in documentos
        if documento.get(
            "clasificacion",
            {},
        ).get(
            "induwork"
        )
    ]

    especial = [
        documento
        for documento in documentos
        if documento.get(
            "clasificacion",
            {},
        ).get(
            "especial"
        )
    ]

    return {
        "coimsa": coimsa,
        "induwork": induwork,
        "especial": especial,
    }


# ============================================================
# CONTAR POR TIPO
# ============================================================

def contar_por_tipo(
    documentos,
):

    licitaciones = sum(
        1
        for documento in documentos
        if documento.get(
            "tipo"
        )
        == "Licitación"
    )

    compras_agiles = sum(
        1
        for documento in documentos
        if documento.get(
            "tipo"
        )
        == "Compra Ágil"
    )

    return {
        "licitaciones": licitaciones,
        "compras_agiles": compras_agiles,
    }