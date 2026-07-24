import os
import datetime
from zoneinfo import ZoneInfo
import requests
from config.database import get_db
from modules.filters import evaluar_licitacion, posible_relevante


CL_TZ = ZoneInfo("America/Santiago")

db = get_db()
TICKET = os.getenv("CHILECOMPRA_TICKET")


BASE_URL_V1 = "https://api.mercadopublico.cl/servicios/v1/publico"

HEADERS_V1 = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

def convertir_fecha(fecha):
    if not fecha or fecha == "Sin fecha":
        return None
    formatos = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y"
    ]
    for formato in formatos:
        try:
            return datetime.datetime.strptime(
                fecha[:19],
                formato
            )
        except:
            continue
    return None

def _url_licitacion(codigo):
    return (
        "https://www.mercadopublico.cl/"
        "Procurement/Modules/RFB/"
        f"DetailsAcquisition.aspx?idlicitacion={codigo}"
    )

def obtener_licitaciones_api_real():

    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET.")
        return []

    ahora = datetime.datetime.now(CL_TZ)

    hoy_str = ahora.strftime("%d%m%Y")

    url = (
        f"{BASE_URL_V1}/licitaciones.json?"
        f"fecha={hoy_str}&ticket={TICKET}"
    )

    try:
        print(
            f"📡 Consultando listado de licitaciones "
            f"para la fecha: {hoy_str}..."
        )

        response = requests.get(
            url,
            headers=HEADERS_V1,
            timeout=15
        )

        if response.status_code == 200:

            listado = response.json().get(
                "Listado",
                []
            )

            print(
                f"🔎 {len(listado)} licitaciones recibidas."
            )
            return listado

        elif response.status_code == 404:
            ayer = ahora - datetime.timedelta(days=1)
            ayer_str = ayer.strftime("%d%m%Y")

            print(
                f"⚠️ Sin datos. "
                f"Consultando respaldo {ayer_str}"
            )

            url_ayer = (
                f"{BASE_URL_V1}/licitaciones.json?"
                f"fecha={ayer_str}&ticket={TICKET}"
            )

            res_ayer = requests.get(
                url_ayer,
                headers=HEADERS_V1,
                timeout=15
            )

            if res_ayer.status_code == 200:
                return res_ayer.json().get(
                    "Listado",
                    []
                )
            return []

        else:
            print(
                "⚠️ Error API:", response.status_code
            )
            return []

    except Exception as e:
        print(
            "❌ Error conexión Mercado Público:",e
        )
        return []

def obtener_detalle_licitacion(codigo):
    url = (
        f"{BASE_URL_V1}/licitaciones.json?"
        f"codigo={codigo}&ticket={TICKET}"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS_V1,
            timeout=15
        )

        if response.status_code != 200:
            return {}

        listado = response.json().get(
            "Listado",
            []
        )
        return listado[0] if listado else {}

    except Exception as e:
        print(
            f"⚠️ No se pudo obtener detalle {codigo}: {e}"
        )
        return {}

def _mapear_licitacion(lic_basico, detalle):

    codigo = (
        lic_basico.get("CodigoExterno")
        or detalle.get("CodigoExterno")
    )

    comprador = detalle.get(
        "Comprador",
        {}
    ) or {}

    fechas = detalle.get(
        "Fechas",
        {}
    ) or {}

    organismo = (
        comprador.get("NombreOrganismo")
        or detalle.get("NombreOrganismo")
        or detalle.get("Organismo")
        or "Organismo Desconocido"
    )

    region = (
        comprador.get("RegionUnidad")
        or detalle.get("Region")
        or "No Especificada"
    )

    descripcion = (
        detalle.get("Descripcion")
        or lic_basico.get("Descripcion")
        or detalle.get("Nombre")
        or lic_basico.get("Nombre","")
    )

    fecha_cierre = (
        fechas.get("FechaCierre")
        or detalle.get("FechaCierre")
        or lic_basico.get(
            "FechaCierre",
            "Sin fecha"
        )
    )

    fecha_apertura = (
        fechas.get("FechaPublicacion")
        or detalle.get("FechaPublicacion")
        or "Sin fecha"
    )

    monto = (
        detalle.get("MontoEstimado")
        or detalle.get("Monto")
        or detalle.get("Presupuesto")
        or "No informado"
    )

    garantia_seriedad = (
        detalle.get("GarantiaSeriedadOferta")
        or "No informado"
    )

    garantia_fiel_cumplimiento = (
        detalle.get("GarantiaFielCumplimiento")
        or "No informado"
    )

    estado = (
        detalle.get("Estado")
        or detalle.get("EstadoLicitacion")
        or ""
    )

    return {
        "id": codigo,
        "nombre": (
            detalle.get("Nombre")
            or lic_basico.get(
                "Nombre",
                "Licitación sin título"
            )
        ),
        "descripcion": descripcion,
        "organismo": organismo,
        "region": region,
        "fecha_apertura": fecha_apertura,
        "fecha_cierre": fecha_cierre,
        "monto": monto,
        "garantia_seriedad": garantia_seriedad,
        "garantia_fiel_cumplimiento":garantia_fiel_cumplimiento,
        "estado": estado,
        "link": _url_licitacion(codigo),
        "tipo": "Licitación"
    }


def procesar_y_guardar_licitaciones():
    licitaciones_crudas = obtener_licitaciones_api_real()
    nuevas_relevantes = []

    if not licitaciones_crudas:
        return nuevas_relevantes

    candidatas = [
        lic
        for lic in licitaciones_crudas
        if posible_relevante(
            lic.get("Nombre", "")
        )
    ]

    print(
        f"🔍 {len(candidatas)} candidatas encontradas."
    )

    for lic in candidatas:
        codigo = lic.get(
            "CodigoExterno"
        )

        if not codigo:
            continue

        detalle = obtener_detalle_licitacion(
            codigo
        )
        licitacion_mapeada = _mapear_licitacion(
            lic,
            detalle
        )

        # ======================================
        # FILTRO DE ESTADO
        # ======================================

        estado = (
            licitacion_mapeada
            .get("estado","")
            .lower()
        )
        estados_invalidos = [
            "adjudicada",
            "cerrada",
            "finalizada",
            "desierta",
            "revocada"
        ]

        if any(
            e in estado
            for e in estados_invalidos
        ):
            print(
                f"⛔ {codigo} descartada por estado: {estado}"
            )
            continue

        # ======================================
        # FILTRO FECHA CIERRE
        # ======================================

        fecha_cierre = convertir_fecha(
            licitacion_mapeada.get(
                "fecha_cierre"
            )
        )
        if fecha_cierre:
            if fecha_cierre < datetime.datetime.now():
                print(
                    f"⛔ {codigo} cerrada."
                )
                continue

        # ======================================
        # CLASIFICACION EMPRESA
        # ======================================

        clasificacion = evaluar_licitacion(
            licitacion_mapeada
        )
        if not (
            clasificacion["coimsa"]
            or clasificacion["induwork"]
            or clasificacion["especial"]
        ):
            continue
        licitacion_mapeada["clasificacion"] = (
            clasificacion
        )
        licitacion_mapeada[
            "fecha_captura"
        ] = datetime.datetime.utcnow()

        if db is not None:
            existe = db[
                "licitaciones"
            ].find_one(
                {
                    "id": codigo
                }
            )

            if existe is None:
                try:
                    db[
                        "licitaciones"
                    ].insert_one(
                        licitacion_mapeada.copy()
                    )
                    nuevas_relevantes.append(
                        licitacion_mapeada
                    )
                    print(
                        f"✨ Nueva licitación guardada {codigo}"
                    )
                except Exception as e:

                    print(
                        f"⚠️ Error guardando {codigo}: {e}"
                    )
        else:
            nuevas_relevantes.append(
                licitacion_mapeada
            )
    print(
        f"✅ {len(nuevas_relevantes)} oportunidades nuevas."
    )
    return nuevas_relevantes

def simular_scraping_compra_agil_urgente():
    if not TICKET:
        print(
            "❌ Falta CHILECOMPRA_TICKET"
        )
        return []

    BASE_URL_V2 = (
        "https://api2.mercadopublico.cl"
    )

    headers = {
        "ticket": TICKET,
        "User-Agent":"Mozilla/5.0"
    }

    params = {
        "estado":"proveedor_seleccionado",
        "tamano_pagina":50,
        "numero_pagina":1
    }
    alertas_urgentes = []

    try:
        response = requests.get(
            f"{BASE_URL_V2}/v2/compra-agil",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        payload = response.json().get(
            "payload",
            {}
        ) or {}
        items = payload.get(
            "items",
            []
        )
        print(
            f"🔎 Compras ágiles encontradas: {len(items)}"
        )

        for item in items:
            codigo_ca = item.get(
                "codigo"
            )

            if not codigo_ca:
                continue

            detalle_resp = requests.get(
                f"{BASE_URL_V2}/v2/compra-agil/{codigo_ca}",
                headers=headers,
                timeout=10
            )

            if detalle_resp.status_code != 200:
                continue

            detalle = detalle_resp.json().get(
                "payload",
                {}
            ) or {}
            orden_compra = detalle.get(
                "orden_compra",
                {}
            ) or {}
            id_oc = orden_compra.get(
                "id_orden_compra"
            )
            if id_oc is None:
                continue
            fechas = detalle.get(
                "fechas",
                {}
            ) or {}
            institucion = detalle.get(
                "institucion",
                {}
            ) or {}

            compra_mapeada = {
                "id":
                    codigo_ca,
                "nombre":
                    item.get(
                        "nombre",
                        "Compra Ágil sin título"
                    ),
                "descripcion":
                    detalle.get(
                        "descripcion",
                        ""
                    ),
                "region":
                    institucion.get(
                        "nombre_region",
                        "No Especificada"
                    ),
                "organismo":
                    institucion.get(
                        "organismo_comprador",
                        "Organismo Desconocido"
                    ),
                "fecha_apertura":
                    fechas.get(
                        "fecha_publicacion",
                        "Sin fecha"
                    ),
                "fecha_cierre":
                    fechas.get(
                        "fecha_cierre",
                        "Sin fecha"
                    ),
                "monto":
                    detalle.get(
                        "monto",
                        "No informado"
                    ),
                "garantia_seriedad":"No aplica",
                "garantia_fiel_cumplimiento":"No aplica",
                "estado":"Compra Ágil",
                "link":"https://buscador.mercadopublico.cl/compra-agil",
                "tipo":"Compra Ágil",
                "id_orden_compra":id_oc
            }

            clasificacion = evaluar_licitacion(
                compra_mapeada
            )

            if (
                clasificacion["coimsa"]
                or clasificacion["induwork"]
                or clasificacion["especial"]
            ):
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
                    if db[
                        "licitaciones"
                    ].find_one(
                        {
                            "id": codigo_ca
                        }
                    ) is None:
                        db[
                            "licitaciones"
                        ].insert_one(
                            compra_mapeada.copy()
                        )
                        alertas_urgentes.append(
                            compra_mapeada
                        )
        return alertas_urgentes

    except Exception as e:
        print(
            f"❌ Error Compra Ágil: {e}"
        )
        return []


# ============================================================
#  CONSULTAS SOBRE LO YA ALMACENADO (para reportes y reenvíos)
# ============================================================

# ============================================================
# CONSULTAS SOBRE LO YA ALMACENADO
# ============================================================


def obtener_almacenadas(desde=None, hasta=None):
    if db is None:
        return []

    query = {}
    if desde or hasta:
        query["fecha_captura"] = {}

        if desde:
            query["fecha_captura"]["$gte"] = desde

        if hasta:
            query["fecha_captura"]["$lte"] = hasta

    documentos = list(
        db["licitaciones"]
        .find(query)
        .sort(
            [
                (
                    "fecha_apertura",
                    -1
                ),
                (
                    "fecha_captura",
                    -1
                )
            ]
        )
    )

    for documento in documentos:
        documento.pop(
            "_id", None
        )
    return documentos

def agrupar_por_empresa(documentos):
    coimsa = [
        d for d in documentos
        if d.get(
            "clasificacion",
            {}
        ).get(
            "coimsa"
        )
    ]

    induwork = [
        d for d in documentos
        if d.get(
            "clasificacion",
            {}
        ).get(
            "induwork"
        )
    ]

    especial = [
        d for d in documentos
        if d.get(
            "clasificacion",
            {}
        ).get(
            "especial"
        )
    ]

    return {
        "coimsa":coimsa,
        "induwork":induwork,
        "especial":especial
    }

def contar_por_tipo(documentos):

    licitaciones = sum(1
        for d in documentos
        if d.get(
            "tipo"
        ) == "Licitación"
    )

    compras_agiles = sum(1
        for d in documentos
        if d.get(
            "tipo"
        ) == "Compra Ágil"
    )

    return {
        "licitaciones":licitaciones,
        "compras_agiles":compras_agiles
    }

def agrupar_por_empresa_con_override(
    documentos,
    solo_categoria=None
):

    resultado = {
        "coimsa": [],
        "induwork": [],
        "especial": []
    }

    for d in documentos:
        clasif = d.get(
            "clasificacion",
            {}
        )

        if clasif.get(
            "coimsa"
        ):
            resultado[
                "coimsa"
            ].append(d)

        elif clasif.get(
            "induwork"
        ):

            resultado[
                "induwork"
            ].append(d)

        elif clasif.get(
            "especial"
        ):
            resultado[
                "especial"
            ].append(d)

    if (
        solo_categoria
        and solo_categoria in resultado
    ):
        return {
            solo_categoria:
                resultado[
                    solo_categoria
                ]
        }
    return resultado