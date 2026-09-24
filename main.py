import telebot

# Замените 'YOUR_BOT_TOKEN' на токен от BotFather
bot = telebot.TeleBot('8895895178:AAHRB6dt-LR_17MX9pMsNJZJDPqGruQHYzk')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет,здесь ты можешь продать💸 свой акаунт в Бравл Старс быстро")

if __name__ == '__main__':
    bot.infinity_polling()
    import os
import telebot
from telebot import types

# Получаем токен из переменных окружения
TOKEN = os.getenv('8895895178:AAHRB6dt-LR_17MX9pMsNJZJDPqGruQHYzk')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    # Создаем обычную клавиатуру вместо инлайн-кнопок
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Создаем 4 кнопки
    btn_like = types.KeyboardButton("связь с админом ")
    btn_dislike = types.KeyboardButton("💸продать акаунт💸")
    btn_report = types.KeyboardButton("правила")
    
    
    # Размещаем все 4 кнопки в один ряд
    keyboard.row(btn_like, btn_dislike, btn_report, btn_sleep)
    
    # Отправляем сообщение
    bot.send_message(
        message.chat.id, 
        "Привет, здесь ты можешь продать💸", 
        reply_markup=keyboard
    )

# Обработка нажатий на кнопки
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == "связь с админом":
        bot.send_message(message.chat.id, "")
    elif message.text == "💸продать акаунт💸":
        bot.send_message(message.chat.id, "👾теперь пришли скриншот своего профиля что бы мы могли его оценить👾")
    elif message.text == "правила":
        bot.send_message(message.chat.id, "привет мы покупаем акаунты от 5000🏆 если опалата не пришла моментально жди около 20 минут")
    

if __name__ == '__main__':
    bot.polling(none_stop=True)

