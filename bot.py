import asyncio
from aiogram import Bot, Dispatcher, types

TOKEN = "8902951037:AAGUmJd2xLIsst3QAmjwDWnIXHmtoQbOdZU"

GROUP_ID = -1003851569073

THREADS = {
    "#луна": 2,     
    "#люц": 3,      
    "default": 4,   
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message()
async def sort_messages(message: types.Message):
    if message.chat.type != "private":
        return

    text = message.text or message.caption or ""

    target_thread_id = THREADS["default"]
    for tag, thread_id in THREADS.items():
        if tag != "default" and tag in text:
            target_thread_id = thread_id
            break

    try:
        await bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            message_thread_id=target_thread_id,
        )
        await message.answer("Сообщение успешно отсортировано! 🚀")
    except Exception as e:
        await message.answer("Произошла ошибка при отправке. Попробуйте позже.")
        print(f"Ошибка: {e}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())
