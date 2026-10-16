
import os
from pathlib import Path

from dotenv import load_dotenv


# Caminho da pasta principal do projeto SALTY.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o .env dessa pasta e prioriza seus valores.
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE, override=True)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-apenas-local")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
