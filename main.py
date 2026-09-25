import os
import re
import cv2
import pytesseract
import logging
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

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
# ТОЧНЫЙ АЛГОРИТМ OCR ДЛЯ BRAWL STARS
# ==========================================
def extract_trophies(image_path: str) -> int | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        h, w, _ = img.shape

        # Если картинка вертикальная (скриншот экрана телефона с черными рамками)
        # Убираем верхние и нижние черные поля
        if h > w:
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray_img, 15, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = max(contours, key=cv2.contourArea)
                x, y, crop_w, crop_h = cv2.boundingRect(c)
                if crop_w > 100 and crop_h > 100:
                    img = img[y:y+crop_h, x:x+crop_w]
                    h, w, _ = img.shape

        # Точная зона блока «ПУТЬ К СЛАВЕ» (верхний центр-право)
        crop_ymin, crop_ymax = int(h * 0.08), int(h * 0.35)
        crop_xmin, crop_xmax = int(w * 0.48), int(w * 0.78)

        cropped = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]
        if cropped.size == 0:
            return None

        # Увеличиваем масштаб для идеального распознавания шрифта игры
        resized = cv2.resize(cropped, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Контрастная фильтрация (белые цифры на темном фоне)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        config = '--psm 6 -c tessedit_char_whitelist=0123456789'
        
        # 1. Попытка чтения с бинаризованного кадра
        raw_text = pytesseract.image_to_string(thresh, config=config)
        found_numbers = re.findall(r'\d+', raw_text)

        # Отбираем только реальные значения кубков (от 500 до 200,000)
        valid = [int(n) for n in found_numbers if 500 <= int(n) <= 200000]
        if valid:
            return valid[0]

        # 2. Попытка чтения с оттенков серого (если порог срезaл грани)
        raw_gray_text = pytesseract.image_to_string(gray, config=config)
        found_gray_numbers = re.findall(r'\d+', raw_gray_text)
        valid_gray = [int(n) for n in found_gray_numbers if 500 <= int(n) <= 200000]
        if valid_gray:
            return valid_gray[0]

        # 3. Резервный вариант: поиск по всему изображению
        raw_full_text = pytesseract.image_to_string(img, config=config)
        full_numbers = re.findall(r'\d+', raw_full_text)
        valid_full = [int(n) for n in full_numbers if 500 <= int(n) <= 200000]
        if valid_full:
            return valid_full[0]

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
    await message.answer("Для связи с администратором пишите: @admin_username")


@dp.message(F.text == "Правила 📄")
async def process_rules(message: types.Message):
    await message.answer(
        "📋 **Правила скупки:**\n\n"
        "1. Принимаются только оригинальные скриншоты профиля.\n"
        "2. Оценка является предварительной и зависит от множества факторов.\n"
        "3. Окончательную сумму утверждает администратор.",
        parse_mode="Markdown"
    )


@dp.message(F.photo)
async def process_screenshot(message: types.Message):
    status_msg = await message.answer("🔍 Сканирую скриншот...")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    temp_filename = f"temp_{message.from_user.id}.jpg"
    await bot.download_file(file_info.file_path, temp_filename)

    try:
        trophies = extract_trophies(temp_filename)
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
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
