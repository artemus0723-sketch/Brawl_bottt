@dp.message_handler(commands=['start'])
def start_command(message: types.Message):
    await message.answer("Привет, здесь ты можешь продать💸 свой акаунт бравл страс")
