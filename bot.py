import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

TOKEN = "8902951037:AAGUmJd2xLIsst3QAmjwDWnIXHmtoQbOdZU"

GROUP_CHAT_ID = -1003851569073

THREAD_LUNA = 2
THREAD_LYUT = 3
THREAD_GENERAL = 4

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

MESSAGE_MAP = {}

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    welcome_text = "тут будет написано что надо писать тег бла бла бла"
    await message.answer(welcome_text)

@dp.message(F.chat.type == "private")
async def forward_to_group(message: types.Message):
    if not GROUP_CHAT_ID:
        return

    text = message.text or message.caption or ""
    text_lower = text.lower()

    # Выбираем ветку в зависимости от хэштега
    if "#луна" in text_lower:
        target_thread = THREAD_LUNA
    elif "#люц" in text_lower:
        target_thread = THREAD_LYUT
    else:
        target_thread = THREAD_GENERAL

    sent_message = await bot.copy_message(
        chat_id=GROUP_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        message_thread_id=target_thread
    )
    
    MESSAGE_MAP[sent_message.message_id] = message.from_user.id

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def reply_from_group(message: types.Message):
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

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
