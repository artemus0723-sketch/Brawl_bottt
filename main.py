import telebot

# Замените 'YOUR_BOT_TOKEN' на токен от BotFather
bot = telebot.TeleBot('8895895178:AAHRB6dt-LR_17MX9pMsNJZJDPqGruQHYzk')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот репозитория Brawl_bottt работает!")

if __name__ == '__main__':
    bot.infinity_polling()
