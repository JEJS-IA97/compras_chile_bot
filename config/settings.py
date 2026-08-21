import os
from dotenv import load_dotenv

load_dotenv()

# Clave de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")