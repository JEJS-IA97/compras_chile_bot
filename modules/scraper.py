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


def _url_licitacion(codigo):
    return f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={codigo}"


def obtener_licitaciones_api_real():
    """
    Consulta la API v1 por fecha (listado BÁSICO del día: nombre, código, fecha de
    cierre). Según la documentación oficial, esta consulta NO trae organismo,
    descripción completa ni link — para eso hay que pedir el detalle por código.
    """
    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET.")
        return []

    ahora = datetime.datetime.now(CL_TZ)
    hoy_str = ahora.strftime("%d%m%Y")

    url = f"{BASE_URL_V1}/licitaciones.json?fecha={hoy_str}&ticket={TICKET}"

    try:
        print(f"📡 Consultando listado de licitaciones para la fecha: {hoy_str}...")
        response = requests.get(url, headers=HEADERS_V1, timeout=15)

        if response.status_code == 200:
            listado = response.json().get("Listado", [])
            print(f"🔎 {len(listado)} licitaciones recibidas para {hoy_str}.")
            return listado

        elif response.status_code == 404:
            ayer = ahora - datetime.timedelta(days=1)
            ayer_str = ayer.strftime("%d%m%Y")
            print(f"⚠️ Fecha de hoy sin datos (404). Consultando respaldo de ayer: {ayer_str}...")
            url_ayer = f"{BASE_URL_V1}/licitaciones.json?fecha={ayer_str}&ticket={TICKET}"
            res_ayer = requests.get(url_ayer, headers=HEADERS_V1, timeout=15)
            if res_ayer.status_code == 200:
                listado = res_ayer.json().get("Listado", [])
                print(f"🔎 {len(listado)} licitaciones recibidas para {ayer_str} (respaldo).")
                return listado
            print(f"⚠️ Respaldo falló con código: {res_ayer.status_code}")
            return []
        else:
            print(f"⚠️ Error inesperado en API: Status {response.status_code} - {response.text[:300]}")
            return []

    except Exception as e:
        print(f"❌ Error de conexión con Mercado Público: {e}")
        return []


def obtener_detalle_licitacion(codigo):
    """
    Consulta el detalle COMPLETO de una licitación por su código. Aquí sí viene
    el organismo, la descripción completa, la región, etc.
    """
    url = f"{BASE_URL_V1}/licitaciones.json?codigo={codigo}&ticket={TICKET}"
    try:
        response = requests.get(url, headers=HEADERS_V1, timeout=15)
        if response.status_code != 200:
            return {}
        listado = response.json().get("Listado", [])
        return listado[0] if listado else {}
    except Exception as e:
        print(f"⚠️ No se pudo obtener el detalle de {codigo}: {e}")
        return {}


def _mapear_licitacion(lic_basico, detalle):
    """
    Combina el listado básico (por fecha) con el detalle completo (por código).
    Usa varias claves candidatas por campo porque distintas versiones de la API
    han usado nombres ligeramente distintos para el mismo dato.
    """
    codigo = lic_basico.get("CodigoExterno") or detalle.get("CodigoExterno")
    comprador = detalle.get("Comprador", {}) or {}
    fechas = detalle.get("Fechas", {}) or {}

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
        or lic_basico.get("Nombre", "")
    )
    fecha_cierre = (
        fechas.get("FechaCierre")
        or detalle.get("FechaCierre")
        or lic_basico.get("FechaCierre", "Sin fecha")
    )
    fecha_publicacion = (
        fechas.get("FechaPublicacion")
        or detalle.get("FechaPublicacion")
        or "Sin fecha"
    )

    # Debug puntual: si seguimos sin organismo real, deja rastro en el log
    # para poder ajustar las claves con datos reales de la API.
    if organismo == "Organismo Desconocido" and detalle:
        print(f"🩺 DEBUG organismo desconocido para {codigo}. Claves del detalle: {list(detalle.keys())}")

    return {
        "id": codigo,
        "nombre": detalle.get("Nombre") or lic_basico.get("Nombre", "Licitación sin título"),
        "descripcion": descripcion,
        "region": region,
        "organismo": organismo,
        "fecha_cierre": fecha_cierre,
        "fecha_publicacion": fecha_publicacion,
        "link": _url_licitacion(codigo),
        "tipo": "Licitación",
    }


def procesar_y_guardar_licitaciones():
    """
    1) Trae el listado básico del día.
    2) Prefiltra por nombre (barato) para no gastar cuota de API en detalle.
    3) Para cada candidata, pide el detalle completo (organismo, descripción, etc).
    4) Clasifica con el texto completo (nombre + descripción reales).
    5) Guarda en Mongo SOLO si matchea alguna categoría (Coimsa/Induwork/Especial).
    """
    licitaciones_crudas = obtener_licitaciones_api_real()
    nuevas_relevantes = []

    if not licitaciones_crudas:
        return nuevas_relevantes

    candidatas = [lic for lic in licitaciones_crudas if posible_relevante(lic.get("Nombre", ""))]
    print(f"🔍 {len(candidatas)} de {len(licitaciones_crudas)} pasaron el prefiltro por nombre. Pidiendo detalle...")

    for lic in candidatas:
        codigo = lic.get("CodigoExterno")
        if not codigo:
            continue

        detalle = obtener_detalle_licitacion(codigo)
        licitacion_mapeada = _mapear_licitacion(lic, detalle)

        clasificacion = evaluar_licitacion(licitacion_mapeada)

        if not (clasificacion["coimsa"] or clasificacion["induwork"] or clasificacion["especial"]):
            continue  # no matchea de verdad con el texto completo -> no se guarda, no se envía

        licitacion_mapeada["clasificacion"] = clasificacion
        licitacion_mapeada["fecha_captura"] = datetime.datetime.utcnow()

        if db is not None:
            if db["licitaciones"].find_one({"id": codigo}) is None:
                try:
                    db["licitaciones"].insert_one(licitacion_mapeada.copy())
                    nuevas_relevantes.append(licitacion_mapeada)
                    print(f"✨ [Licitación] Nueva detectada y guardada: {codigo}")
                except Exception as e:
                    print(f"⚠️ No se pudo guardar {codigo}: {e}")
        else:
            nuevas_relevantes.append(licitacion_mapeada)

    print(f"✅ {len(nuevas_relevantes)} licitaciones nuevas y relevantes encontradas.")
    return nuevas_relevantes


def simular_scraping_compra_agil_urgente():
    """
    Monitoreo rápido (cada 30 minutos). Recorre TODAS las páginas de procesos
    en estado 'proveedor_seleccionado' y valida si ya se emitió la Orden de Compra.
    """
    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET para Compra Ágil v2.")
        return []

    BASE_URL_V2 = "https://api2.mercadopublico.cl"
    headers = {"ticket": TICKET, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    params = {"estado": "proveedor_seleccionado", "tamano_pagina": 50, "numero_pagina": 1}

    alertas_urgentes = []
    MAX_PAGINAS_SEGURIDAD = 20

    try:
        todos_los_items = []
        while True:
            print(f"⏱️ Consultando Compra Ágil v2 - página {params['numero_pagina']}...")
            response = requests.get(f"{BASE_URL_V2}/v2/compra-agil", headers=headers, params=params, timeout=15)
            response.raise_for_status()

            payload = response.json().get("payload", {}) or {}
            items = payload.get("items", [])
            paginacion = payload.get("paginacion", {}) or {}
            todos_los_items.extend(items)

            total_paginas = paginacion.get("total_paginas", 1)
            numero_pagina = paginacion.get("numero_pagina", params["numero_pagina"])
            if numero_pagina >= total_paginas or numero_pagina >= MAX_PAGINAS_SEGURIDAD:
                break
            params["numero_pagina"] += 1

        print(f"🔎 Analizando {len(todos_los_items)} transacciones de Compra Ágil (proveedor_seleccionado)...")

        for item in todos_los_items:
            codigo_ca = item.get("codigo")
            if not codigo_ca:
                continue

            det_resp = requests.get(f"{BASE_URL_V2}/v2/compra-agil/{codigo_ca}", headers=headers, timeout=10)
            if det_resp.status_code != 200:
                continue

            detalle = det_resp.json().get("payload", {}) or {}
            orden_compra = detalle.get("orden_compra", {}) or {}
            id_oc = orden_compra.get("id_orden_compra")

            if id_oc is not None:
                compra_mapeada = {
                    "id": codigo_ca,
                    "nombre": item.get("nombre", "Compra Ágil sin título"),
                    "descripcion": detalle.get("descripcion", item.get("nombre", "")),
                    "region": (detalle.get("institucion", {}) or {}).get("nombre_region", "No Especificada"),
                    "organismo": (detalle.get("institucion", {}) or {}).get("organismo_comprador", "Organismo Desconocido"),
                    "fecha_cierre": (detalle.get("fechas", {}) or {}).get("fecha_cierre", "Finalizado"),
                    "link": "https://buscador.mercadopublico.cl/compra-agil",
                    "tipo": "Compra Ágil",
                    "id_orden_compra": id_oc
                }

                clasificacion = evaluar_licitacion(compra_mapeada)

                if clasificacion["coimsa"] or clasificacion["induwork"] or clasificacion["especial"]:
                    compra_mapeada["clasificacion"] = clasificacion
                    compra_mapeada["urgente"] = True
                    compra_mapeada["fecha_captura"] = datetime.datetime.utcnow()

                    if db is not None:
                        if db["licitaciones"].find_one({"id": codigo_ca}) is None:
                            try:
                                db["licitaciones"].insert_one(compra_mapeada.copy())
                                alertas_urgentes.append(compra_mapeada)
                                print(f"✨ [Compra Ágil] OC Detectada y Guardada: {codigo_ca}")
                            except Exception as e:
                                print(f"⚠️ No se pudo guardar {codigo_ca}: {e}")
                    else:
                        alertas_urgentes.append(compra_mapeada)

        return alertas_urgentes

    except Exception as e:
        print(f"❌ Error al conectar con la API v2 de Compra Ágil: {e}")
        return []


# ============================================================
#  CONSULTAS SOBRE LO YA ALMACENADO (para reportes y reenvíos)
# ============================================================

def obtener_almacenadas(desde=None, hasta=None):
    """
    Devuelve todo lo guardado en Mongo entre 'desde' y 'hasta' (datetime UTC naive,
    igual formato que fecha_captura). Si no se pasan fechas, devuelve TODO.
    """
    if db is None:
        return []

    query = {}
    if desde or hasta:
        query["fecha_captura"] = {}
        if desde:
            query["fecha_captura"]["$gte"] = desde
        if hasta:
            query["fecha_captura"]["$lte"] = hasta

    documentos = list(db["licitaciones"].find(query).sort("fecha_captura", -1))
    for d in documentos:
        d.pop("_id", None)  # nunca exponer ObjectId hacia afuera de este módulo
    return documentos


def agrupar_por_empresa(documentos):
    """Separa una lista de licitaciones/compras ágiles en coimsa / induwork / especial."""
    coimsa = [d for d in documentos if d.get("clasificacion", {}).get("coimsa")]
    induwork = [d for d in documentos if d.get("clasificacion", {}).get("induwork")]
    especial = [d for d in documentos if d.get("clasificacion", {}).get("especial")]
    return {"coimsa": coimsa, "induwork": induwork, "especial": especial}


def contar_por_tipo(documentos):
    """Cuenta cuántas son 'Licitación' vs 'Compra Ágil' dentro de una lista."""
    licitaciones = sum(1 for d in documentos if d.get("tipo") == "Licitación")
    compras_agiles = sum(1 for d in documentos if d.get("tipo") == "Compra Ágil")
    return {"licitaciones": licitaciones, "compras_agiles": compras_agiles}

def agrupar_por_empresa_con_override(documentos, solo_categoria=None):
    """
    Separa una lista de documentos en coimsa / induwork / especial.
    Si solo_categoria no es None, devuelve solo esa categoría.
    """
    resultado = {"coimsa": [], "induwork": [], "especial": []}
    for d in documentos:
        clasif = d.get("clasificacion", {})
        if clasif.get("coimsa"):
            resultado["coimsa"].append(d)
        elif clasif.get("induwork"):
            resultado["induwork"].append(d)
        elif clasif.get("especial"):
            resultado["especial"].append(d)
    
    if solo_categoria and solo_categoria in resultado:
        return {solo_categoria: resultado[solo_categoria]}
    return resultado