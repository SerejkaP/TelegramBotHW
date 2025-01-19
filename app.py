import asyncio
from datetime import datetime
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, User, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from pydantic import BaseModel
from config import TELEGRAM_BOT_TOKEN
from utils.api_requests import get_weather_async
from utils.calculation import calculate_calories, calculate_water
from utils.visualization import get_water_visualization


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


users = {}

# Создаем экземпляры бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user = event.from_user.username
        print(f"{event.date} Сообщение от {user}: {event.text}")
        return await handler(event, data)


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
    calorie = State()
    water = State()
    activity = State()

# Параметры профиля


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


@dp.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileForm.weight)


@dp.message(ProfileForm.weight)
async def cmd_set_profile_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(ProfileForm.height)


@dp.message(ProfileForm.height)
async def cmd_set_profile_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(ProfileForm.age)


@dp.message(ProfileForm.age)
async def cmd_set_profile_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(ProfileForm.activity)


@dp.message(ProfileForm.activity)
async def cmd_set_profile_activity(message: Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(ProfileForm.city)


async def show_update_message(user_info: User, calorie_goal: int, water_goal: int, temp: int):
    more_water_info = '\nСегодня жарко, выпейте побольше воды!' if temp > 25 else ''
    await bot.send_message(
        user_info.id,
        f'@{user_info.username} Ваша информация успешно записана!\n' +
        f'Цель по калориям: {calorie_goal} калорий;\n' +
        f'Цель по выпитой воде: {water_goal} мл. {more_water_info}',
        reply_markup=user_keyboard
    )


@dp.message(ProfileForm.city)
async def cmd_set_profile_city(message: Message, state: FSMContext):
    city = message.text
    data = await state.get_data()
    user_id = message.from_user.id
    weight = float(data.get('weight'))
    height = float(data.get('height'))
    age = int(data.get('age'))
    activity = int(data.get('activity'))
    city_temperature = await get_weather_async(city)
    water_goal = await calculate_water(weight, activity, city_temperature)
    calorie_goal = calculate_calories(weight, height, age, activity)
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


@dp.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        await message.reply("")


@dp.message(Command("log_food"))
async def cmd_log_food(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        await message.reply("")


@dp.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("Сперва укажите данные с помощью /set_profile")
    else:
        await message.reply("")


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
            f"  Выпито: {user_info.logged_water}/{user_info.water_goal};\n" +
            f"  Осталось: {user_info.logged_water}/{user_info.water_goal};\n\n" +
            "Калории:\n" +
            f"  Потреблено: {logged_calories}/{calorie_goal};\n" +
            f"  Потрачено: {user_info.burned_calories};\n",
            f"  Баланс: {logged_calories - user_info.burned_calories}.",
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
    await state.clear()

# Отправка фото с достижением целей


async def show_goals_visualization(user_id: int):
    if user_id not in users:
        await bot.send_message(user_id, "Сперва укажите данные с помощью /set_profile")
    else:
        user_info: UserProfile = users.get(user_id)
        buf = get_water_visualization(
            user_info.logged_water,
            user_info.water_goal,
            user_info.logged_calories,
            user_info.calorie_goal
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
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
