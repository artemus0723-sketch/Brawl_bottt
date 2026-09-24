import io
import re
import requests
import telebot
from telebot import types

# ==================== НАСТРОЙКИ ====================
TOKEN = "8895895178:AAHYlkLlTbGCCNpyMYLIZF4NHbZ5PZmmvL8"            # Вставь токен от @BotFather
ADMIN_CHAT_ID = 5267181585             # Твой Telegram ID
OCR_API_KEY = "K83218609288957" # Вставь скопированный ключ из письма
# ====================================================

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_admin = types.KeyboardButton("связь с админом")
    btn_rules = types.KeyboardButton("Правила📑")
    btn_sell = types.KeyboardButton("👾Продать аккаунт (По фото)👾")
    
    markup.add(btn_admin, btn_rules)
    markup.add(btn_sell)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Мы быстро оцениваем и покупаем аккаунты Brawl Stars 💸\n\n"
        "Отправь скриншот своего профиля из игры, и я автоматически посчитаю стоимость!", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Ответ админа пользователю через "Ответить" (Reply)
    if message.chat.id == ADMIN_CHAT_ID and message.reply_to_message:
        try:
            first_line = message.reply_to_message.caption or message.reply_to_message.text or ""
            if "ID:" in first_line:
                raw_id = first_line.split("ID:")[1].split("\n")[0].strip()
                user_id = int(raw_id)
                bot.send_message(user_id, f"💬 **Ответ от администратора:**\n\n{message.text}", parse_mode="Markdown")
                bot.send_message(ADMIN_CHAT_ID, "✅ Ответ успешно отправлен!")
            else:
                bot.send_message(ADMIN_CHAT_ID, "❌ Не удалось найти ID пользователя.")
        except Exception as e:
            bot.send_message(ADMIN_CHAT_ID, f"❌ Ошибка отправки: {e}")
        return

    if message.text == "связь с админом":
        bot.send_message(message.chat.id, "Администратор: @yrodochk")
    elif message.text == "Правила📑":
        bot.send_message(message.chat.id, "Покупаем аккаунты только от 5000🏆 с полными данными!")
    elif message.text == "👾Продать аккаунт (По фото)👾":
        bot.send_message(
            message.chat.id, 
            "📸 **Отправь скриншот твоего профиля Brawl Stars.**\n\n"
            "Убедись, что на фото хорошо видно количество кубков!"
        )
    else:
        bot.send_message(message.chat.id, "Отправь скриншот профиля или воспользуйся кнопками меню ⬇️")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔍 Сканирую скриншот...")
    
    try:
        # Скачиваем фото в оперативную память
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Отправляем фото в быструю бесплатную OCR
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'filename': ('image.jpg', downloaded_file, 'image/jpeg')},
            data={'apikey': OCR_API_KEY, 'language': 'eng', 'OCREngine': 2},
            timeout=10
        )
        
        result = response.json()
        parsed_text = ""
        if result.get("ParsedResults"):
            parsed_text = result["ParsedResults"][0]["ParsedText"]
            
        # Ищем числа на скриншоте (диапазон кубков)
        numbers = []
        for line in parsed_text.splitlines():
            cleaned = re.sub(r'\D', '', line)
            if cleaned:
                val = int(cleaned)
                if 500 <= val <= 150000:
                    numbers.append(val)
        
        username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"

        if numbers:
            trophies = max(numbers)
            
            # Формула расчета: 25 кубков = 1 грн = 2 руб
            price_uah = round(trophies / 25, 2)
            price_rub = round(price_uah * 2, 2)
            
            info_text = (
                f"📊 **Результат сканирования:**\n"
                f"🏆 Распознано кубков: **~{trophies}**\n\n"
                f"💰 **Предварительная оценка:**\n"
                f"• **{price_uah} грн**\n"
                f"• **{price_rub} руб**\n\n"
                f"Заявка передана администратору! ⏳"
            )
            bot.send_message(chat_id, info_text, parse_mode="Markdown")
            
            # Сообщение администратору
            caption_text = (
                f"📩 **Новая заявка!**\n"
                f"От: {username}\n"
                f"ID: {chat_id}\n"
                f"🏆 Кубков на фото: ~{trophies}\n"
                f"💰 Оценка: {price_uah} грн / {price_rub} руб\n\n"
                f"*(Зажмите сообщение и нажмите «Ответить», чтобы написать)*"
            )
            bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=caption_text, parse_mode="Markdown")
            
        else:
            bot.send_message(
                chat_id, 
                "❌ Не удалось четко распознать кубки. Заявка отправлена администратору на ручную проверку ⏳"
            )
            bot.send_photo(
                ADMIN_CHAT_ID, 
                message.photo[-1].file_id, 
                caption=f"📩 **Новая заявка (Ручная проверка)!**\nОт: {username}\nID: {chat_id}"
            )
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка обработки фото: {e}")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling(skip_pending=True)
