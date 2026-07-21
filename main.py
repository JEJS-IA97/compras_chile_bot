from fastapi import FastAPI, BackgroundTasks
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

from modules.scraper import (
    procesar_y_guardar_licitaciones,
    simular_scraping_compra_agil_urgente,
    obtener_almacenadas,
    agrupar_por_empresa,
)
from modules.mailer import enviar_correo_categoria, CONFIG_CATEGORIAS, DEST_PRUEBA_SOPORTE
from config.database import get_db

app = FastAPI(
    title="Bot Mercado Público & Compra Ágil",
    description="Sistema automatizado de capturas para Induwork, Coimsa y MVI",
    version="3.0.0"
)

db = get_db()
if db is not None:
    print("✅ Conexión exitosa a MongoDB Atlas e índices únicos listos.")
else:
    print("⚠️ Bot iniciado sin conexión activa a la base de datos.")

CL_TZ = ZoneInfo("America/Santiago")

def _enviar_por_categoria(items, hora_local, prefijo_asunto, es_alerta_urgente=False):
    """Reparte una lista de items ya clasificados a los 3 correos según corresponda."""
    grupos = agrupar_por_empresa(items)

    if grupos["coimsa"]:
        enviar_correo_categoria(
            "coimsa",
            f"{prefijo_asunto} (COIMSA) - {hora_local}",
            grupos["coimsa"],
            es_alerta_urgente=es_alerta_urgente,
        )
    if grupos["induwork"]:
        enviar_correo_categoria(
            "induwork",
            f"{prefijo_asunto} (INDUWORK) - {hora_local}",
            grupos["induwork"],
            es_alerta_urgente=es_alerta_urgente,
        )
    if grupos["especial"]:
        enviar_correo_categoria(
            "especial",
            f"{prefijo_asunto} (SOCIALES/MVI) - {hora_local}",
            grupos["especial"],
            es_alerta_urgente=es_alerta_urgente,
        )


def tarea_fast_check_compra_agil():
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    print(f"⏱️ Fast Check Compra Ágil ({hora_local} hora Chile)")

    alertas = simular_scraping_compra_agil_urgente()
    if not alertas:
        print("ℹ️ No hubo alertas urgentes en este ciclo.")
        return

    _enviar_por_categoria(alertas, hora_local, "🚨 ALERTA INMEDIATA: Compra Ágil de Cierre Pronto", es_alerta_urgente=True)


def tarea_reporte_diario():
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    print(f"📋 Reporte Diario ({hora_local} hora Chile)")

    nuevas = procesar_y_guardar_licitaciones()
    if not nuevas:
        print("ℹ️ No hay nuevas licitaciones para el reporte diario.")
        return

    _enviar_por_categoria(nuevas, hora_local, "📋 Nuevas Oportunidades")
    print("📨 Correo(s) diario(s) enviado(s).")

def _armar_cuerpo_resumen(nombre_categoria, items, dias_texto):
    from modules.scraper import contar_por_tipo
    conteo = contar_por_tipo(items)
    return f"""
    <p>Resumen de <b>{nombre_categoria}</b> — {dias_texto}:</p>
    <ul>
        <li><b>{conteo['licitaciones']}</b> licitaciones nuevas</li>
        <li><b>{conteo['compras_agiles']}</b> compras ágiles nuevas</li>
        <li><b>{len(items)}</b> oportunidades en total</li>
    </ul>
    """


def _reporte_periodo(desde, hasta, hora_local, prefijo_asunto, dias_texto):
    todas = obtener_almacenadas(desde=desde, hasta=hasta)
    if not todas:
        print(f"ℹ️ No hay datos almacenados en el período {dias_texto}.")
        return

    grupos = agrupar_por_empresa(todas)

    for categoria, nombre in (("coimsa", "Coimsa"), ("induwork", "Induwork"), ("especial", "MVI / Sociales")):
        items = grupos[categoria]
        if not items:
            continue
        cuerpo_extra = _armar_cuerpo_resumen(nombre, items, dias_texto)
        enviar_correo_categoria(
            categoria,
            f"{prefijo_asunto} ({nombre.upper()}) - {hora_local}",
            items,
            cuerpo_extra_html=cuerpo_extra,
        )

def tarea_reporte_semanal():
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    ahora_utc = datetime.utcnow()
    desde = ahora_utc - timedelta(days=7)
    print(f"📆 Reporte Semanal ({hora_local} hora Chile)")
    _reporte_periodo(desde, ahora_utc, hora_local, "📆 Resumen Semanal de Oportunidades", "últimos 7 días")


def tarea_reporte_mensual():
    hoy_cl = datetime.now(CL_TZ)
    hora_local = hoy_cl.strftime("%H:%M")

    primer_dia_mes_actual = hoy_cl.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(seconds=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    desde_utc = primer_dia_mes_anterior.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    hasta_utc = ultimo_dia_mes_anterior.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    nombre_mes = primer_dia_mes_anterior.strftime("%B %Y")
    print(f"🗓️ Reporte Mensual ({hora_local} hora Chile) — mes: {nombre_mes}")
    _reporte_periodo(desde_utc, hasta_utc, hora_local, "🗓️ Resumen Mensual de Oportunidades", f"mes de {nombre_mes}")

def tarea_reenviar_todo_almacenado():
    """
    Reenvía TODO lo que hay guardado en Mongo, sin volver a consultar Mercado Público.
    Este reporte va a SOPORTE@INDUWORK.CL (para que el equipo de soporte pueda revisar)
    """
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    print(f"📤 Reenviando todo lo almacenado a soporte ({hora_local} hora Chile)")

    todas = obtener_almacenadas()
    if not todas:
        print("ℹ️ No hay datos almacenados en la base de datos.")
        return

    # Agrupar por empresa
    grupos = agrupar_por_empresa(todas)
    
    # Contar totales
    from modules.scraper import contar_por_tipo
    total_licitaciones = 0
    total_compras_agiles = 0
    
    for categoria, items in grupos.items():
        if not items:
            continue
        conteo = contar_por_tipo(items)
        total_licitaciones += conteo["licitaciones"]
        total_compras_agiles += conteo["compras_agiles"]
        
        nombre_categoria = {
            "coimsa": "Coimsa",
            "induwork": "Induwork",
            "especial": "MVI / Sociales"
        }.get(categoria, categoria)

        # Cuerpo del resumen
        cuerpo_extra = f"""
        <h3>📊 Resumen de {nombre_categoria}</h3>
        <ul>
            <li><b>{conteo['licitaciones']}</b> licitaciones</li>
            <li><b>{conteo['compras_agiles']}</b> compras ágiles</li>
            <li><b>{len(items)}</b> oportunidades totales</li>
        </ul>
        <hr>
        """

        enviar_correo_categoria(
            categoria,
            f"📤 REENVÍO COMPLETO DB ({nombre_categoria}) - {hora_local}",
            items,
            cuerpo_extra_html=cuerpo_extra,
            destinatario_override=DEST_PRUEBA_SOPORTE, 
        )

    print(f"📨 Reenvío completo enviado a {DEST_PRUEBA_SOPORTE}")


@app.get("/")
def estado_bot():
    return {
        "status": "online",
        "proyecto": "Induwork & Coimsa & MVI Procurement Bot",
        "hora_chile": datetime.now(CL_TZ).isoformat(),
        "modo_prueba": True, 
        "destinatario_general": "gerencia@induwork.cl",
        "destinatario_resend": "soporte@induwork.cl",
    }


@app.get("/cron/fast-check")
def endpoint_fast_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(tarea_fast_check_compra_agil)
    return {"status": "scheduled", "task": "fast-check"}


@app.get("/cron/daily-report")
def endpoint_daily_report(background_tasks: BackgroundTasks):
    background_tasks.add_task(tarea_reporte_diario)
    return {"status": "scheduled", "task": "daily-report"}


@app.get("/cron/weekly-report")
def endpoint_weekly_report(background_tasks: BackgroundTasks):
    background_tasks.add_task(tarea_reporte_semanal)
    return {"status": "scheduled", "task": "weekly-report"}


@app.get("/cron/monthly-report")
def endpoint_monthly_report(background_tasks: BackgroundTasks):
    background_tasks.add_task(tarea_reporte_mensual)
    return {"status": "scheduled", "task": "monthly-report"}


@app.get("/cron/resend-all")
def endpoint_resend_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(tarea_reenviar_todo_almacenado)
    return {
        "status": "scheduled",
        "task": "resend-all",
        "destinatario": DEST_PRUEBA_SOPORTE
    }


@app.get("/cron/test-fast-check-now")
def test_fast_check_now():
    alertas = simular_scraping_compra_agil_urgente()
    return {"alertas_encontradas": len(alertas)}


@app.get("/cron/test-daily-report-now")
def test_daily_report_now():
    nuevas = procesar_y_guardar_licitaciones()
    return {"licitaciones_nuevas": len(nuevas)}