from datetime import datetime
import os

import aiohttp

from config import OPEN_WEATHER_MAP_TOKEN

URL_OWM = "https://api.openweathermap.org/"


async def get_data_async(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def get_weather_async(city: str):
    # Вернет температуру
    city_info_url = URL_OWM + \
        f"geo/1.0/direct?q={city}&appid={OPEN_WEATHER_MAP_TOKEN}"
    city_info = await get_data_async(city_info_url)
    if 'cod' in city_info and city_info['cod'] == 401:
        return 0.0
    lat, lon = city_info[0]['lat'], city_info[0]['lon']
    weather_url = URL_OWM + \
        f"data/2.5/weather?lat={lat}&lon={
            lon}&units=metric&appid={OPEN_WEATHER_MAP_TOKEN}"
    weather = await get_data_async(weather_url)
    return float(weather['main']['temp'])
