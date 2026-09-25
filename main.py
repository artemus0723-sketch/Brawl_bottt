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

# Для Windows может потребоваться указать путь к Tesseract:
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
# УЛУЧШЕННЫЙ АЛГОРИТМ OCR ДЛЯ BRAWL STARS
# ==========================================
def extract_trophies(image_path: str) -> int | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        h, w, _ = img.shape

        # Если скриншот с черными рамками по краям — обрезаем их
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray_img, 15, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            x, y, crop_w, crop_h = cv2.boundingRect(c)
            if crop_w > 100 and crop_h > 100:
                img = img[y:y+crop_h, x:x+crop_w]
                h, w, _ = img.shape

        # 1. Скорректированная зона блока «ПУТЬ К СЛАВЕ» с числом кубков
        crop_ymin, crop_ymax = int(h * 0.12), int(h * 0.28)
        crop_xmin, crop_xmax = int(w * 0.52), int(w * 0.72)

        cropped = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]
        if cropped.size == 0:
            return None

        # Увеличиваем изображение для точного считывания
        resized = cv2.resize(cropped, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)

        # Выделение чисто белого цвета цифр кубков через HSV
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)

        # Инвертируем: делаем цифры черными на белом фоне (лучший формат для Tesseract)
        inverted = cv2.bitwise_not(mask_white)

        config = '--psm 6 -c tessedit_char_whitelist=0123456789'

        # Попытка 1: чтение по выделенной маске white/inverted
        raw_text = pytesseract.image_to_string(inverted, config=config)
        found = re.findall(r'\d+', raw_text)
        valid = [int(n) for n in found if 500 <= int(n) <= 200000]
        if valid:
            return valid[0]

        # Попытка 2: чтение по обычному серому полутону
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        _, thresh_gray = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        raw_text_gray = pytesseract.image_to_string(thresh_gray, config=config)
        found_gray = re.findall(r'\d+', raw_text_gray)
        valid_gray = [int(n) for n in found_gray if 500 <= int(n) <= 200000]
        if valid_gray:
            return valid_gray[0]

        # Попытка 3: Резервный поиск по более широкой верхней части экрана
        backup_crop = img[int(h * 0.05):int(h * 0.40), int(w * 0.40):int(w * 0.80)]
        backup_gray = cv2.cvtColor(backup_crop, cv2.COLOR_BGR2GRAY)
        raw_backup = pytesseract.image_to_string(backup_gray, config=config)
        found_backup = re.findall(r'\d+', raw_backup)
        valid_backup = [int(n) for n in found_backup if 500 <= int(n) <= 200000]
        if valid_backup:
            return valid_backup[0]

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

        # Синхронная функция OCR запускается асинхронно, чтобы не задерживать бота
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
