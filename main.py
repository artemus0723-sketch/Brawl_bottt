import os
import re
import cv2
import logging
import asyncio
import numpy as np
import easyocr
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализируем модель EasyOCR для русского и английского языков (загружается 1 раз при старте)
# gpu=False использует CPU (поставьте gpu=True, если есть видеокарта Nvidia)
reader = easyocr.Reader(['ru', 'en'], gpu=False)

# ==========================================
# ПОЛУЧЕНИЕ ПЕРЕМЕННЫХ
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8895895178:AAHYlkLlTbGCCNpyMYLIZF4NHbZ5PZmmvL8")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "5267181585"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# КЛАВИАТУРА
# ==========================================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="связь с админом"), KeyboardButton(text="Правила 📄")],
        [KeyboardButton(text="👾 Продать аккаунт (По фото) 👾")]
    ],
    resize_keyboard=True
)

# ==========================================
# НАДЁЖНЫЙ АЛГОРИТМ OCR НА БАЗЕ EASYOCR
# ==========================================
def extract_trophies_easyocr(image_path: str) -> int | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        # 1. Обрезаем черные рамки телефона по краям (если они есть)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            x, y, crop_w, crop_h = cv2.boundingRect(c)
            if crop_w > 100 and crop_h > 100:
                img = img[y:y+crop_h, x:x+crop_w]

        # 2. Запускаем распознавание с помощью EasyOCR
        # EasyOCR возвращает список: [ [bbox, text, confidence], ... ]
        results = reader.readtext(img)

        candidates = []
        
        # Сканируем все найденные блоки текста
        for bbox, text, prob in results:
            # Очищаем текст, оставляем только цифры
            clean_text = re.sub(r'\D', '', text)
            if clean_text:
                val = int(clean_text)
                # Кубки обычно находятся в диапазоне от 500 до 200,000
                if 500 <= val <= 200000:
                    # Получаем Y-координату центра найденного блока
                    top_y = bbox[0][1]
                    candidates.append((val, top_y, prob))

        if not candidates:
            return None

        # Кубки в профиле Brawl Stars («ПУТЬ К СЛАВЕ») всегда находятся в ВЕРХНЕЙ части экрана
        # Сортируем кандидатов по Y-координате (чем выше на экране, тем вероятнее это кубки)
        candidates.sort(key=lambda item: item[1])

        # Возвращаем первое подходящее число из верхней зоны
        return candidates[0][0]

    except Exception as e:
        logging.error(f"Ошибка при работе EasyOCR: {e}")

    return None


def calculate_price(trophies: int) -> dict:
    rate_rub = 0.08
    rate_uah = 0.04
    return {
        "trophies": trophies,
        "price_rub": round(trophies * rate_rub, 2),
        "price_uah": round(trophies * rate_uah, 2)
    }

# ==========================================
# ХЭНДЛЕРЫ КОМАНД И КНОПОК
# ==========================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Отправь мне скриншот профиля Brawl Stars, и я рассчитаю стоимость аккаунта.",
        reply_markup=main_keyboard
    )


@dp.message(F.text == "👾 Продать аккаунт (По фото) 👾")
async def process_sell_button(message: types.Message):
    await message.answer(
        "📸 Пожалуйста, отправьте скриншот вашего профиля Brawl Stars в чат."
    )


@dp.message(F.text == "связь с админом")
async def process_admin_contact(message: types.Message):
    await message.answer("Для связи с администратором пишите: @yrodochk")


@dp.message(F.text == "Правила 📄")
async def process_rules(message: types.Message):
    await message.answer(
        "📋 **Правила скупки:**\n\n"
        "1. Принимаются только оригинальные скриншоты профиля.\n"
        "2. Покупаем только от 5000🏆.\n"
        "3. Окончательную сумму утверждает администратор.",
        parse_mode="Markdown"
    )


@dp.message(F.photo)
async def process_screenshot(message: types.Message):
    status_msg = await message.answer("🔍 Сканирую скриншот...")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    temp_filename = f"temp_{message.from_user.id}_{message.message_id}.jpg"

    try:
        await bot.download_file(file_info.file_path, temp_filename)

        # Обработка изображения нейросетью EasyOCR в отдельном потоке
        trophies = await asyncio.to_thread(extract_trophies_easyocr, temp_filename)
        
        user_mention = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

        if trophies:
            data = calculate_price(trophies)
            user_text = (
                f"📊 **Результат сканирования:**\n"
                f"🏆 Распознано кубков: ~{data['trophies']}\n\n"
                f"💰 **Предварительная оценка:**\n"
                f"• {data['price_uah']} грн\n"
                f"• {data['price_rub']} руб\n\n"
                f"Заявка передана администратору! ⏳"
            )
            await status_msg.edit_text(user_text, parse_mode="Markdown")

            admin_text = (
                f"📩 **Новая заявка!**\n"
                f"От: {user_mention}\n"
                f"ID: `{message.from_user.id}`\n"
                f"🏆 Кубков на фото: ~{data['trophies']}\n"
                f"💰 Оценка: {data['price_uah']} грн / {data['price_rub']} руб\n\n"
                f"_(Зажмите сообщение и нажмите «Ответить», чтобы написать)_"
            )
            await bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=photo.file_id,
                caption=admin_text,
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text(
                "⚠️ Не удалось автоматически считать кубки со скриншота.\n"
                "Заявка отправлена администратору на ручную проверку!"
            )
            await bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=photo.file_id,
                caption=f"⚠️ **Ошибка OCR!** Скриншот от {user_mention} (`{message.from_user.id}`). Требуется ручная оценка.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Ошибка при обработке скриншота: {e}")
        await status_msg.edit_text("❌ Произошла ошибка при обработке скриншота.")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
