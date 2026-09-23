"""
Purga validaciones de IA obsoletas en MongoDB.

Uso:
    python purgar_validaciones_ia.py

Quita validacion_ia_induwork y marca induwork=False en clasificacion
para que el siguiente daily-report vuelva a consultar Gemini con el
prompt corregido (evita falsos positivos cacheados, p.ej. uniformes
de hospital).
"""
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def main():
    uri = os.getenv("MONGO_URI")

    if not uri:
        print("❌ MONGO_URI no configurada.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client["chilecompra_db"]
    col = db["licitaciones"]

    total = col.count_documents({})
    con_validacion = col.count_documents(
        {"validacion_ia_induwork": {"$exists": True}}
    )

    print(f"📄 Documentos totales: {total}")
    print(f"🤖 Con validacion_ia_induwork: {con_validacion}")

    resultado = col.update_many(
        {"validacion_ia_induwork": {"$exists": True}},
        {
            "$unset": {"validacion_ia_induwork": ""},
            "$set": {"clasificacion.induwork": False},
        },
    )

    print(
        f"♻️ Purgados: {resultado.modified_count} "
        "(revalidará Gemini en el próximo reporte)."
    )

    cliente_induwork = col.count_documents(
        {"clasificacion.induwork": True}
    )
    print(
        f"ℹ️ Quedan {cliente_induwork} con "
        "clasificacion.induwork=True (sin cache de IA)."
    )

    client.close()


if __name__ == "__main__":
    main()
