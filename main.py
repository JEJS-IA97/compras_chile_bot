from fastapi import FastAPI
import asyncio
from datetime import datetime

from modules.scraper import procesar_y_guardar_licitaciones, simular_scraping_compra_agil_urgente
from modules.mailer import enviar_correo_oportunidades
from config.database import get_db

app = FastAPI(
    title="Bot Mercado Público & Compra Ágil",
    description="Sistema automatizado de capturas para Coimsa e Induwork",
    version="2.0.0"
)

db = get_db()
if db is not None:
    print("✅ Conexión exitosa a MongoDB Atlas e índices únicos listos.")
else:
    print("⚠️ Bot iniciado sin conexión activa a la base de datos.")



# ============================================================
#  FUNCIONES DE NEGOCIO
# ============================================================

async def ejecutar_fast_check(hora):
    print(f"⏱️ Fast Check Compra Ágil ({hora}:00)")

    alertas = simular_scraping_compra_agil_urgente()

    if alertas:
        print("🚨 Compra Ágil urgente detectada, enviando correo inmediato...")
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",
            asunto=f"🚨 ALERTA INMEDIATA ({hora}:00): Compra Ágil de Cierre Pronto",
            licitaciones=alertas,
            es_alerta_urgente=True
        )
    else:
        print("ℹ️ No hubo alertas urgentes en este ciclo.")


async def ejecutar_reporte_diario(hora):
    print(f"📋 Reporte Diario ({hora}:00)")

    nuevas = procesar_y_guardar_licitaciones()

    if nuevas:
        enviar_correo_oportunidades(
            destinatario="soporte@induwork.cl",
            asunto=f"📋 REPORTE DIARIO ({hora}:00): Nuevas Oportunidades Detectadas",
            licitaciones=nuevas
        )
        print("📨 Correo diario enviado.")
    else:
        print("ℹ️ No hay nuevas licitaciones para el reporte diario.")


# ============================================================
#  SCHEDULER AUTOMÁTICO
# ============================================================

async def scheduler():
    print("🕒 Scheduler iniciado. El bot se ejecutará automáticamente.")

    while True:
        ahora = datetime.now().strftime("%H:%M")

        if ahora == "06:00":
            await ejecutar_fast_check("06")

        if ahora == "12:00":
            await ejecutar_reporte_diario("12")

        if ahora == "18:00":
            await ejecutar_fast_check("18")

        if ahora == "00:00":
            await ejecutar_reporte_diario("00")

        await asyncio.sleep(60)  # revisar cada minuto


# ============================================================
#  INICIO AUTOMÁTICO DEL BOT
# ============================================================

@app.on_event("startup")
async def iniciar_bot():
    print("🚀 Bot iniciado, activando scheduler automático...")
    asyncio.create_task(scheduler())


@app.get("/")
def estado_bot():
    return {"status": "online", "proyecto": "Coimsa & Induwork Procurement Bot"}
