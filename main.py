import os
import telebot
from telebot import types

# Укажите ваш токен от BotFather
TOKEN = '8895895178:AAHRB6dt-LR_17MX9pMsNJZJDPqGruQHYzk'

# Укажите ваш Telegram ID (число без кавычек), куда отправлять скриншоты
# Свой ID можно узнать у бота @userinfobot в Telegram
ADMIN_CHAT_ID = 5267181585

bot = telebot.TeleBot(TOKEN)

# Словарь для отслеживания пользователей, ожидающих отправку фото
user_states = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    btn_admin = types.KeyboardButton("связь с админом")
    btn_rules = types.KeyboardButton("Правила📑")
    btn_sell = types.KeyboardButton("👾продать аккаунт👾")
    
    markup.add(btn_admin, btn_rules, btn_sell)
    
    bot.send_message(
        message.chat.id, 
        "Привет,здесь ты можешь продать💸 свой аккаунт в Бравл Старс быстро", 
        reply_markup=markup
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "связь с админом":
        bot.send_message(message.chat.id, "@yrodochk администратор постарается вам ответь как можно скорее")
    elif message.text == "Правила📑":
        bot.send_message(message.chat.id, "Привет, мы покупаем аккаунты только от 5000🏆")
    elif message.text == "👾продать аккаунт👾":
        user_states[message.chat.id] = 'waiting_for_photo'
        bot.send_message(message.chat.id, "Отлично,отправь нам скриншот своего профиля в Бравл старс что бы мы могли оценить")

# Обработчик отправленных фотографий
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    
    # Проверяем, нажал ли пользователь кнопку "продать аккаунт"
    if user_states.get(chat_id) == 'waiting_for_photo':
        # Отправляем фото админу с информацией о пользователе
        photo_id = message.photo[-1].file_id
        username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {chat_id}"
        
        bot.send_photo(
            ADMIN_CHAT_ID, 
            photo_id, 
            caption=f"📩 **Новая заявка на продажу!**\nОт: {username}"
        )
        
        # Отвечаем пользователю
        bot.send_message(chat_id, "ожидание⏳")
        
        # Сбрасываем состояние
        user_states[chat_id] = None

if __name__ == '__main__':
    bot.infinity_polling()
