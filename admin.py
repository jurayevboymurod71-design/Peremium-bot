"""Premium Bot — Telegram bot + admin paneli (aiogram 3).

Ishga tushirish:
  pip install "aiogram>=3.7,<4"   # (aiohttp avtomatik o‘rnatiladi)
  BOT_TOKEN=... ADMIN_IDS=123456789 WEBAPP_URL=https://sizning-sayt.uz python bot.py

ADMIN_IDS — vergul bilan ajratilgan admin Telegram ID lari.
WEBAPP_URL — Mini App manzili (https). DB_PATH — SQLite fayl (standart: premium.db).
Backend (FastAPI) shu bazadan foydalanadi va tasdiqlangan hodisalarni
record_ad_view() / record_channel_join() orqali yozadi.
"""
import asyncio, html, logging, os, sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, BotCommandScopeChat, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, MenuButtonWebApp, Message,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
DB_PATH = os.getenv("DB_PATH", "premium.db")
SLOTS = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
  referrer_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sponsor_channels(slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 1 AND 5),
  chat_id TEXT NOT NULL, title TEXT, link TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS channel_joins(user_id INTEGER, slot INTEGER, chat_id TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, chat_id));
CREATE TABLE IF NOT EXISTS ad_views(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
  event_id TEXT UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


def q(sql, args=(), write=False):
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        cur = c.execute(sql, args)
        if write:
            c.commit()
            return cur.rowcount
        return cur.fetchall()
    finally:
        c.close()


def init_db():
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    c.close()


# --- Backend uchun: faqat server tomonida TASDIQLANGAN hodisalar uchun chaqiring ---
def record_ad_view(user_id: int, event_id: str) -> bool:
    """Provayder tasdiqlagan reklama ko‘rishini yozadi (takroriy event_id e’tiborga olinmaydi)."""
    return q("INSERT OR IGNORE INTO ad_views(user_id,event_id) VALUES(?,?)", (user_id, event_id), True) == 1


def record_channel_join(user_id: int, slot: int) -> bool:
    """Bot API orqali obuna tasdiqlangandan keyin chaqiring. Bir kanal uchun bir marta yoziladi."""
    r = q("SELECT chat_id FROM sponsor_channels WHERE slot=? AND active=1", (slot,))
    return bool(r) and q("INSERT OR IGNORE INTO channel_joins(user_id,slot,chat_id) VALUES(?,?,?)",
                         (user_id, slot, r[0]["chat_id"]), True) == 1


# ------------------------------- Oddiy foydalanuvchi -------------------------------
pub = Router()


@pub.message(CommandStart())
async def start(m: Message, command: CommandObject):
    u = m.from_user
    a = command.args or ""
    ref = int(a[4:]) if a.startswith("ref_") and a[4:].isdigit() else None
    if ref == u.id or (ref and not q("SELECT 1 FROM users WHERE id=?", (ref,))):
        ref = None
    # INSERT OR IGNORE: mavjud foydalanuvchining referal egasi o‘zgarmaydi
    q("INSERT OR IGNORE INTO users(id,username,first_name,referrer_id) VALUES(?,?,?,?)",
      (u.id, u.username, u.first_name, ref), True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="🚀 Mini Appni ochish", web_app=WebAppInfo(url=WEBAPP_URL))]]) if WEBAPP_URL else None
    await m.answer(
        f"👋 Salom, <b>{html.escape(u.first_name or 'do‘st')}</b>!\n\n"
        "🎁 Telegram <b>Stars</b> va <b>Premium</b> olish uchun Mini Appni oching: reklama ko‘ring, "
        "homiy kanallarga obuna bo‘ling va do‘stlaringizni taklif qiling, olmos to‘plang.",
        reply_markup=kb)


# --------------------------------- Admin paneli ---------------------------------
adm = Router()
adm.message.filter(F.from_user.id.in_(ADMIN_IDS))
adm.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


class Ch(StatesGroup):
    wait = State()


KB = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Homiy kanallar")],
    [KeyboardButton(text="🔄 Kanalni almashtirish"), KeyboardButton(text="🏠 Chiqish")],
], resize_keyboard=True, input_field_placeholder="Admin paneli")


def chans():
    return {r["slot"]: r for r in q("SELECT * FROM sponsor_channels")}


def cname(r):
    t = html.escape(r["title"] or "")
    return f'<a href="{r["link"]}">{t}</a>' if r["link"] else t


@adm.message(Command("admin"))
async def panel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("🛠 <b>Admin paneli</b>\nKerakli bo‘limni tanlang 👇", reply_markup=KB)


@adm.message(F.text == "📊 Statistika")
async def stats(m: Message, state: FSMContext):
    await state.clear()
    users = q("SELECT COUNT(*) n FROM users")[0]["n"]
    ads = q("SELECT COUNT(*) n FROM ad_views")[0]["n"]
    ch, lines = chans(), []
    for s in range(1, SLOTS + 1):
        r = ch.get(s)
        if not r:
            lines.append(f"{s}. — (bo‘sh)")
            continue
        n = q("SELECT COUNT(*) n FROM channel_joins WHERE chat_id=?", (r["chat_id"],))[0]["n"]
        lines.append(f"{s}. {cname(r)} — <b>{n}</b> ta obuna")
    await m.answer(f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: <b>{users}</b>\n"
                   f"▶️ Ko‘rilgan reklamalar: <b>{ads}</b>\n\n"
                   "📢 <b>Homiy kanallar</b> (topshiriqni bajarganlar):\n" + "\n".join(lines))


@adm.message(F.text == "📢 Homiy kanallar")
async def lst(m: Message, state: FSMContext):
    await state.clear()
    ch = chans()
    await m.answer("📢 <b>Homiy kanallar</b>\n\n" + "\n".join(
        f"{s}. {cname(ch[s])} · <code>{ch[s]['chat_id']}</code>" if s in ch else f"{s}. — (bo‘sh)"
        for s in range(1, SLOTS + 1)))


@adm.message(F.text == "🔄 Kanalni almashtirish")
async def pick(m: Message, state: FSMContext):
    await state.clear()
    ch = chans()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=f"{s}-kanal: " + (ch[s]["title"] if s in ch else "bo‘sh"), callback_data=f"slot:{s}")]
        for s in range(1, SLOTS + 1)])
    await m.answer("Qaysi o‘rindagi kanalni almashtirasiz?", reply_markup=kb)


@adm.message(F.text == "🏠 Chiqish")
async def leave(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Panel yopildi. Qayta ochish: /admin", reply_markup=ReplyKeyboardRemove())


@adm.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.", reply_markup=KB)


@adm.callback_query(F.data.startswith("slot:"))
async def slot(c: CallbackQuery, state: FSMContext):
    s = int(c.data.split(":")[1])
    if not 1 <= s <= SLOTS:
        return await c.answer()
    await state.set_state(Ch.wait)
    await state.update_data(slot=s)
    await c.message.answer(
        f"<b>{s}-kanal</b> uchun yangi kanalni yuboring:\n"
        "• @username yoki -100... ID\n• yoki kanaldan biror postni forward qiling\n\n"
        "⚠️ Bot kanalda administrator bo‘lishi shart (obunani tekshirish uchun).\nBekor qilish: /cancel")
    await c.answer()


@adm.message(Ch.wait)
async def setch(m: Message, state: FSMContext, bot: Bot):
    s = (await state.get_data())["slot"]
    fo = getattr(m, "forward_origin", None)
    ref = fo.chat.id if fo is not None and getattr(fo, "type", "") == "channel" else (m.text or "").strip()
    if isinstance(ref, str) and ref.lstrip("-").isdigit():
        ref = int(ref)
    if not ref:
        return await m.answer("Kanal @username yoki ID yuboring.")
    try:
        chat = await bot.get_chat(ref)
    except Exception:
        return await m.answer("❌ Kanal topilmadi. @username yoki ID ni tekshiring.")
    if chat.type != "channel":
        return await m.answer("❌ Bu kanal emas. Kanal yuboring.")
    try:
        me = await bot.get_chat_member(chat.id, bot.id)
    except Exception:
        me = None
    if not me or me.status not in ("administrator", "creator"):
        return await m.answer("❌ Avval botni shu kanalga administrator qiling, so‘ng qayta yuboring.")
    link = f"https://t.me/{chat.username}" if chat.username else None
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except Exception:
            link = None
    q("INSERT OR REPLACE INTO sponsor_channels(slot,chat_id,title,link,active) VALUES(?,?,?,?,1)",
      (s, str(chat.id), chat.title or str(chat.id), link), True)
    await state.clear()
    await m.answer(f"✅ {s}-kanal almashtirildi: <b>{html.escape(chat.title or '')}</b>\n"
                   "Yangi kanal statistikasi 0 dan boshlanadi, eskisi bazada saqlanadi.", reply_markup=KB)


# ------------------------------------- Ishga tushirish -------------------------------------
async def start_health_server():
    """Render kabi hostinglar PORT talab qiladi: oddiy "ok" javob beruvchi mini-server."""
    port = int(os.getenv("PORT", "0"))
    if not port:
        return
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()


async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN o‘rnatilmagan")
    init_db()
    await start_health_server()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(adm, pub)
    # Botga birinchi kirganda START tugmasi ustida chiqadigan yozuv
    await bot.set_my_description("🎁 Telegram Stars va Premium olish uchun START tugmasini bosing! 👇")
    await bot.set_my_short_description("🎁 Stars va Premium — START ni bosing!")
    await bot.set_my_commands([BotCommand(command="start", description="Boshlash")])
    for a in ADMIN_IDS:
        try:
            await bot.set_my_commands([BotCommand(command="start", description="Boshlash"),
                                       BotCommand(command="admin", description="Admin paneli")],
                                      scope=BotCommandScopeChat(chat_id=a))
        except Exception:
            pass
    if WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Ochish", web_app=WebAppInfo(url=WEBAPP_URL)))
        except Exception:
            logging.exception("Menu tugmasi o‘rnatilmadi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
