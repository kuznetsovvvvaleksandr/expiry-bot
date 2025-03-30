import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta
import asyncio

API_TOKEN = os.getenv('7825679766:AAEcmgkMdwUl77gkgSFBcrmxEk0WLsDEVBU')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# In-memory DB
user_data = {}

class AddProduct(StatesGroup):
    name = State()
    expiry = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # Меню команд
    commands = [
        types.BotCommand(command="/add", description="Добавить продукт"),
        types.BotCommand(command="/list", description="Посмотреть список"),
        types.BotCommand(command="/remove", description="Удалить продукт"),
        types.BotCommand(command="/edit", description="Редактировать продукт"),
        types.BotCommand(command="/settings", description="Настройки"),
    ]
    await bot.set_my_commands(commands)

    await message.answer(
        "👋 Привет! Я помогу отслеживать сроки годности продуктов.\n\nКоманды:\n"
        "/add — Добавить продукт\n"
        "/list — Посмотреть список\n"
        "/remove — Удалить продукт\n"
        "/edit — Редактировать продукт\n"
        "/settings — Настройки"
    )

@dp.message_handler(commands=['add'])
async def add_product(message: types.Message):
    await message.answer("Введите название продукта:")
    await AddProduct.name.set()

@dp.message_handler(state=AddProduct.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите дату окончания срока годности (в формате ДД.ММ.ГГГГ):")
    await AddProduct.expiry.set()

@dp.message_handler(state=AddProduct.expiry)
async def process_expiry(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        expiry_date = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❗ Неверный формат. Введите дату в формате ДД.ММ.ГГГГ.")
        return

    product = {
        "name": data['name'],
        "expiry": expiry_date
    }
    user_data.setdefault(message.from_user.id, []).append(product)

    await message.answer(f"✅ Продукт '{data['name']}' добавлен с датой {message.text}")
    await state.finish()

@dp.message_handler(commands=['list'])
async def list_products(message: types.Message):
    products = user_data.get(message.from_user.id, [])
    if not products:
        await message.answer("📭 У вас нет добавленных продуктов.")
        return
    text = "📋 Ваши продукты:\n"
    for idx, p in enumerate(sorted(products, key=lambda x: x['expiry']), 1):
        text += f"{idx}. {p['name']} — до {p['expiry'].strftime('%d.%m.%Y')}\n"
    await message.answer(text)

@dp.message_handler(commands=['remove'])
async def remove_product(message: types.Message):
    products = user_data.get(message.from_user.id, [])
    if not products:
        await message.answer("❗ Список пуст.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for idx, p in enumerate(products, 1):
        keyboard.add(KeyboardButton(f"{idx}. {p['name']}"))

    await message.answer("Выберите продукт для удаления:", reply_markup=keyboard)

    @dp.message_handler()
    async def process_remove(msg: types.Message):
        try:
            index = int(msg.text.split('.')[0]) - 1
            removed = user_data[msg.from_user.id].pop(index)
            await msg.answer(f"🗑️ Продукт '{removed['name']}' удалён.", reply_markup=types.ReplyKeyboardRemove())
        except:
            await msg.answer("❗ Неверный выбор.")

@dp.message_handler(commands=['edit'])
async def edit_product(message: types.Message):
    await message.answer("Редактирование пока в разработке. В следующей версии ✏️")

@dp.message_handler(commands=['settings'])
async def settings(message: types.Message):
    await message.answer("⚙️ Настройки:\n- Уведомления включены по умолчанию\n(будет реализовано в следующей версии)")

async def notify_expiry():
    while True:
        now = datetime.now()
        for user_id, products in user_data.items():
            for p in products:
                days_left = (p['expiry'] - now).days
                if days_left in [3, 1, 0]:
                    await bot.send_message(user_id, f"⏰ Напоминание! Срок годности '{p['name']}' истекает через {days_left} дн." if days_left > 0 else f"⚠️ Сегодня последний день для '{p['name']}'!")
        await asyncio.sleep(86400)  # проверка раз в сутки

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(notify_expiry())
    executor.start_polling(dp, skip_updates=True)
