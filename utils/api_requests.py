import aiohttp

from config import OPEN_WEATHER_MAP_TOKEN

URL_OWM = "https://api.openweathermap.org/"
URL_OFF = "https://world.openfoodfacts.org/"


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


async def get_food_info(product_name: str):
    url = URL_OFF + \
        f"cgi/search.pl?action=process&search_terms={product_name}&json=true"
    data = await get_data_async(url)
    products = data.get('products', [])
    if products:  # Проверяем, есть ли найденные продукты
        first_product = products[0]
        return {
            'name': first_product.get('product_name', 'Неизвестно'),
            'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
        }
    return None
