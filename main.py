from fastapi import FastAPI, BackgroundTasks
from zoneinfo import ZoneInfo
from datetime import datetime

from modules.scraper import procesar_y_guardar_licitaciones, simular_scraping_compra_agil_urgente
from modules.mailer import enviar_correo_oportunidades
from config.database import get_db

app = FastAPI(
    title="Bot Mercado Público & Compra Ágil",
    description="Sistema automatizado de capturas para Coimsa e Induwork",
    version="2.1.0"
)

db = get_db()
if db is not None:
    print("✅ Conexión exitosa a MongoDB Atlas e índices únicos listos.")
else:
    print("⚠️ Bot iniciado sin conexión activa a la base de datos.")

CL_TZ = ZoneInfo("America/Santiago")


# ============================================================
#  FUNCIONES DE NEGOCIO (ejecutadas como BackgroundTasks)
# ============================================================

def tarea_fast_check_compra_agil():
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    print(f"⏱️ Fast Check Compra Ágil ({hora_local} hora Chile)")

    alertas = simular_scraping_compra_agil_urgente()

    if not alertas:
        print("ℹ️ No hubo alertas urgentes en este ciclo.")
        return

    ca_coimsa = [ca for ca in alertas if ca["clasificacion"]["coimsa"]]
    ca_induwork = [ca for ca in alertas if ca["clasificacion"]["induwork"]]

    if ca_coimsa:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",  # TODO: cambiar al correo real de Coimsa
            asunto=f"🚨 ALERTA INMEDIATA (COIMSA) - {hora_local}: Compra Ágil de Cierre Pronto",
            licitaciones=ca_coimsa,
            es_alerta_urgente=True
        )

    if ca_induwork:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",
            asunto=f"🚨 ALERTA INMEDIATA (INDUWORK) - {hora_local}: Compra Ágil de Cierre Pronto",
            licitaciones=ca_induwork,
            es_alerta_urgente=True
        )


def tarea_reporte_diario():
    hora_local = datetime.now(CL_TZ).strftime("%H:%M")
    print(f"📋 Reporte Diario ({hora_local} hora Chile)")

    nuevas = procesar_y_guardar_licitaciones()

    if not nuevas:
        print("ℹ️ No hay nuevas licitaciones para el reporte diario.")
        return

    licitaciones_coimsa = [l for l in nuevas if l["clasificacion"]["coimsa"]]
    licitaciones_induwork = [l for l in nuevas if l["clasificacion"]["induwork"]]
    licitaciones_especiales = [l for l in nuevas if l["clasificacion"]["especial"]]

    if licitaciones_coimsa:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",  # TODO: cambiar al correo real de Coimsa
            asunto=f"📋 COIMSA - {hora_local}: Nuevas Licitaciones de Limpieza y Aseo",
            licitaciones=licitaciones_coimsa
        )

    if licitaciones_induwork:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",
            asunto=f"📋 INDUWORK - {hora_local}: Nuevas Oportunidades de Equipo Táctico y Seguridad",
            licitaciones=licitaciones_induwork
        )

    if licitaciones_especiales:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",
            asunto=f"💡 ALERTAS - {hora_local}: Nuevos Proyectos Informáticos o Sociales",
            licitaciones=licitaciones_especiales
        )

    print("📨 Correo(s) diario(s) enviado(s).")


# ============================================================
#  ENDPOINTS
#  cron-job.org (u otro cron externo) llama estas rutas.
#  En el plan gratis de Render, esto además evita que el
#  servicio se duerma por falta de tráfico HTTP.
# ============================================================

@app.get("/")
def estado_bot():
    return {
        "status": "online",
        "proyecto": "Coimsa & Induwork Procurement Bot",
        "hora_servidor_utc": datetime.utcnow().isoformat(),
        "hora_chile": datetime.now(CL_TZ).isoformat(),
    }


@app.get("/cron/fast-check")
def endpoint_fast_check(background_tasks: BackgroundTasks):
    """Configurar en cron-job.org: cada 30 minutos, todos los días."""
    background_tasks.add_task(tarea_fast_check_compra_agil)
    return {"status": "scheduled", "task": "Fast Check - Compra Ágil en segundo plano"}


@app.get("/cron/daily-report")
def endpoint_daily_report(background_tasks: BackgroundTasks):
    """Configurar en cron-job.org: 06:00 y 18:00 hora Chile (o los horarios que definas)."""
    background_tasks.add_task(tarea_reporte_diario)
    return {"status": "scheduled", "task": "Daily Report - Ejecutando extracción diaria"}


@app.get("/cron/test-fast-check-now")
def test_fast_check_now():
    """
    Endpoint SÍNCRONO (sin BackgroundTasks) para probar manualmente desde el navegador
    o Postman y ver el resultado real al tiro, sin esperar el horario programado.
    """
    alertas = simular_scraping_compra_agil_urgente()
    return {"alertas_encontradas": len(alertas), "detalle": alertas}


@app.get("/cron/test-daily-report-now")
def test_daily_report_now():
    """Igual que arriba, pero para el reporte diario de licitaciones."""
    nuevas = procesar_y_guardar_licitaciones()
    return {"licitaciones_nuevas": len(nuevas), "detalle": nuevas}