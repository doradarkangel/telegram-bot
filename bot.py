import os
import logging
import asyncio
import asyncpg
import time
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Update

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
GROUP_CHAT_ID = -1003959716659

THREAD_LUNA = 28531
THREAD_LYUT = 28530
THREAD_GENERAL = 28553
THREAD_RUSY = 28533
THREAD_BUSIN = 28539
THREAD_LILIT = 42176
THREAD_SIGA = 43559
THREAD_ANGELSK = 140213
THREAD_SMERTN = 136939
THREAD_HOLOD = 191411

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

db_pool = None
BANNED_USERS = set()
REPORT_TO_BROADCAST = {}  # Связь ID отчета в группе с ID рассылки для быстрого удаления

WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://telegram-bot-pr8q.onrender.com{WEBHOOK_PATH}"

async def init_db():
    global db_pool, BANNED_USERS
    if DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL)
            logging.info("Успешное подключение к облачной базе данных!")
            
            async with db_pool.acquire() as connection:
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS banned_users (
                        user_id BIGINT PRIMARY KEY
                    );
                    CREATE TABLE IF NOT EXISTS user_tags (
                        user_id BIGINT PRIMARY KEY,
                        target_thread BIGINT
                    );
                    CREATE TABLE IF NOT EXISTS message_map (
                        forwarded_message_id BIGINT PRIMARY KEY,
                        user_id BIGINT
                    );
                    CREATE TABLE IF NOT EXISTS broadcast_messages (
                        id SERIAL PRIMARY KEY,
                        broadcast_id BIGINT,
                        user_id BIGINT,
                        message_id BIGINT
                    );
                """)
                
                rows = await connection.fetch("SELECT user_id FROM banned_users")
                BANNED_USERS = set(row["user_id"] for row in rows)
            logging.info(f"Загружено забаненных пользователей из БД: {len(BANNED_USERS)}")
            
        except Exception as e:
            logging.error(f"Ошибка подключения к БД: {e}")

async def get_user_by_message(forwarded_msg_id: int):
    if not db_pool:
        return None
    async with db_pool.acquire() as connection:
        row = await connection.fetchrow("SELECT user_id FROM message_map WHERE forwarded_message_id = $1", forwarded_msg_id)
        return row["user_id"] if row else None

async def save_message_mapping(forwarded_msg_id: int, user_id: int):
    if not db_pool:
        return
    async with db_pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO message_map (forwarded_message_id, user_id) 
            VALUES ($1, $2) 
            ON CONFLICT (forwarded_message_id) 
            DO UPDATE SET user_id = $2
            """,
            forwarded_msg_id, user_id
        )

async def get_user_thread(user_id: int):
    if not db_pool:
        return THREAD_GENERAL
    async with db_pool.acquire() as connection:
        row = await connection.fetchrow("SELECT target_thread FROM user_tags WHERE user_id = $1", user_id)
        return row["target_thread"] if row else THREAD_GENERAL

async def save_user_thread(user_id: int, thread_id: int):
    if not db_pool:
        return
    async with db_pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO user_tags (user_id, target_thread) 
            VALUES ($1, $2) 
            ON CONFLICT (user_id) 
            DO UPDATE SET target_thread = $2
            """,
            user_id, thread_id
        )

async def get_all_users_for_broadcast():
    if not db_pool:
        return []
    async with db_pool.acquire() as connection:
        rows = await connection.fetch("SELECT user_id FROM user_tags UNION SELECT user_id FROM message_map")
        return [row["user_id"] for row in rows]

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
Без веской причины менять ответственного админа нельзя. Вы можете сменить админа только 3 раза , выбирайте из тех что вас взяли, либо в конечном итоге будет - бан.

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
    
    # Текст или подпись к медиа (фото, видео, документ и т.д.)
    text = message.text or message.caption or ""
    text_lower = text.lower()

    target_thread = None
    if "#луна" in text_lower:
        target_thread = THREAD_LUNA
    elif "#люц" in text_lower:
        target_thread = THREAD_LYUT
    elif "#аид" in text_lower in text_lower:
        target_thread = THREAD_RUSY
    elif "#бусинка" in text_lower:
        target_thread = THREAD_BUSIN
    elif "#лилит" in text_lower:
        target_thread = THREAD_LILIT
    elif "#пушистый" in text_lower:
        target_thread = THREAD_SIGA
    elif "#ангельская" in text_lower:
        target_thread = THREAD_ANGELSK
    elif "#смертная" in text_lower:
        target_thread = THREAD_SMERTN
    elif "#холод" in text_lower:
        target_thread = THREAD_HOLOD

    if target_thread:
        # Если пользователь написал тег, сохраняем эту ветку за ним
        await save_user_thread(user_id, target_thread)
    else:
        # Если тега нет, подтягиваем прошлую ветку из базы. Новые пользователи получат THREAD_GENERAL.
        target_thread = await get_user_thread(user_id)

    try:
        # method message.forward отлично пересылает тексты, фото, кружочки, голосовые, видео и файлы
        forwarded = await message.forward(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=target_thread
        )
        await save_message_mapping(forwarded.message_id, user_id)
    except Exception as e:
        logging.error(f"ОШИБКА ПЕРЕСЫЛКИ: юзер {user_id}, ветка {target_thread}, ошибка: {e}")
        try:
            forwarded = await message.forward(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=THREAD_GENERAL
            )
            await save_message_mapping(forwarded.message_id, user_id)
            await message.answer("⚠️ Не удалось доставить сообщение в нужную ветку, оно перенаправлено в общую ветку.")
            return
        except Exception as e2:
            logging.error(f"Не удалось отправить даже в General: {e2}")

        await message.answer("⚠️ Не удалось доставить сообщение администраторам. Попробуй написать с тегом.")

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def reply_from_group(message: types.Message):
    if message.from_user.id == bot.id:
        return

    text = message.text or message.caption or ""
    clean_text = text.strip()
    
    if clean_text.startswith("/bc") or clean_text.startswith("/broadcast"):
        await handle_broadcast(message)
        return

    if clean_text.startswith("/delbc"):
        await handle_delete_broadcast(message)
        try:
            await message.delete()
        except Exception:
            pass
        return

    if clean_text.startswith("/banpz"):
        await handle_ban(message)
        try:
            await message.delete()
        except Exception:
            pass
        return
    elif clean_text.startswith("/unbanpz"):
        await handle_unban(message)
        try:
            await message.delete()
        except Exception:
            pass
        return

    if clean_text.startswith("/") or clean_text.startswith("//"):
        await message.reply("Error command.")
        return

    if not message.reply_to_message:
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = await get_user_by_message(reply_to_id)

    if user_id:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str or "forbidden" in err_str:
                await message.reply("Bot was blocked by this user.")
            else:
                logging.error(f"Не удалось отправить ответ пользователю: {e}")

async def handle_ban(message: types.Message):
    if not message.reply_to_message:
        await message.reply("⚠ Сделай Reply на сообщение пользователя для бана и напиши `/banpz`")
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = await get_user_by_message(reply_to_id)

    if not user_id:
        await message.reply("❌ Не удалось найти пользователя.")
        return

    if db_pool:
        async with db_pool.acquire() as connection:
            await connection.execute(
                "INSERT INTO banned_users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                user_id
            )

    BANNED_USERS.add(user_id)
    await message.reply(f"🚫 Пользователь (ID: `{user_id}`) забанен.")

async def handle_unban(message: types.Message):
    if not message.reply_to_message:
        await message.reply("⚠️ Сделай Reply на сообщение пользователя для разбана и напиши `/unbanpz`")
        return

    reply_to_id = message.reply_to_message.message_id
    user_id = await get_user_by_message(reply_to_id)

    if not user_id:
        await message.reply("❌ Не удалось найти пользователя.")
        return

    if user_id in BANNED_USERS:
        if db_pool:
            async with db_pool.acquire() as connection:
                await connection.execute("DELETE FROM banned_users WHERE user_id = $1", user_id)

        BANNED_USERS.remove(user_id)
        await message.reply(f"✅ Пользователь (ID: `{user_id}`) разбанен.")
    else:
        await message.reply("ℹ️ Пользователь не в бане.")

async def handle_broadcast(message: types.Message):
    text_to_send = message.text or message.caption or ""
    broadcast_text = text_to_send.strip()
    
    for prefix in ["/broadcast", "/bc"]:
        if broadcast_text.lower().startswith(prefix):
            broadcast_text = broadcast_text[len(prefix):].lstrip()
            break

    db_users = await get_all_users_for_broadcast()
    all_users = list(set(db_users) - BANNED_USERS)
    
    if not all_users:
        await message.reply("❌ Нет пользователей для рассылки.")
        return

    broadcast_id = int(time.time())
    success_count = 0
    blocked_count = 0

    for uid in all_users:
        try:
            if message.photo or message.video or message.animation or message.document or message.audio or message.sticker or message.voice or message.video_note:
                sent_msg = await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=broadcast_text if broadcast_text else None
                )
            else:
                sent_msg = await bot.send_message(
                    chat_id=uid,
                    text=broadcast_text,
                    entities=message.entities
                )
            
            if db_pool and sent_msg:
                async with db_pool.acquire() as connection:
                    await connection.execute(
                        "INSERT INTO broadcast_messages (broadcast_id, user_id, message_id) VALUES ($1, $2, $3)",
                        broadcast_id, uid, sent_msg.message_id
                    )

            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str or "forbidden" in err_str:
                blocked_count += 1
            else:
                logging.error(f"Не удалось отправить рассылку юзеру {uid}: {e}")

    report_msg = await message.reply(
        f"✅ Рассылка завершена.\n\n"
        f"📬 Получили сообщение: **{success_count}**\n"
        f"🚫 Заблокировали бота: **{blocked_count}**\n\n"
        f"🆔 ID рассылки: `{broadcast_id}`\n"
        f"*(Чтобы удалить эту рассылку у всех, сделай Reply на это сообщение и напиши `/delbc`)*"
    )
    
    REPORT_TO_BROADCAST[report_msg.message_id] = broadcast_id

async def handle_delete_broadcast(message: types.Message):
    broadcast_id_to_delete = None

    if message.reply_to_message and message.reply_to_message.message_id in REPORT_TO_BROADCAST:
        broadcast_id_to_delete = REPORT_TO_BROADCAST[message.reply_to_message.message_id]
    else:
        parts = (message.text or "").split()
        if len(parts) > 1 and parts[1].isdigit():
            broadcast_id_to_delete = int(parts[1])

    if not broadcast_id_to_delete:
        await message.reply("⚠️ Сделай Reply на сообщение с отчетом о рассылке и напиши `/delbc`, либо укажи ID: `/delbc <ID>`")
        return

    if not db_pool:
        await message.reply("❌ База данных недоступна.")
        return

    async with db_pool.acquire() as connection:
        rows = await connection.fetch("SELECT user_id, message_id FROM broadcast_messages WHERE broadcast_id = $1", broadcast_id_to_delete)
        
    if not rows:
        await message.reply("❌ Рассылка с таким ID не найдена в базе данных.")
        return

    deleted_count = 0
    failed_count = 0

    for row in rows:
        try:
            await bot.delete_message(chat_id=row["user_id"], message_id=row["message_id"])
            deleted_count += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed_count += 1

    async with db_pool.acquire() as connection:
        await connection.execute("DELETE FROM broadcast_messages WHERE broadcast_id = $1", broadcast_id_to_delete)

    await message.reply(
        f"🗑 Рассылка `{broadcast_id_to_delete}` удалена.\n\n"
        f"✅ Успешно удалено у пользователей: **{deleted_count}**\n"
        f"ℹ️ Не удалось удалить (удалили чат/прошло много времени): **{failed_count}**"
    )

async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        telegram_update = Update(**data)
        await dp.feed_update(bot=bot, update=telegram_update)
        return web.Response(status=200)
    exceptException as e:
        logging.error(f"Ошибка при обработке вебхука: {e}")
        return web.Response(status=500)

async def handle_ping(request: web.Request):
    return web.Response(text="Бот успешно работает через Webhooks!")

async def main():
    await init_db()

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
