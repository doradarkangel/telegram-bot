import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import Update

TOKEN = "8866396965:AAET0Ra7IFCjx5Yspm4xYH5ujEPUjyGMggM"
GROUP_CHAT_ID = -1003959716659

THREAD_LUNA = 28531
THREAD_LYUT = 28530
THREAD_GENERAL = 28553
THREAD_RUSY = 28533
THREAD_USHAST = 28536
THREAD_MELKA = 28537
THREAD_POHIT = 28538
THREAD_BUSIN = 28539

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

MESSAGE_MAP = {}

WEBHOOK_PATH = f"/{TOKEN}"

WEBHOOK_URL = f"https://telegram-bot-pr8q.onrender.com{WEBHOOK_PATH}"

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    welcome_text = """Напишите любое предложение 😌

❕Правила ❕

1. Не просите у админов личные данные - юз, имя, возраст, город и т. д.
Админы могут сообщать ту информацию что пожелают нужной, на вытягивайте ее из них. 

2. Обязательно отмечайте своего админа.
Чтобы ваше сообщение точно не потерялось, всегда ставьте тег нужного админа. Без тега сообщение может остаться без внимания так как у нас ветки в боте!

3. Админы - такие же люди: у них есть личное время и потребность в отдыхе. Если вы написали ночью и не получили ответа сразу, не стоит жаловаться.

4. Меняйте админа разумно.
Без веской причины менять ответственного админа нельзя. Вы можете сменить админа только 3 раза , затем выбирайте из тех что вас взяли, либо в конечном итоге будет - бан.

5. Если ваш админ не отвечает - пожалуйста, подождите: возможно, он занят или взял перерыв. Если администратор ушёл в рест (отпуск), дождитесь его возвращения либо в рамках разумного смените ответственного. Помните: администрации тоже нужен отдых.

Всю информацию о админах и изменениях - мы публикуем в нашем тгк : https://t.me/devilspalac"""
    await message.answer(welcome_text)

@dp.message(F.chat.type == "private")
async def forward_to_group(message: types.Message):
    if not GROUP_CHAT_ID:
        return
    
    text = message.text or message.caption or ""
    text_lower = text.lower()

    if "#луна" in text_lower:
        target_thread = THREAD_LUNA
    elif "#люц" in text_lower:
        target_thread = THREAD_LYUT
    elif "#русый" in text_lower:
        target_thread = THREAD_RUSY
    elif "#ушастая" in text_lower:
        target_thread = THREAD_USHAST
    elif "#мелкая" in text_lower:
        target_thread = THREAD_MELKA
    elif "#похититель" in text_lower:
        target_thread = THREAD_POHIT
    elif "#бусинка" in text_lower:
        target_thread = THREAD_BUSIN
    else:
        target_thread = THREAD_GENERAL

    forwarded = await message.forward(
        chat_id=GROUP_CHAT_ID,
        message_thread_id=target_thread
    )

    MESSAGE_MAP[forwarded.message_id] = message.from_user.id

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def reply_from_group(message: types.Message):
    if not message.reply_to_message:
        return

    text = message.text or message.caption or ""
    if text.startswith("/") or text.startswith("//"):
        await message.reply("Error command.")
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = MESSAGE_MAP.get(reply_to_id)

    if user_id:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as e:
            logging.error(f"Не удалось отправить ответ пользователю: {e}")

async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        telegram_update = Update(**data)
        await dp.feed_update(bot=bot, update=telegram_update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Ошибка при обработке вебхука: {e}")
        return web.Response(status=500)

async def handle_ping(request: web.Request):
    return web.Response(text="Бот успешно работает через Webhooks!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, allowed_updates=["message", "callback_query"])
    logging.info(f"Вебхук установлен на адрес: {WEBHOOK_URL}")

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/", handle_ping)

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logging.info(f"Веб-сервер запущен на порту {port}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
