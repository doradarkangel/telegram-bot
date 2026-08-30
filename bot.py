import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Update

TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = -1003959716659

THREAD_LUNA = 28531
THREAD_LYUT = 28530
THREAD_GENERAL = 28553
THREAD_RUSY = 28533
THREAD_MELKA = 28537
THREAD_POHIT = 28538
THREAD_BUSIN = 28539
THREAD_LILIT = 42176
THREAD_SIGA = 43559

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

MESSAGE_MAP = {}
USER_LAST_TAG = {}

# Файл для постоянного хранения забаненных ID
BANNED_FILE = "banned.txt"

def load_banned_users():
    """Загружает список забаненных из файла при запуске бота"""
    if os.path.exists(BANNED_FILE):
        try:
            with open(BANNED_FILE, "r") as f:
                return set(int(line.strip()) for line in f if line.strip().isdigit())
        except Exception as e:
            logging.error(f"Ошибка загрузки файла банов: {e}")
    return set()

def save_banned_users(banned_set):
    """Сохраняет актуальный список забаненных в файл"""
    try:
        with open(BANNED_FILE, "w") as f:
            for uid in banned_set:
                f.write(f"{uid}\n")
    except Exception as e:
        logging.error(f"Ошибка сохранения файла банов: {e}")

# Загружаем баны при старте бота
BANNED_USERS = load_banned_users()

WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://telegram-bot-pr8q.onrender.com{WEBHOOK_PATH}"

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    welcome_text = """Напишите любое предложение 😌

❕Правила ❕

1. Не просите у админов личные данные - юз, имя, возраст, город и т. д.
Админы могут сообщать ту информацию что пожелают нужной, на вытягивайте ее из них. 

2. Обязательно отмечайте своего админа.
Чтобы ваше сообщение точно не потерялось, всегда ставьте тег нужного админа. Без тега сообщение может остаться без внимания так как у нас ветки в боте!

3. Админы - такие же люди: у них есть личное время и потребность в отдыхе. Если вы написали ночью и не получили ответа сразу, не стоит жаловаться.

4. Меняйте админа разумно.
Без веской причины менять ответственного админа нельзя. Вы можете сменить админа только 3 раза , затем выбирайте из тех что вас взяли, либо в конечном итоге будет - бан.

5. Если ваш админ не отвечает - пожалуйста, подождите: возможно, он занят или взял перерыв. Если администратор ушёл в рест (отпуск), дождитесь его возвращения либо в рамках разумного смените ответственного. Помните: администрации тоже нужен отдых.

Всю информацию о админах и изменениях - мы публикуем в нашем тгк : https://t.me/devilspalac"""
    await message.answer(welcome_text)

@dp.message(F.chat.type == "private")
async def forward_to_group(message: types.Message):
    if not GROUP_CHAT_ID:
        return
    
    user_id = message.from_user.id

    if user_id in BANNED_USERS:
        await message.answer("Вы забанены администратором")
        return  
    
    text = message.text or message.caption or ""
    text_lower = text.lower()

    target_thread = None
    if "#луна" in text_lower:
        target_thread = THREAD_LUNA
    elif "#люц" in text_lower:
        target_thread = THREAD_LYUT
    elif "#русый" in text_lower:
        target_thread = THREAD_RUSY
    elif "#мелкая" in text_lower:
        target_thread = THREAD_MELKA
    elif "#похититель" in text_lower:
        target_thread = THREAD_POHIT
    elif "#бусинка" in text_lower:
        target_thread = THREAD_BUSIN
    elif "#лилит" in text_lower:
        target_thread = THREAD_LILIT
    elif "пушистый" in text_lower:
        target_thread = THREAD_SIGA

    if not target_thread:
        if (message.sticker or message.voice or message.animation or message.video_note) and user_id in USER_LAST_TAG:
            target_thread = USER_LAST_TAG[user_id]
        else:
            if user_id in USER_LAST_TAG:
                del USER_LAST_TAG[user_id]
            target_thread = THREAD_GENERAL

    if target_thread != THREAD_GENERAL:
        USER_LAST_TAG[user_id] = target_thread

    forwarded = await message.forward(
        chat_id=GROUP_CHAT_ID,
        message_thread_id=target_thread
    )

    MESSAGE_MAP[forwarded.message_id] = user_id

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def reply_from_group(message: types.Message):
    text = message.text or message.caption or ""
    clean_text = text.strip()
    
    # 1. Универсальная и надежная проверка на рассылку
    if clean_text.startswith("/bc") or clean_text.startswith("/broadcast"):
        await handle_broadcast(message)
        return

    # 2. Проверка остальных команд
    if clean_text.startswith("/") or clean_text.startswith("//"):
        if clean_text.startswith("/ban"):
            await handle_ban(message)
            try:
                await message.delete()
            except Exception:
                pass
            return
        elif clean_text.startswith("/unban"):
            await handle_unban(message)
            try:
                await message.delete()
            except Exception:
                pass
            return
            
        await message.reply("Error command.")
        return

    # 3. Обычный ответ на сообщение пользователя в ветке
    if not message.reply_to_message:
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

async def handle_ban(message: types.Message):
    if not message.reply_to_message:
        await message.reply("⚠️ Сделай Reply (ответ) на сообщение пользователя, которого хочешь забанить, и напиши `/ban`")
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = MESSAGE_MAP.get(reply_to_id)

    if not user_id:
        await message.reply("❌ Не удалось найти пользователя по этому сообщению.")
        return

    BANNED_USERS.add(user_id)
    save_banned_users(BANNED_USERS)
    USER_LAST_TAG.pop(user_id, None)
    
    await message.reply(f"🚫 Пользователь (ID: `{user_id}`) забанен в боте.")

async def handle_unban(message: types.Message):
    if not message.reply_to_message:
        await message.reply("⚠️ Сделай Reply (ответ) на сообщение пользователя, которого хочешь разбанить, и напиши `/unban`")
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = MESSAGE_MAP.get(reply_to_id)

    if not user_id:
        await message.reply("❌ Не удалось найти пользователя по этому сообщению.")
        return

    if user_id in BANNED_USERS:
        BANNED_USERS.remove(user_id)
        save_banned_users(BANNED_USERS)
        await message.reply(f"✅ Пользователь (ID: `{user_id}`) разбанен.")
    else:
        await message.reply("ℹ️ Этот пользователь не находится в списке забаненных.")

async def handle_broadcast(message: types.Message):
    text_to_send = message.text or message.caption or ""
    
    # Аккуратно вырезаем саму команду (/bc или /broadcast) из текста/подписи
    broadcast_text = text_to_send.strip()
    for prefix in ["/broadcast", "/bc"]:
        if broadcast_text.startswith(prefix):
            broadcast_text = broadcast_text[len(prefix):].lstrip()
            break

    # Собираем всех уникальных пользователей, исключая забаненных
    all_users = list((set(USER_LAST_TAG.keys()) | set(MESSAGE_MAP.values())) - BANNED_USERS)
    
    if not all_users:
        await message.reply("❌ Нет пользователей для рассылки.")
        return

    for uid in all_users:
        try:
            # Если рассылка идет с картинкой, видео или анимацией — копируем медиа с новым текстом
            if message.photo or message.video or message.animation or message.document or message.sticker:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=broadcast_text if broadcast_text else message.caption
                )
            else:
                await bot.send_message(chat_id=uid, text=broadcast_text)
            
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Не удалось отправить рассылку юзеру {uid}: {e}")

    await message.reply("✅ Рассылка завершена.")

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
