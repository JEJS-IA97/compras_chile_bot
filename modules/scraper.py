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

# Ventana de "cierre pronto" para las alertas urgentes de Compra Ágil
HORAS_URGENTE_COMPRA_AGIL = 72


def _url_licitacion(codigo):
    return f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={codigo}"


def _parsear_fecha(valor):
    """Convierte strings tipo '2026-07-24T17:30:00' a datetime naive (hora Chile, sin tz)."""
    if not valor or not isinstance(valor, str):
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(valor, fmt)
        except ValueError:
            continue
    return None


def _formatear_monto(monto, moneda):
    if monto in (None, "", 0):
        return "No especificado"
    try:
        return f"{moneda or 'CLP'} {float(monto):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return f"{moneda or ''} {monto}".strip()


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
    el organismo, la descripción completa, la región, montos y garantías.
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

    # --- Monto estimado ---
    monto_estimado = (
        detalle.get("MontoEstimado")
        or detalle.get("Monto")
        or lic_basico.get("MontoEstimado")
    )
    moneda = detalle.get("Moneda") or lic_basico.get("Moneda") or "CLP"

    # --- Garantías (claves candidatas; se ajustan según lo que confirme el log de debug) ---
    garantias = detalle.get("Garantias", {}) or {}
    requiere_garantia_seriedad = bool(
        garantias.get("MontoGarantiaSeriedad")
        or garantias.get("RequiereGarantiaSeriedad")
        or detalle.get("RequiereGarantiaSeriedad")
    )
    monto_garantia_seriedad = garantias.get("MontoGarantiaSeriedad") or detalle.get("MontoGarantiaSeriedad")

    requiere_garantia_fiel = bool(
        garantias.get("MontoGarantiaFielCumplimiento")
        or garantias.get("RequiereGarantiaFielCumplimiento")
        or detalle.get("RequiereGarantiaFielCumplimiento")
    )
    monto_garantia_fiel = garantias.get("MontoGarantiaFielCumplimiento") or detalle.get("MontoGarantiaFielCumplimiento")

    # Debug puntual: deja rastro en el log para poder ajustar claves con datos reales.
    if organismo == "Organismo Desconocido" and detalle:
        print(f"🩺 DEBUG organismo desconocido para {codigo}. Claves del detalle: {list(detalle.keys())}")
    if not requiere_garantia_seriedad and not requiere_garantia_fiel and detalle:
        print(f"🩺 DEBUG sin datos de garantía para {codigo}. Claves de 'Garantias': {list(garantias.keys()) if garantias else 'no existe la llave Garantias'}")

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
        "monto_estimado": monto_estimado,
        "moneda": moneda,
        "monto_formateado": _formatear_monto(monto_estimado, moneda),
        "requiere_garantia_seriedad": requiere_garantia_seriedad,
        "monto_garantia_seriedad": monto_garantia_seriedad,
        "requiere_garantia_fiel_cumplimiento": requiere_garantia_fiel,
        "monto_garantia_fiel_cumplimiento": monto_garantia_fiel,
    }


def procesar_y_guardar_licitaciones():
    """
    1) Trae el listado básico del día.
    2) Prefiltra por nombre (barato) para no gastar cuota de API en detalle.
    3) Para cada candidata, pide el detalle completo (organismo, descripción, montos, garantías).
    4) Clasifica con el texto completo (nombre + descripción reales).
    5) Descarta las que YA cerraron (no son oportunidad real de oferta).
    6) Guarda en Mongo SOLO si matchea alguna categoría (Coimsa/Induwork/Especial).
    """
    licitaciones_crudas = obtener_licitaciones_api_real()
    nuevas_relevantes = []

    if not licitaciones_crudas:
        return nuevas_relevantes

    candidatas = [lic for lic in licitaciones_crudas if posible_relevante(lic.get("Nombre", ""))]
    print(f"🔍 {len(candidatas)} de {len(licitaciones_crudas)} pasaron el prefiltro por nombre. Pidiendo detalle...")

    ahora = datetime.datetime.now(CL_TZ).replace(tzinfo=None)

    for lic in candidatas:
        codigo = lic.get("CodigoExterno")
        if not codigo:
            continue

        detalle = obtener_detalle_licitacion(codigo)
        licitacion_mapeada = _mapear_licitacion(lic, detalle)

        # Descartar licitaciones cuyo cierre ya pasó: no es una oportunidad real, es historial.
        fecha_cierre_dt = _parsear_fecha(licitacion_mapeada["fecha_cierre"])
        if fecha_cierre_dt and fecha_cierre_dt < ahora:
            print(f"⏭️ {codigo} ya cerró ({licitacion_mapeada['fecha_cierre']}), se descarta.")
            continue

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
    Monitoreo rápido (cada 30 minutos).

    IMPORTANTE: antes esto consultaba estado='proveedor_seleccionado' (procesos YA
    resueltos, con proveedor elegido) — eso hacía que compras ágiles ya adjudicadas
    hace semanas aparecieran como "nueva oportunidad". Se corrigió para consultar
    estado='publicada' (todavía abiertas, aceptando cotizaciones) y solo avisar de
    las que cierran dentro de las próximas HORAS_URGENTE_COMPRA_AGIL horas.
    """
    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET para Compra Ágil v2.")
        return []

    BASE_URL_V2 = "https://api2.mercadopublico.cl"
    headers = {"ticket": TICKET, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    params = {"estado": "publicada", "tamano_pagina": 50, "numero_pagina": 1}

    alertas_urgentes = []
    MAX_PAGINAS_SEGURIDAD = 20
    ahora = datetime.datetime.now(CL_TZ).replace(tzinfo=None)

    try:
        todos_los_items = []
        while True:
            print(f"⏱️ Consultando Compra Ágil v2 (publicada) - página {params['numero_pagina']}...")
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

        print(f"🔎 Analizando {len(todos_los_items)} Compras Ágiles publicadas (abiertas)...")

        for item in todos_los_items:
            codigo_ca = item.get("codigo")
            if not codigo_ca:
                continue

            det_resp = requests.get(f"{BASE_URL_V2}/v2/compra-agil/{codigo_ca}", headers=headers, timeout=10)
            if det_resp.status_code != 200:
                continue

            detalle = det_resp.json().get("payload", {}) or {}
            fechas = detalle.get("fechas", {}) or {}
            fecha_cierre_str = fechas.get("fecha_cierre") or item.get("fecha_cierre")
            fecha_cierre_dt = _parsear_fecha(fecha_cierre_str)

            if not fecha_cierre_dt:
                continue  # sin fecha de cierre confiable, no podemos saber si es "urgente"

            horas_restantes = (fecha_cierre_dt - ahora).total_seconds() / 3600

            # Ya cerró, o falta demasiado tiempo todavía: no es "urgente" aún.
            if horas_restantes <= 0 or horas_restantes > HORAS_URGENTE_COMPRA_AGIL:
                continue

            compra_mapeada = {
                "id": codigo_ca,
                "nombre": item.get("nombre", "Compra Ágil sin título"),
                "descripcion": detalle.get("descripcion", item.get("nombre", "")),
                "region": (detalle.get("institucion", {}) or {}).get("nombre_region", "No Especificada"),
                "organismo": (detalle.get("institucion", {}) or {}).get("organismo_comprador", "Organismo Desconocido"),
                "fecha_cierre": fecha_cierre_str,
                "link": "https://buscador.mercadopublico.cl/compra-agil",
                "tipo": "Compra Ágil",
                "monto_estimado": detalle.get("monto_estimado") or item.get("monto_estimado"),
                "moneda": detalle.get("moneda", "CLP"),
                "monto_formateado": _formatear_monto(detalle.get("monto_estimado") or item.get("monto_estimado"), detalle.get("moneda", "CLP")),
                "requiere_garantia_seriedad": False,  # Compra Ágil generalmente no exige garantías
                "requiere_garantia_fiel_cumplimiento": False,
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
                            print(f"✨ [Compra Ágil] Cierra en {horas_restantes:.1f}h — Guardada: {codigo_ca}")
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
        d.pop("_id", None)
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