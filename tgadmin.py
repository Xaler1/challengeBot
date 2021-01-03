from datetime import datetime
import multiprocessing as mp

import telebot

from models import Users

TB_BOT_TOKEN = "1432792475:AAHAvDJiucpui_hPDyOLeGVtYCQJhMCbFFA"

bot = telebot.TeleBot(TB_BOT_TOKEN)

taxes = {0: 0, 1: 30, 2: 95, 3: 195, 4: 330, 5: 500, 6: 705, 7: 945, 8: 1220, 9: 1530, 10: 1875, 11: 2255, 12: 2655,
         13: 3055, 14: 3455, 15: 3855, 16: 4255, 17: 4655, 18: 5055, 19: 5455, 20: 5855, 21: 6255, 22: 6655, 23: 7055,
         24: 7455, 25: 7855, 26: 8255, 27: 8655, 28: 9055, 29: 9455}

bot_process = None

def getDaysSinceTurnover(start_day):
    today = datetime.now().weekday()
    if today > start_day:
        return  today - start_day
    else:
        return today + (7 - start_day)

def timeMonitor(chat_id, start_day):
    week = 0
    week_updated = False
    day_updated = True
    reminded = False
    while True:
        if datetime.now().weekday() == start_day and not week_updated:
            week_updated = True
            week += 1
            bot.send_message(chat_id, "Пошла " + str(week) + "-ая неделя")
            for user in Users.select().execute():
                user.done_per_week = 0
                user.fails_this_week = 0
                user.save()
        if datetime.now().weekday() != start_day and week_updated:
            week_updated = False
        if datetime.now().hour == 0 and datetime.now().minute == 0 and not day_updated:
            day_updated = True
            days_passed = getDaysSinceTurnover()
            bot.send_message(chat_id, "День окончен.")
            for user in Users.select().execute():
                fails_this_week = days_passed - user.done_per_week - 2
                if fails_this_week > user.fails_this_week:
                    user.fails_this_week = fails_this_week
                    user.fails += 1
                    user.save()
                    bot.send_message(chat_id, user.name + " забыл потренероваться!🤦‍♂️ Начислен штраф - " + str(taxes[user.fails] - taxes[user.fails - 1])
                                     + "руб. (Общий - " + str(taxes[user.fails] + "руб.)"))
            bot.send_message(chat_id, get_leaderboard())
        if datetime.now().hour == 1 and day_updated:
            day_updated = False
        if datetime.now().hour == 20 and not reminded:
            reminded = True
            text = "Ежедневная напоминалка, кому еще надо потренероваться:\n"
            i = 0
            for user in Users.select().execute():
                if user.last_trening != datetime.now().today():
                    i += 1
                    if getDaysSinceTurnover() - user.done_per_week >= 2:
                        text += user.name + " - надо бы.\n"
                    else:
                        text += user.name + " - обязательно если не хочешь штраф.\n"
            if i == 0:
                bot.send_message(chat_id, "Сегодня все молодцы и уже потренировались💪💪💪")
            else:
                bot.send_message(chat_id, text)
        if datetime.now().hour == 21 and reminded:
            reminded = False


@bot.message_handler(commands=['start', "/restart"])
def start(message):
    global bot_process
    if bot_process != None:
        bot_process.kill()
    bot.send_message(message.chat.id, "Чэллендж начался, всем удачи!")
    for user in Users.select().execute():
        user.done_per_week = 0
        user.done = 0
        user.last_trening = -1
        user.fails = 0
        user.fails_this_week = 0
        user.save()
    bot_process = mp.Process(target=timeMonitor, args=(message.chat.id, datetime.now().weekday() ))
    bot_process.start()
    bot_process.join()

@bot.message_handler(commands=['stop'])
def stop(message):
    bot.send_message(message.chat.id, "Сезон тренеровок окончен")

@bot.message_handler(content_types=["photo"])
def done(message):
    print("photo")
    user = Users.get_or_none(Users.tel_id == message.from_user.id)
    if not user:
        user = Users.get_or_create(name=message.from_user.first_name, tel_id=message.from_user.id)
        print("User created")

    if user.last_trening < datetime.date.today():
        print("Complete")
        user.username = message.from_user.username
        user.last_trening = datetime.date.today()
        user.done_per_week += 1
        user.done += 1
        user.save()
        bot.reply_to(message, f"Тренировка засчитана! Всего выполнено: {user.done}")
    else:
        bot.reply_to(message, f"2 раза за день перебор) Всего выполнено: {user.done}")


def get_leaderboard():
    mes = "Лидер борд 👊🏼\n\n"
    day = datetime.date.today().weekday()
    for i, u in enumerate(Users.select().order_by(Users.done.desc()).execute()):
        rest = max(0, 2 - (getDaysSinceTurnover() - u.done_per_week))
        if u.fails:
            mes += f"{i + 1}. {u.name} - {u.done} [{rest}] (-{taxes[u.fails]})\n"
        else:
            mes += f"{i + 1}. {u.name} - {u.done} [{rest}] 💪\n"

        print(u.name, u.tel_id)
    return mes


@bot.message_handler(content_types=["text"])
def text_mes(message):
    if message.text == "/leaderboard":
        bot.send_message(message.chat.id, get_leaderboard())

    if message.from_user.id == 445330281 and message.text == "/alarm":
        text = "Напомню, что вам нужно сделать сегодня тренировочку: "
        for u in Users.select().execute():
            if u.last_trening < datetime.date.today() and u.username:
                text += f"@{u.username} "
        bot.send_message(message.chat.id, text)

    if message.from_user.id == 445330281 and message.text == "/weekEnd":
        for u in Users.select().execute():
            u.fails += 5 - u.done_per_week, 0
            u.done_per_week = 0
            u.save()
        bot.send_message(message.chat.id, "Неделя обновлена.")
        bot.send_message(message.chat.id, get_leaderboard())

    print(message.text, message.from_user.id)


if __name__ == "__main__":
    # tasks = {}
    # sum = 0
    # delt = 30
    # for t in range(30):
    #     tasks[t] = sum
    #     sum += delt
    #     delt += 35
    #     delt = min(delt, 400)
    # print(tasks)
    print("Start")
    bot.polling(none_stop=True, timeout=60)
