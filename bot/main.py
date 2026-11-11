import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TOKEN or not WEBHOOK_URL or not WEBHOOK_SECRET:
    raise RuntimeError("Maxfiy sozlamalar kiritilmagan!")

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

@dp.message(lambda m: m.text == "👑 Premium olish")
async def premium(message: Message):
    await message.answer("Premium bo‘limi tayyorlanmoqda.")

@dp.message(lambda m: m.text == "📢 Reklama joylash")
async def reklama(message: Message):
    await message.answer("Reklama bo‘limi tayyorlanmoqda.")

@dp.message(lambda m: m.text == "🛡 Admin panel")
async def admin(message: Message):
    if not ADMIN_ID or message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Ruxsat yo‘q.")
        return
    await message.answer("Admin panel tayyorlanmoqda.")

@dp.message(lambda m: m.text == "🚫 Spamdan chiqish")
async def spam(message: Message):
    await message.answer(
        "Spam cheklovi bo‘yicha muammoingizni yozing."
    )

async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{WEBHOOK_URL}/webhook",
        secret_token=WEBHOOK_SECRET
    )

async def main():
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path="/webhook")

    setup_application(app, dp, bot=bot)

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000"))
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
