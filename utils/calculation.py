from utils.api_requests import get_weather_async


def calculate_calories(weight: float, height: float, age: int, activity: int):
    # Калории за время активности
    activity_calorie = 200 + activity * 4.5
    # Расчет калорий на день
    return int(10 * weight + 6.25 * height - 5 * age + activity_calorie)


async def calculate_water(weight: float, activity: int, temperature: float):
    water_for_temperature = 1000 if temperature > 25 else 0
    # Возврат нужного количества воды на день
    return int(weight * 30 + 500 * activity / 30 + 500 - water_for_temperature)
