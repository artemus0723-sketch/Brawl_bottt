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
# УЛУЧШЕННАЯ ОБРАБОТКА ИЗОБРАЖЕНИЙ (OCR)
# ==========================================
def extract_trophies(image_path: str) -> int | None:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        height, width, _ = img.shape

        # Расширяем область обрезки, чтобы захватить кубки на любых разрешениях и вертикальных скриншотах
        crop_ymin, crop_ymax = int(height * 0.0), int(height * 0.45)
        crop_xmin, crop_xmax = int(width * 0.25), int(width * 0.85)
        
        cropped_img = img[crop_ymin:crop_ymax, crop_xmin:crop_xmax]
        if cropped_img.size == 0:
            return None

        # Увеличиваем изображение для более точного OCR
        resized = cv2.resize(cropped_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Вариант 1: Пороговая обработка (Threshold)
        _, thresh = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY)
        
        config = '--psm 6 -c tessedit_char_whitelist=0123456789'
        raw_text = pytesseract.image_to_string(thresh, config=config)
        digits = [int(d) for d in re.findall(r'\d+', raw_text) if 50 <= int(d) <= 200000]

        if digits:
            return max(digits)

        # Вариант 2: Адаптивный порог (для контрастных цифр на сложном фоне)
        adapt_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        raw_text_adapt = pytesseract.image_to_string(adapt_thresh, config=config)
        digits_adapt = [int(d) for d in re.findall(r'\d+', raw_text_adapt) if 50 <= int(d) <= 200000]

        if digits_adapt:
            return max(digits_adapt)

        # Вариант 3: Прямой поиск по оттенкам серого
        raw_text_gray = pytesseract.image_to_string(gray, config=config)
        digits_gray = [int(d) for d in re.findall(r'\d+', raw_text_gray) if 50 <= int(d) <= 200000]

        if digits_gray:
            return max(digits_gray)

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
