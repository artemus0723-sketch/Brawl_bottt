import telebot
from telebot import types
import requests

TOKEN = '8895895178:AAE59bdqWy9oPjpS-hWWzvt3ERUKOvS3Nyw'
ADMIN_CHAT_ID = 5267181585

bot = telebot.TeleBot(TOKEN)
user_states = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_admin = types.KeyboardButton("связь с админом")
    btn_rules = types.KeyboardButton("Правила📑")
    btn_sell = types.KeyboardButton("👾Продать аккаунт (Авто-оценка)👾")
    
    markup.add(btn_admin, btn_rules)
    markup.add(btn_sell)
    
    # Расценка убрана из приветствия
    bot.send_message(
        message.chat.id, 
        "Привет! Мы быстро оцениваем и покупаем аккаунты Brawl Stars 💸\n\n"
        "Нажми кнопку ниже, чтобы узнать стоимость твоего аккаунта по тегу!", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Ответ админа
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
    elif message.text == "👾Продать аккаунт (Авто-оценка)👾":
        user_states[message.chat.id] = 'waiting_for_tag'
        bot.send_message(
            message.chat.id, 
            "Введи ваш **Тег игрока** из игры (например `#2PP08L9U` или `2PP08L9U`):\n\n"
            "*(Его можно скопировать в профиле игры под аватаркой)*",
            parse_mode="Markdown"
        )
    elif user_states.get(message.chat.id) == 'waiting_for_tag':
        # Автоматическая замена похожих символов (буква O на ноль 0)
        tag = message.text.strip().replace('#', '').upper().replace('O', '0')
        
        bot.send_message(message.chat.id, "🔍 Поиск аккаунта и расчет стоимости...")
        
        try:
            url = f"https://api.brawlace.com/v1/players/%23{tag}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                name = data.get('name', 'Неизвестно')
                trophies = data.get('trophies', 0)
                
                # Расчет (25 кубков = 1 грн = 2 рубля)
                price_uah = round(trophies / 25, 2)
                price_rub = round(price_uah * 2, 2)
                
                info_text = (
                    f"📊 **Данные аккаунта:**\n"
                    f"👤 Ник: **{name}**\n"
                    f"🏆 Кубки: **{trophies}**\n\n"
                    f"💰 **Предварительная оценка:**\n"
                    f"• **{price_uah} грн**\n"
                    f"• **{price_rub} руб**\n\n"
                    f"Если устраивает цена — отправь скриншот профиля для подтверждения сделки!"
                )
                bot.send_message(message.chat.id, info_text, parse_mode="Markdown")
                user_states[message.chat.id] = 'waiting_for_photo'
                
            else:
                bot.send_message(message.chat.id, "❌ Аккаунт с таким тегом не найден! Проверьте тег и попробуйте снова.")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ Ошибка соединения с сервером. Попробуйте чуть позже.")
    else:
        bot.send_message(message.chat.id, "Воспользуйтесь кнопками меню ниже ⬇️")

# Обработка фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if user_states.get(chat_id) == 'waiting_for_photo':
        photo_id = message.photo[-1].file_id
        username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
        
        caption_text = (
            f"📩 **Новая заявка на продажу!**\n"
            f"От: {username}\n"
            f"ID: {chat_id}\n\n"
            f"*(Зажмите сообщение и нажмите «Ответить», чтобы написать пользователю)*"
        )
        
        bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=caption_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Спасибо! Ваша заявка передана администратору. Ожидайте ответа ⏳")
        user_states[chat_id] = None
    else:
        bot.send_message(chat_id, "Сначала нажмите кнопку «👾Продать аккаунт (Авто-оценка)👾» и введите тег.")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling(skip_pending=True)
