import asyncio
from datetime import datetime
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, User, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from pydantic import BaseModel
from config import TELEGRAM_BOT_TOKEN
from utils.api_requests import get_food_info, get_weather_async
from utils.calculation import calculate_calories, calculate_water
from utils.visualization import get_water_visualization
import logging


# Профиль пользователя для хранения данных
class UserProfile(BaseModel):
    id: int
    weight: float
    height: float
    age: int
    activity: int
    city: str
    water_goal: int
    calorie_goal: int
    logged_water: int
    logged_calories: int
    burned_calories: int
    logged_activity: int
    temperature: float
    last_active_date: str


# Словарь для хранения пользователей
users = {}

# Создаем экземпляры бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


# Middleware для логирования сообщений
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user = event.from_user.username
        logging.info(f"{event.date} Сообщение от {user}: {event.text}")
        return await handler(event, data)


# Middleware для проверки начала нового дня
class UpdateInfoMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        if user_id in users:
            user_info: UserProfile = users.get(user_id)
            last_date = user_info.last_active_date
            now_date = datetime.now().date().isoformat()
            # Если начался новый день, то сбросить предыдущую информацию
            if now_date != last_date:
                user_info.logged_activity = 0
                user_info.logged_calories = 0
                user_info.logged_water = 0
                user_info.burned_calories = 0
                temperature = await get_weather_async(user_info.city)
                user_info.temperature = temperature
                user_info.water_goal = calculate_water(
                    user_info.weight, user_info.activity, temperature)
                user_info.last_active_date = now_date
                print(f"{event.from_user.username} Информация за день сброшена!")
        return await handler(event, data)


# Подключение middleware к диспетчеру
dp.message.middleware(LoggingMiddleware())
dp.message.middleware(UpdateInfoMiddleware())


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Этот бот помогает рассчитать дневные нормы воды и калорий, а также отслеживать тренировки и питание.")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        '/start - Запуск бота;\n' +
        '/help - Информация о командах;\n' +
        '/set_profile - Заполнение профиля пользователя;\n' +
        '/log_water <количество> - Добавить запись о выпитой воде;\n' +
        '/log_food <название продукта> - Записывает калорийность съеденного продукта;\n' +
        '/log_workout <тип тренировки> <время (мин)> - Фиксирует сожженные калории и расход жидкости во время тренировки;\n' +
        '/check_progress - Показывает, сколько воды и калорий потреблено, сожжено и сколько осталось до выполнения цели;\n' +
        '/change_calorie_goal - Изменить количество калорий на день.'
    )


class ProfileForm(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()


class UpdateInfoForm(StatesGroup):
    calorie_goal = State()


class FoodQuantityForm(StatesGroup):
    food_calorie = State()
    food_quantity = State()


change_calorie_button = InlineKeyboardButton(
    text="Изменить цель по калориям",
    callback_data="change_calorie"
)
show_stats_button = InlineKeyboardButton(
    text="Показать график выполнения цели",
    callback_data="show_goals"
)
user_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[change_calorie_button], [show_stats_button]]
)


# Команда настройки профиля пользователя
@dp.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileForm.weight)


# Установка веса
@dp.message(ProfileForm.weight)
async def cmd_set_profile_weight(message: Message, state: FSMContext):
    try:
        await state.update_data(weight=float(message.text))
        await message.answer("Введите ваш рост (в см):")
        await state.set_state(ProfileForm.height)
    except Exception:
        await message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте /set_profile еще раз...")
        await state.clear()


# Установка роста
@dp.message(ProfileForm.height)
async def cmd_set_profile_height(message: Message, state: FSMContext):
    try:
        await state.update_data(height=float(message.text))
        await message.answer("Введите ваш возраст:")
        await state.set_state(ProfileForm.age)
    except Exception:
        await message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте /set_profile еще раз...")
        await state.clear()


# Установка возраста
@dp.message(ProfileForm.age)
async def cmd_set_profile_age(message: Message, state: FSMContext):
    try:
        await state.update_data(age=int(message.text))
        await message.answer("Сколько минут активности у вас в день?")
        await state.set_state(ProfileForm.activity)
    except Exception:
        await message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте /set_profile еще раз...")
        await state.clear()


# Установка времени активности
@dp.message(ProfileForm.activity)
async def cmd_set_profile_activity(message: Message, state: FSMContext):
    try:
        await state.update_data(activity=int(message.text))
        await message.answer("В каком городе вы находитесь?")
        await state.set_state(ProfileForm.city)
    except Exception:
        await message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте /set_profile еще раз...")
        await state.clear()


# Сообщение об обновлении целей с их выводом
async def show_update_message(user_info: User, calorie_goal: int, water_goal: int, temp: int):
    more_water_info = '\nСегодня жарко, выпейте побольше воды!' if temp > 25 else ''
    await bot.send_message(
        user_info.id,
        f'@{user_info.username} Ваша информация успешно записана!\n' +
        f'Цель по калориям: {calorie_goal} калорий;\n' +
        f'Цель по выпитой воде: {water_goal} мл. {more_water_info}',
        reply_markup=user_keyboard
    )


# Установка города пользователя
@dp.message(ProfileForm.city)
async def cmd_set_profile_city(message: Message, state: FSMContext):
    city = message.text
    data = await state.get_data()
    user_id = message.from_user.id
    weight = data.get('weight')
    height = data.get('height')
    age = data.get('age')
    activity = data.get('activity')
    city_temperature = await get_weather_async(city)
    water_goal = await calculate_water(weight, activity, city_temperature)
    calorie_goal = calculate_calories(weight, height, age, activity)
    # Создание профиля пользователя
    user_profile = UserProfile(
        id=user_id,
        weight=weight,
        height=height,
        age=age,
        activity=activity,
        city=city,
        calorie_goal=calorie_goal,
        logged_calories=0,
        burned_calories=0,
        water_goal=water_goal,
        logged_water=0,
        logged_activity=0,
        last_active_date=datetime.now().date().isoformat(),
        temperature=city_temperature
    )
    users[user_id] = user_profile
    await show_update_message(
        message.from_user,
        calorie_goal,
        water_goal,
        city_temperature
    )
    await state.clear()

# Обновление информации об активностях


# возвращает список параметров
def get_command_params(text: str, command: str) -> list[str]:
    return text[len(command):].strip().split()


# Логирование воды
@dp.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        try:
            params = get_command_params(message.text, "/log_water")
            new_water = int(params[0])
            user_info: UserProfile = users.get(user_id)
            # Обновление данных о выпитой воде
            user_info.logged_water += new_water
            water_left = user_info.water_goal - user_info.logged_water
            await message.reply(
                "Выпитая вода записана.\n" +
                f"Выпито: {user_info.logged_water} из {user_info.water_goal} мл\n" +
                f"Осталось выпить: {water_left} мл."
            )
        except Exception:
            await message.answer("Произошла ошибка при обработке запроса.")


# Логирование еды. Получение информации о еде
@dp.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        try:
            params = get_command_params(message.text, "/log_food")
            # Запрос информации о еде
            food_info = await get_food_info(params[0])
            if food_info:
                food_name = food_info.get('name')
                food_calories = food_info.get('calories')
                await state.update_data(food_calorie=food_calories)
                await message.answer(f"{food_name} - {food_calories} ккал на 100г. Сколько грамм вы съели?")
                await state.set_state(FoodQuantityForm.food_quantity)
            else:
                await message.reply("Не удалось определить продукт.")
        except Exception:
            await message.answer("Произошла ошибка при обработке запроса.")


# Логирование еды. Получение информации о съеденном количестве
@dp.message(FoodQuantityForm.food_quantity)
async def cmd_set_profile_activity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        try:
            data = await state.get_data()
            quantity = int(message.text)
            calorie = data.get('food_calorie')
            new_calories = calorie*quantity/100
            user_info: UserProfile = users.get(user_id)
            logged_calories = user_info.logged_calories + new_calories
            # Обновление данных о калориях
            user_info.logged_calories = logged_calories
            await message.reply(
                f"Потребленные калории записаны : {new_calories} ккал.\n" +
                f"Калорий за день: {user_info.logged_calories} из {user_info.calorie_goal} ккал\n" +
                f"Баланс: {logged_calories - user_info.burned_calories} ккал."
            )
        except Exception:
            await message.answer("Произошла ошибка при обработке запроса.")
    await state.clear()


# Логирование тренировок
@dp.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        try:
            params = get_command_params(message.text, "/log_workout")
            activity_type = params[0]
            activity_time = int(params[1])
            calories = activity_time*10
            user_info: UserProfile = users.get(user_id)
            # Обновление сожженных калорий
            user_info.burned_calories += calories
            user_info.logged_activity += activity_time
            optional_info = ''
            # Учет расходов воды на тренировку
            if activity_time > 30:
                water = int(200*activity_time/30)
                optional_info = f" Дополнительно: выпейте {water} мл воды."
            await message.reply(f"{activity_type} {activity_time} минут — {calories} ккал.{optional_info}")
        except Exception:
            await message.answer("Произошла ошибка при обработке запроса.")


# Прогресс по воде и калориям
@dp.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        user_info: UserProfile = users.get(user_id)
        logged_calories = user_info.logged_calories
        calorie_goal = user_info.calorie_goal
        await message.reply(
            f"@{message.from_user.username} вот Ваш прогресс:\n" +
            "Жидкость:\n" +
            f"  Выпито: {user_info.logged_water}/{user_info.water_goal} мл;\n" +
            f"  Осталось: {user_info.water_goal - user_info.logged_water} мл;\n\n" +
            "Калории:\n" +
            f"  Потреблено: {logged_calories}/{calorie_goal} ккал;\n" +
            f"  Потрачено: {user_info.burned_calories} ккал;\n" +
            f"  Баланс: {logged_calories - user_info.burned_calories} ккал.",
            reply_markup=user_keyboard
        )


# Изменение цели по калориям
@dp.message(Command("change_calorie_goal"))
async def cmd_change_calorie_goal(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        await message.answer("Укажите новое количество калорий на день:")
        await state.set_state(UpdateInfoForm.calorie_goal)


@dp.message(UpdateInfoForm.calorie_goal)
async def change_calorie_goal(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        calorie_goal = int(message.text)
        user_info: UserProfile = users.get(user_id)
        user_info.calorie_goal = calorie_goal
        await show_update_message(
            message.from_user,
            user_info.calorie_goal,
            user_info.water_goal,
            user_info.temperature
        )
    except Exception:
        await message.answer("Произошла ошибка при обработке запроса.")
    await state.clear()


# Отправка графика с достижением целей
async def show_goals_visualization(user_id: int):
    if user_id not in users:
        await bot.send_message(user_id, "Сперва укажите данные с помощью /set_profile")
    else:
        user_info: UserProfile = users.get(user_id)
        buf = get_water_visualization(
            user_info.logged_water,
            user_info.water_goal,
            user_info.logged_calories,
            user_info.calorie_goal,
            user_info.logged_activity,
            user_info.activity
        )
        buf.seek(0)
        photo_bytes = buf.read()
        photo = BufferedInputFile(file=photo_bytes, filename='goals.png')
        await bot.send_photo(user_id, photo=photo)


# Обработчик вызовов из кнопок
@dp.callback_query()
async def handle_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    if callback_query.data == "change_calorie":
        user_id = callback_query.from_user.id
        if user_id not in users:
            await bot.send_message(callback_query.from_user.id, "Сперва укажите данные с помощью /set_profile")
        else:
            await bot.send_message(callback_query.from_user.id, "Укажите новое количество калорий на день:")
            await state.set_state(UpdateInfoForm.calorie_goal)
    elif callback_query.data == "show_goals":
        user_id = callback_query.from_user.id
        await show_goals_visualization(user_id)


# Основная функция запуска бота
async def main():
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
