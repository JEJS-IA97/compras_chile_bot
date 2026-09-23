# modules/scraper.py

import os
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
from modules.ai_classifier import clasificar_con_gemini


CL_TZ = ZoneInfo("America/Santiago")

db = get_db()
TICKET = os.getenv("CHILECOMPRA_TICKET")

BASE_URL_V1 = (
    "https://api.mercadopublico.cl/servicios/v1/publico"
)

HEADERS_V1 = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64)"
    ),
    "Accept": "application/json",
}

HORAS_URGENTE_COMPRA_AGIL = 72

# ============================================================
# CONTROL DE PETICIONES
# ============================================================

# Tiempo mínimo entre consultas de detalle.
# Evita disparar demasiadas solicitudes consecutivas.
DETAIL_REQUEST_DELAY = 1.0

# Cantidad máxima de reintentos cuando Mercado Público
# responde HTTP 429.
MAX_RETRIES_429 = 3

# Esperas progresivas ante 429.
BACKOFF_429 = (
    3,
    8,
    15,
)


def _url_licitacion(codigo):
    return (
        "https://www.mercadopublico.cl/"
        "Procurement/Modules/RFB/"
        f"DetailsAcquisition.aspx?idlicitacion={codigo}"
    )


def _parsear_fecha(valor):
    if not valor:
        return None

    if isinstance(
        valor,
        datetime.datetime,
    ):
        return valor.replace(
            tzinfo=None
        )

    if not isinstance(valor, str):
        return None

    formatos = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
    )

    for fmt in formatos:
        try:
            return datetime.datetime.strptime(
                valor,
                fmt,
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
            ).replace(tzinfo=None)

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
            .replace(",", ".")
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


def _es_fecha_de_hoy_chile(
    valor,
):
    """
    Determina si una fecha UTC/naive corresponde
    al día actual en Chile.
    """

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


def _esperar_entre_detalles():
    """
    Pausa entre consultas de detalle para
    reducir riesgo de HTTP 429.
    """
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
    """
    Realiza una solicitud GET y reintenta cuando
    Mercado Público responde 429.

    Si es una consulta de detalle, mantiene una pausa
    antes de cada solicitud para evitar ráfagas.
    """

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
                f"⚠️ Timeout. Reintentando "
                f"en {espera}s..."
            )

            time.sleep(espera)
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
            f"HTTP 429. "
            f"Reintento {intento + 1}/"
            f"{MAX_RETRIES_429} "
            f"en {espera}s..."
        )

        time.sleep(espera)

    return response


def obtener_licitaciones_api_real():
    """
    Obtiene TODAS las licitaciones actualmente activas.
    """

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
                .get("Listado", [])
            )

            print(
                f"🔎 {len(listado)} "
                "licitaciones activas "
                "recibidas desde "
                "Mercado Público."
            )

            return listado

        print(
            f"⚠️ Error Mercado Público: "
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


def obtener_detalle_licitacion(
    codigo,
):
    """
    Obtiene el detalle de una licitación
    por código.

    Incluye control de HTTP 429.
    """

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
                f"respondió HTTP "
                f"{response.status_code}"
            )

            return {}

        listado = (
            response.json()
            .get("Listado", [])
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


def _mapear_licitacion(
    lic_basico,
    detalle,
):
    """
    Une los datos básicos de la consulta de activas
    con el detalle completo de la licitación.
    """

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

    monto_estimado = (
        detalle.get(
            "MontoEstimado"
        )
        or detalle.get(
            "Monto"
        )
        or lic_basico.get(
            "MontoEstimado"
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
        "requiere_garantia_seriedad": None,
        "monto_garantia_seriedad": None,
        "requiere_garantia_fiel_cumplimiento": None,
        "monto_garantia_fiel_cumplimiento": None,
    }


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
    licitacion["clasificacion"] = (
        clasificacion
    )

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
    """
    Actualiza los datos actuales de una licitación
    sin modificar su fecha de primera detección.
    """

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

    if existente.get(
        "validacion_ia_induwork"
    ):
        licitacion_actualizada[
            "validacion_ia_induwork"
        ] = existente[
            "validacion_ia_induwork"
        ]

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

            db[
                "licitaciones"
            ].update_one(
                {
                    "id": codigo
                },
                {
                    "$set": datos_actualizados
                },
            )

        except Exception as e:

            print(
                f"⚠️ No se pudo actualizar "
                f"{codigo}: {e}"
            )

    return licitacion_actualizada


def procesar_y_guardar_licitaciones():
    """
    Busca todas las licitaciones activas.

    Flujo:

    1. Obtiene todas las activas.
    2. Filtra las candidatas por keywords.
    3. Obtiene detalle de cada candidata.
    4. Valida Induwork con Gemini.
    5. Si es nueva, la guarda y la retorna como nueva.
    6. Si ya existía, actualiza sus datos pero no la
       vuelve a considerar nueva.
    7. Devuelve nuevas + activas anteriores.
    """

    licitaciones_activas = (
        obtener_licitaciones_api_real()
    )

    resultado = {
        "nuevas": [],
        "activas_anteriores": [],
    }

    if not licitaciones_activas:
        return resultado

    # ========================================================
    # PREFILTRO
    # ========================================================

    candidatas = []

    for lic in licitaciones_activas:

        texto_basico = (
            f"{lic.get('Nombre', '')} "
            f"{lic.get('Descripcion', '')}"
        )

        if posible_relevante(
            texto_basico
        ):
            candidatas.append(lic)

    print(
        f"🔍 {len(candidatas)} candidatas "
        f"de {len(licitaciones_activas)} "
        "licitaciones activas."
    )

    ahora_chile = (
        datetime.datetime.now(
            CL_TZ
        ).replace(
            tzinfo=None
        )
    )

    ahora_utc = _ahora_utc_naive()

    # ========================================================
    # PROCESAMIENTO DE CANDIDATAS
    # ========================================================

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
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            f"🔎 Candidata "
            f"{indice}/{len(candidatas)}: "
            f"{codigo}"
        )

        # ====================================================
        # DETALLE
        # ====================================================

        detalle = (
            obtener_detalle_licitacion(
                codigo
            )
        )

        if not detalle:

            print(
                f"⚠️ No se pudo obtener "
                f"detalle de {codigo}, "
                "se omite."
            )

            continue

        licitacion_mapeada = (
            _mapear_licitacion(
                lic,
                detalle,
            )
        )

        # ====================================================
        # FECHA DE CIERRE
        # ====================================================

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
                f"({licitacion_mapeada['fecha_cierre']}), "
                "se descarta."
            )

            continue

        # ====================================================
        # CLASIFICACIÓN BASE
        # ====================================================

        clasificacion = (
            evaluar_licitacion(
                licitacion_mapeada
            )
        )

        texto = (
            f"{licitacion_mapeada.get('nombre', '')} "
            f"{licitacion_mapeada.get('descripcion', '')}"
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
                f"🎯 Coincidencia Induwork: "
                f"{terminos}"
            )

            debe_consultar_gemini = True

            # ------------------------------------------------
            # Si ya fue validada anteriormente por Gemini,
            # NO volvemos a gastar una consulta de IA.
            # ------------------------------------------------

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
                        "♻️ Ya validada previamente "
                        "por Gemini. "
                        "No se vuelve a consultar IA."
                    )

            # ------------------------------------------------
            # Gemini
            # ------------------------------------------------

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
                        licitacion_mapeada.get(
                            "descripcion",
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

        # ====================================================
        # NINGUNA CATEGORÍA
        # ====================================================

        if not (
            clasificacion["coimsa"]
            or clasificacion["induwork"]
            or clasificacion["especial"]
        ):

            print(
                f"⏭️ {codigo} no clasifica "
                "para ninguna categoría."
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

        # ----------------------------------------------------
        # Si se detectó HOY:
        # nueva de hoy
        # ----------------------------------------------------

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
                "ya estaba almacenada, "
                "pero su primera detección "
                "corresponde a hoy."
            )

        # ----------------------------------------------------
        # Si fue detectada anteriormente:
        # activa anterior
        # ----------------------------------------------------

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

    # ========================================================
    # RESUMEN
    # ========================================================

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
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    return resultado


def simular_scraping_compra_agil_urgente():
    """
    Busca Compras Ágiles publicadas que cierren
    dentro de las próximas 72 horas.
    """

    if not TICKET:
        print(
            "❌ Error: No se ha configurado "
            "CHILECOMPRA_TICKET para "
            "Compra Ágil v2."
        )
        return []

    BASE_URL_V2 = (
        "https://api2.mercadopublico.cl"
    )

    headers = {
        "ticket": TICKET,
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64)"
        ),
    }

    params = {
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    }

    alertas_urgentes = []

    MAX_PAGINAS_SEGURIDAD = 20

    ahora = (
        datetime.datetime.now(
            CL_TZ
        ).replace(
            tzinfo=None
        )
    )

    try:

        todos_los_items = []

        while True:

            print(
                "⏱️ Consultando Compra Ágil "
                "v2 (publicada) - página "
                f"{params['numero_pagina']}..."
            )

            try:

                response = requests.get(
                    f"{BASE_URL_V2}/v2/compra-agil",
                    headers=headers,
                    params=params,
                    timeout=45,
                )

                response.raise_for_status()

            except requests.exceptions.Timeout:
                print(
                    "⚠️ Timeout consultando "
                    "Compra Ágil."
                )

                break

            payload = (
                response.json()
                .get("payload", {})
                or {}
            )

            items = payload.get(
                "items",
                []
            )

            paginacion = (
                payload.get(
                    "paginacion",
                    {},
                )
                or {}
            )

            todos_los_items.extend(
                items
            )

            total_paginas = (
                paginacion.get(
                    "total_paginas",
                    1,
                )
            )

            numero_pagina = (
                paginacion.get(
                    "numero_pagina",
                    params[
                        "numero_pagina"
                    ],
                )
            )

            if (
                numero_pagina
                >= total_paginas
                or numero_pagina
                >= MAX_PAGINAS_SEGURIDAD
            ):
                break

            params[
                "numero_pagina"
            ] += 1

            time.sleep(1)

        print(
            f"🔎 Analizando "
            f"{len(todos_los_items)} "
            "Compras Ágiles publicadas."
        )

        for item in todos_los_items:

            codigo_ca = item.get(
                "codigo"
            )

            if not codigo_ca:
                continue

            try:

                det_resp = requests.get(
                    f"{BASE_URL_V2}/v2/compra-agil/"
                    f"{codigo_ca}",
                    headers=headers,
                    timeout=30,
                )

            except requests.exceptions.Timeout:
                print(
                    f"⚠️ Timeout obteniendo "
                    f"Compra Ágil {codigo_ca}."
                )
                continue

            if det_resp.status_code != 200:
                continue

            detalle = (
                det_resp.json()
                .get("payload", {})
                or {}
            )

            fechas = (
                detalle.get(
                    "fechas",
                    {},
                )
                or {}
            )

            fecha_cierre_str = (
                fechas.get(
                    "fecha_cierre"
                )
                or item.get(
                    "fecha_cierre"
                )
            )

            fecha_cierre_dt = (
                _parsear_fecha(
                    fecha_cierre_str
                )
            )

            if not fecha_cierre_dt:
                continue

            horas_restantes = (
                (
                    fecha_cierre_dt
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

            compra_mapeada = {
                "id": codigo_ca,
                "nombre": item.get(
                    "nombre",
                    "Compra Ágil sin título",
                ),
                "descripcion": (
                    detalle.get(
                        "descripcion"
                    )
                    or item.get(
                        "nombre",
                        "",
                    )
                ),
                "region": (
                    detalle.get(
                        "institucion",
                        {},
                    )
                    or {}
                ).get(
                    "nombre_region",
                    "No Especificada",
                ),
                "organismo": (
                    detalle.get(
                        "institucion",
                        {},
                    )
                    or {}
                ).get(
                    "organismo_comprador",
                    "Organismo Desconocido",
                ),
                "fecha_cierre": fecha_cierre_str,
                "link": (
                    "https://buscador."
                    "mercadopublico.cl/"
                    "compra-agil"
                ),
                "tipo": "Compra Ágil",
                "monto_estimado": (
                    detalle.get(
                        "monto_estimado"
                    )
                    or item.get(
                        "monto_estimado"
                    )
                ),
                "moneda": detalle.get(
                    "moneda",
                    "CLP",
                ),
                "monto_formateado": (
                    _formatear_monto(
                        detalle.get(
                            "monto_estimado"
                        )
                        or item.get(
                            "monto_estimado"
                        ),
                        detalle.get(
                            "moneda",
                            "CLP",
                        ),
                    )
                ),
                "requiere_garantia_seriedad": False,
                "requiere_garantia_fiel_cumplimiento": False,
            }

            clasificacion = (
                evaluar_licitacion(
                    compra_mapeada
                )
            )

            texto = (
                f"{compra_mapeada.get('nombre', '')} "
                f"{compra_mapeada.get('descripcion', '')}"
            )

            if contiene_keyword_induwork(
                texto
            ):

                terminos = (
                    keywords_induwork_detectadas(
                        texto
                    )
                )

                print(
                    f"🎯 Compra Ágil "
                    f"{codigo_ca} "
                    f"coincide con Induwork "
                    f"| términos: {terminos}"
                )

                clasificacion_ia = (
                    clasificar_con_gemini(
                        compra_mapeada.get(
                            "nombre",
                            "",
                        ),
                        compra_mapeada.get(
                            "descripcion",
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

                    compra_mapeada[
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
                        f"✅ Gemini aprobó "
                        f"Compra Ágil "
                        f"{codigo_ca}"
                    )

                else:

                    print(
                        f"⛔ Gemini descartó "
                        f"Compra Ágil "
                        f"{codigo_ca}"
                    )

            if not (
                clasificacion["coimsa"]
                or clasificacion["induwork"]
                or clasificacion["especial"]
            ):
                continue

            compra_mapeada[
                "clasificacion"
            ] = clasificacion

            compra_mapeada[
                "urgente"
            ] = True

            compra_mapeada[
                "fecha_captura"
            ] = datetime.datetime.utcnow()

            if db is not None:

                existente = (
                    db[
                        "licitaciones"
                    ].find_one(
                        {
                            "id": codigo_ca
                        }
                    )
                )

                if existente:
                    continue

                try:

                    db[
                        "licitaciones"
                    ].insert_one(
                        compra_mapeada.copy()
                    )

                    alertas_urgentes.append(
                        compra_mapeada
                    )

                    print(
                        f"✨ [Compra Ágil] "
                        f"Cierra en "
                        f"{horas_restantes:.1f}h "
                        f"— Guardada: "
                        f"{codigo_ca}"
                    )

                except Exception as e:

                    print(
                        f"⚠️ No se pudo guardar "
                        f"{codigo_ca}: {e}"
                    )

            else:

                alertas_urgentes.append(
                    compra_mapeada
                )

            time.sleep(0.5)

        return alertas_urgentes

    except Exception as e:

        print(
            "❌ Error al conectar con "
            f"la API v2 de Compra Ágil: {e}"
        )

        return []


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
            ]["$gte"] = desde

        if hasta:
            query[
                "fecha_captura"
            ]["$lte"] = hasta

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


def agrupar_por_empresa(
    documentos,
):
    coimsa = [
        d
        for d in documentos
        if d.get(
            "clasificacion",
            {},
        ).get(
            "coimsa"
        )
    ]

    induwork = [
        d
        for d in documentos
        if d.get(
            "clasificacion",
            {},
        ).get(
            "induwork"
        )
    ]

    especial = [
        d
        for d in documentos
        if d.get(
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


def contar_por_tipo(
    documentos,
):
    licitaciones = sum(
        1
        for d in documentos
        if d.get(
            "tipo"
        )
        == "Licitación"
    )

    compras_agiles = sum(
        1
        for d in documentos
        if d.get(
            "tipo"
        )
        == "Compra Ágil"
    )

    return {
        "licitaciones": licitaciones,
        "compras_agiles": compras_agiles,
    }


def limpiar_licitaciones_no_clasificadas():
    """
    Elimina de Mongo las licitaciones que ya no
    clasifican bajo los filtros actuales.
    """

    if db is None:
        print(
            "❌ No hay conexión "
            "a la base de datos."
        )
        return

    todas = list(
        db.licitaciones.find(
            {},
            {
                "_id": 1,
                "id": 1,
                "nombre": 1,
                "descripcion": 1,
                "region": 1,
            },
        )
    )

    eliminados = 0

    for doc in todas:

        lic_temp = {
            "nombre": doc.get(
                "nombre",
                "",
            ),
            "descripcion": doc.get(
                "descripcion",
                "",
            ),
            "region": doc.get(
                "region",
                "",
            ),
        }

        clasif = evaluar_licitacion(
            lic_temp
        )

        if not (
            clasif["coimsa"]
            or clasif["induwork"]
            or clasif["especial"]
        ):

            db.licitaciones.delete_one(
                {
                    "_id": doc["_id"]
                }
            )

            eliminados += 1

            print(
                f"🗑️ Eliminada licitación "
                f"{doc.get('id', 'sin_id')} "
                "porque ya no clasifica."
            )

    print(
        f"✅ Limpieza completada: "
        f"{eliminados} registros eliminados."
    )