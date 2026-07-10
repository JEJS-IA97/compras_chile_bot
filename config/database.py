import os
from pymongo import MongoClient, errors
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

def get_db():
    """
    Establece la conexión con MongoDB Atlas utilizando la URI de entorno.
    Retorna la instancia de la base de datos 'chilecompra_db'.
    """
    if not MONGO_URI:
        raise ValueError("Error: La variable MONGO_URI no está configurada en el archivo .env")
    
    try:
        # Conectar al clúster de MongoDB
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["chilecompra_db"]
        
        # Crear índices únicos para evitar duplicados de raíz
        # Asegura que el ID de la licitación ('id') sea único en la colección
        db["licitaciones"].create_index("id", unique=True)
        
        return db
    except errors.ServerSelectionTimeoutError:
        print("❌ Error: No se pudo conectar a MongoDB Atlas. Revisa tu conexión o IP permitidas.")
        return None
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado al conectar a la Base de Datos: {e}")
        return None