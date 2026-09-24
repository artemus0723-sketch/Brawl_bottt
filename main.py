import os
import re
import cv2
import pytesseract
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# ==========================================
# НАСТРОЙКИ (Заполните своими данными)
# ==========================================
BOT_TOKEN = "8895895178:AAHYlkLlTbGCCNpyMYLIZF4NHbZ5PZmmvL8"  # Токен от @BotFather
ADMIN_CHAT_ID = 5267181585     # ID администратора или ID чата админов

# Если Tesseract установлен в системную папку на Windows, раскомментируйте строку ниже:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==========================================
# ЛОГИКА ОБРАБОТКИ С КУБКАМИ (OCR)
# ==========================================
def extract_trophies(image_path: str) -> int | None:
    """
    Вырезает область с кубками и считывает точное число,
    полностью игнорируя блок с количеством бойцов (104/104).
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    height, width, _ = img.shape

    # Вырезаем строго область, где находятся кубки (верхний центр)
    crop_ymin, crop_ymax = int(height * 0.10), int(height * 0.26)
    crop_xmin, crop_xmax = int(width * 0.35), int(width * 0.65)
    
    cropped_img = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]

    # Предобработка для четкости цифр
    gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    # Сканируем только цифры
    config = '--psm 6 -c tessedit_char_whitelist=0123456789'
    raw_text = pytesseract.image_to_string(thresh, config=config)
    digits_only = re.sub(r'\D', '', raw_text)

    # Если через бинаризацию не прочиталось, сканируем оригинал вырезки
    if not digits_only:
        raw_text = pytesseract.image_to_string(cropped_img, config=config)
        digits_only = re.sub(r'\D', '', raw_text)

    if digits_only:
        trophies = int(digits_only)
        # Валидация: защита от аномальных чисел (больше 85 000)
        if 50 <= trophies <= 85000:
            return trophies

    return None


def calculate_price(trophies: int) -> dict:
    """Расчет стоимости по вашим коэффициентам"""
    rate_rub = 0.08
    rate_uah = 0.04

    return {
        "trophies": trophies,
        "price_rub": round(trophies * rate_rub, 2),
        "price_uah": round(trophies * rate_uah, 2)
    }


# ==========================================
# ХЕНДЛЕРЫ БОТА
# ==========================================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Отправь мне скриншот профиля Brawl Stars, и я рассчитаю стоимость аккаунта.")


@dp.message(F.photo)
async def process_screenshot(message: types.Message):
    # ПРИНТ ДЛЯ ПРОВЕРКИ ОБНОВЛЕНИЯ КОДА:
    print("\n[INFO] --- ЗАПУЩЕНА НОВАЯ ВЕРСИЯ КОДА (С ОБРЕЗКОЙ КАДРА) ---\n")

    status_msg = await message.answer("🔍 Сканирую скриншот...")
    
    # Скачиваем полученное фото во временный файл
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    temp_filename = f"temp_{message.from_user.id}.jpg"
    await bot.download_file(file_info.file_path, temp_filename)

    try:
        # Распознаем кубки
        trophies = extract_trophies(temp_filename)
        user_mention = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

        if trophies:
            data = calculate_price(trophies)
            
            # Сообщение клиенту
            user_text = (
                f"📊 **Результат сканирования:**\n"
                f"🏆 Распознано кубков: ~{data['trophies']}\n\n"
                f"💰 **Предварительная оценка:**\n"
                f"• {data['price_uah']} грн\n"
                f"• {data['price_rub']} руб\n\n"
                f"Заявка передана администратору! ⏳"
            )
            await status_msg.edit_text(user_text, parse_mode="Markdown")

            # Отправка заявки администратору
            admin_text = (
                f"📩 **Новая заявка!**\n"
                f"От: {user_mention}\n"
                f"ID: `{message.from_user.id}`\n"
                f"🏆 Кубков на фото: ~{data['trophies']}\n"
                f"💰 Оценка: {data['price_uah']} грн / {data['price_rub']} руб\n\n"
                f"_(Зажмите сообщение и нажмите «Ответить», чтобы написать)_"
            )
            # Отправляем админу фото и детали
            await bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=photo.file_id,
                caption=admin_text,
                parse_mode="Markdown"
            )

        else:
            # Если не удалось корректно распознать кубки
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

    finally:
        # Удаляем временное фото после обработки
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
