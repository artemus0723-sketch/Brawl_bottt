import os
import telebot
from telebot import types

# Укажите ваш токен от BotFather в кавычках
TOKEN = '8895895178:AAHRB6dt-LR_17MX9pMsNJZJDPqGruQHYzk'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_command(message):
    # Создаем меню кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # Создаем кнопки
    btn_admin = types.KeyboardButton("связь с админом")
    btn_rules = types.KeyboardButton("Правила📑")
    btn_sell = types.KeyboardButton("👾продать аккаунт👾")
    
    # Добавляем кнопки в меню
    markup.add(btn_admin, btn_rules, btn_sell)
    
    # Отправляем приветствие с кнопками
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
        bot.send_message(message.chat.id, "Отлично,отправь нам скриншот своего профиля в Бравл старс что бы мы могли оценить")

if __name__ == '__main__':
    bot.infinity_polling()
