import os
import re
import cv2
import pytesseract
import logging
import asyncio
import numpy as np
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Для Windows при необходимости укажите путь к tesseract.exe:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
# ТОЧНЫЙ АЛГОРИТМ OCR
# ==========================================
def preprocess_for_ocr(cropped_bgr):
    """Предобработка области с цифрами для надежного считывания."""
    resized = cv2.resize(cropped_bgr, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    
    # Выделение белого цвета цифр кубков через HSV
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 160])
    upper_white = np.array([180, 60, 255])
    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    
    # Инверсия: черные цифры на белом фоне
    inverted = cv2.bitwise_not(mask_white)
    return inverted, resized


def parse_number_from_image(img_input) -> int | None:
    config = '--psm 6 -c tessedit_char_whitelist=0123456789'
    raw_text = pytesseract.image_to_string(img_input, config=config)
    found = re.findall(r'\d+', raw_text)
    valid = [int(n) for n in found if 500 <= int(n) <= 200000]
    return valid[0] if valid else None


def extract_trophies(image_path: str) -> int | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        # 1. Удаляем черные рамки со скриншота экрана телефона
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_img, 20, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            x, y, crop_w, crop_h = cv2.boundingRect(c)
            if crop_w > 100 and crop_h > 100:
                img = img[y:y+crop_h, x:x+crop_w]

        h, w, _ = img.shape

        # 2. Детекция золотого кубка (по цвету HSV)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Желтый/золотой цвет иконки кубка
        lower_yellow = np.array([15, 120, 120])
        upper_yellow = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Ограничиваем область поиска кубка верхней частью экрана
        search_zone = yellow_mask[0:int(h * 0.4), int(w * 0.3):int(w * 0.8)]
        y_indices, x_indices = np.where(search_zone > 0)

        if len(x_indices) > 0 and len(y_indices) > 0:
            # Находим координаты иконки кубка
            min_x, max_x = np.min(x_indices) + int(w * 0.3), np.max(x_indices) + int(w * 0.3)
            min_y, max_y = np.min(y_indices), np.max(y_indices)

            # Берем область СТРОГО СПРАВА от кубка (где стоят цифры)
            crop_ymin = max(0, min_y - int((max_y - min_y) * 0.3))
            crop_ymax = min(h, max_y + int((max_y - min_y) * 0.5))
            crop_xmin = max_x
            crop_xmax = min(w, max_x + int((max_x - min_x) * 6.5))

            cropped_digits = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]

            if cropped_digits.size > 0:
                prep_img, _ = preprocess_for_ocr(cropped_digits)
                val = parse_number_from_image(prep_img)
                if val:
                    return val

        # 3. Запасной вариант: кадрирование по относительным координатам
        crop_ymin, crop_ymax = int(h * 0.10), int(h * 0.28)
        crop_xmin, crop_xmax = int(w * 0.50), int(w * 0.75)
        cropped_fallback = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]

        if cropped_fallback.size > 0:
            prep_fallback, resized_fallback = preprocess_for_ocr(cropped_fallback)
            
            # Попытка считывания с маски
            val = parse_number_from_image(prep_fallback)
            if val:
                return val
            
            # Попытка считывания с оттенков серого
            gray_fallback = cv2.cvtColor(resized_fallback, cv2.COLOR_BGR2GRAY)
            val_gray = parse_number_from_image(gray_fallback)
            if val_gray:
                return val_gray

    except Exception as e:
        logging.error(f"Ошибка при OCR: {e}")

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

        # Выполняем OCR в отдельном потоке
        trophies = await asyncio.to_thread(extract_trophies, temp_filename)
        
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
