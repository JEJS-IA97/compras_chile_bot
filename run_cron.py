"""
Punto de entrada para correr las tareas del bot fuera de Render,
disparado por GitHub Actions (cron). Uso:

    python run_cron.py fast-check
    python run_cron.py daily-report
    python run_cron.py weekly-report
    python run_cron.py monthly-report
    python run_cron.py resend-all
"""
import sys

from main import (
    tarea_fast_check_compra_agil,
    tarea_reporte_diario,
    tarea_reporte_semanal,
    tarea_reporte_mensual,
    tarea_reenviar_todo_almacenado,
)

TAREAS = {
    "fast-check": tarea_fast_check_compra_agil,
    "daily-report": tarea_reporte_diario,
    "weekly-report": tarea_reporte_semanal,
    "monthly-report": tarea_reporte_mensual,
    "resend-all": tarea_reenviar_todo_almacenado,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TAREAS:
        print(f"Uso: python run_cron.py [{'|'.join(TAREAS.keys())}]")
        sys.exit(1)

    nombre_tarea = sys.argv[1]
    print(f"🚀 Ejecutando tarea: {nombre_tarea}")
    TAREAS[nombre_tarea]()
    print(f"🏁 Tarea '{nombre_tarea}' finalizada.")