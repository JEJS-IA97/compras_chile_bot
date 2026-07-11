import os
import datetime
from zoneinfo import ZoneInfo
import requests
from config.database import get_db
from modules.filters import evaluar_licitacion

CL_TZ = ZoneInfo("America/Santiago")

# Conectar a la base de datos
db = get_db()
TICKET = os.getenv("CHILECOMPRA_TICKET")


def obtener_licitaciones_api_real():
    """
    Consulta la API oficial v1 de Mercado Público (licitaciones.json) para el día actual,
    con respaldo al día anterior si no hay datos publicados todavía.
    """
    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET en el archivo .env")
        return []

    ahora = datetime.datetime.now()
    hoy_str = ahora.strftime("%d%m%Y")  # Formato estricto DDMMAAAA (ej: 09072026)

    url = f"https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?fecha={hoy_str}&ticket={TICKET}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    try:
        print(f"📡 Consultando API Mercado Público Oficial para la fecha: {hoy_str}...")
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            listado = data.get("Listado", [])
            print(f"🔎 {len(listado)} licitaciones recibidas para {hoy_str}.")
            return listado

        elif response.status_code == 404:
            ayer = ahora - datetime.timedelta(days=1)
            ayer_str = ayer.strftime("%d%m%Y")
            print(f"⚠️ Fecha de hoy sin datos (404). Consultando respaldo de ayer: {ayer_str}...")

            url_ayer = f"https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?fecha={ayer_str}&ticket={TICKET}"
            res_ayer = requests.get(url_ayer, headers=headers, timeout=15)

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
        print(f"❌ Error de conexión con el servidor de Mercado Público: {e}")
        return []


def procesar_y_guardar_licitaciones():
    """
    Toma el listado crudo de la API v1 de Licitaciones, lo mapea al formato que
    espera evaluar_licitacion(), clasifica para Coimsa/Induwork/Especiales,
    evita duplicados en MongoDB y retorna solo las licitaciones NUEVAS y relevantes.

    Esta es la función que faltaba: main.py la importaba pero nunca existió,
    por eso el reporte diario nunca traía resultados.
    """
    licitaciones_crudas = obtener_licitaciones_api_real()
    nuevas_relevantes = []

    if not licitaciones_crudas:
        return nuevas_relevantes

    print(f"🔍 Clasificando {len(licitaciones_crudas)} licitaciones...")

    for lic in licitaciones_crudas:
        codigo = lic.get("CodigoExterno")
        if not codigo:
            continue

        comprador = lic.get("Comprador", {}) or {}

        licitacion_mapeada = {
            "id": codigo,
            "nombre": lic.get("Nombre", "Licitación sin título"),
            "descripcion": lic.get("Descripcion", "") or lic.get("Nombre", ""),
            "region": comprador.get("RegionUnidad", "No Especificada"),
            "organismo": comprador.get("NombreOrganismo", "Organismo Desconocido"),
            "fecha_cierre": lic.get("FechaCierre", "Sin fecha"),
            "tipo": "Licitación",
        }

        clasificacion = evaluar_licitacion(licitacion_mapeada)

        if clasificacion["coimsa"] or clasificacion["induwork"] or clasificacion["especial"]:
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
                # Fallback si la DB no está disponible, para no perder el correo
                nuevas_relevantes.append(licitacion_mapeada)

    print(f"✅ {len(nuevas_relevantes)} licitaciones nuevas y relevantes encontradas.")
    return nuevas_relevantes


def simular_scraping_compra_agil_urgente():
    """
    Monitoreo rápido (cada 30 minutos).
    Consulta la API oficial v2 de Compra Ágil recorriendo TODAS las páginas
    de procesos en estado 'proveedor_seleccionado', clasifica para Coimsa/Induwork
    y valida si ya se emitió la Orden de Compra.
    """
    if not TICKET:
        print("❌ Error: No se ha configurado CHILECOMPRA_TICKET para Compra Ágil v2.")
        return []

    BASE_URL_V2 = "https://api2.mercadopublico.cl"

    headers = {
        "ticket": TICKET,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    params = {
        "estado": "proveedor_seleccionado",
        "tamano_pagina": 50,   # máximo permitido por la API
        "numero_pagina": 1
    }

    alertas_urgentes = []
    MAX_PAGINAS_SEGURIDAD = 20  # evita agotar la cuota diaria si hay muchísimos resultados

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

            # Si id_orden_compra es distinto de null, significa que la OC SÍ fue emitida
            if id_oc is not None:
                compra_mapeada = {
                    "id": codigo_ca,
                    "nombre": item.get("nombre", "Compra Ágil sin título"),
                    "descripcion": detalle.get("descripcion", item.get("nombre", "")),
                    "region": (detalle.get("institucion", {}) or {}).get("nombre_region", "No Especificada"),
                    "organismo": (detalle.get("institucion", {}) or {}).get("organismo_comprador", "Organismo Desconocido"),
                    "fecha_cierre": (detalle.get("fechas", {}) or {}).get("fecha_cierre", "Finalizado"),
                    "tipo": "Compra Ágil",
                    "id_orden_compra": id_oc
                }

                clasificacion = evaluar_licitacion(compra_mapeada)

                if clasificacion["coimsa"] or clasificacion["induwork"]:
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