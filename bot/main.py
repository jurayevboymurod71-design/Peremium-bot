import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👑 Premium olish")],
        [KeyboardButton(text="📢 Reklama joylash")],
        [KeyboardButton(text="🛡 Admin panel")],
        [KeyboardButton(text="🚫 Spamdan chiqish")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎁 BONUS PREMIUM ga xush kelibsiz!\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=menu
    )

@dp.message(lambda message: message.text == "👑 Premium olish")
async def premium(message: Message):
    await message.answer("Premium olish bo‘limi tayyorlanmoqda.")

@dp.message(lambda message: message.text == "📢 Reklama joylash")
async def reklama(message: Message):
    await message.answer("Reklama joylash bo‘limi tayyorlanmoqda.")

@dp.message(lambda message: message.text == "🛡 Admin panel")
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID or ADMIN_ID == 0:
        await message.answer("⛔ Sizda admin ruxsati yo‘q.")
        return
    await message.answer("Admin panel tayyorlanmoqda.")

@dp.message(lambda message: message.text == "🚫 Spamdan chiqish")
async def spam(message: Message):
    await message.answer(
        "Spam cheklovi bo‘yicha yordam beraman.\n"
        "Muammoingizni yozib yuboring."
    )

async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
