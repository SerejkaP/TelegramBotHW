import os

from dotenv import load_dotenv

# Суперподробное логирование для отладки
import logging
LOGGING_LEVEL = int(os.getenv("LOGGING_LEVEL", logging.INFO))
logging.basicConfig(level=LOGGING_LEVEL)

aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(LOGGING_LEVEL)

# Загрузка переменных из .env файла
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPEN_WEATHER_MAP_TOKEN = os.getenv("OPEN_WEATHER_MAP_TOKEN")

if not TELEGRAM_BOT_TOKEN or not OPEN_WEATHER_MAP_TOKEN:
    raise NameError
