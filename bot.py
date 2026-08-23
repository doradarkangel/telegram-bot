import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

TOKEN = "8902951037:AAGUmJd2xLIsst3QAmjwDWnIXHmtoQbOdZU"
GROUP_CHAT_ID = -1003851569073
MESSAGE_THREAD_ID = None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

MESSAGE_MAP = {}

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    welcome_text = "Привет! 👋 Напиши свой вопрос или сообщение в этот чат, и мы ответим тебе в самое ближайшее время!"
    await message.answer(welcome_text)

@dp.message(F.chat.type == "private")
async def forward_to_group(message: types.Message):
    if not GROUP_CHAT_ID:
        return

    user = message.from_user
    user_info = f"📩 Сообщение от @{user.username or 'нет_ника'} (ID: `{user.id}`):"
    
    header_msg = await bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=user_info,
        message_thread_id=MESSAGE_THREAD_ID
    )

    forwarded = await message.forward(
        chat_id=GROUP_CHAT_ID,
        message_thread_id=MESSAGE_THREAD_ID
    )
    
    MESSAGE_MAP[forwarded.message_id] = user.id
    MESSAGE_MAP[header_msg.message_id] = user.id

    await message.answer("✅ Сообщение доставлено администраторам!")

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
            await message.react([types.ReactionTypeEmoji(emoji="👍")])
        except Exception as e:
            logging.error(f"Не удалось отправить ответ пользователю: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
