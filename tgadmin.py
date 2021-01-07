from datetime import datetime
import multiprocessing as mp
import telebot
from models import User
import pickle
from os import path

TB_BOT_TOKEN = "1432792475:AAHAvDJiucpui_hPDyOLeGVtYCQJhMCbFFA"

bot = telebot.TeleBot(TB_BOT_TOKEN)
queue = mp.Queue()
active = False

def save(users):
    pickle.dump(users, open("users.pkl", "wb"))

def getFine(times):
    if times == 0:
        return 0
    else:
        return getFine(times - 1) + times * 35 - 5

def timeMonitor(queue):
    chat_id = 0
    start_day = 0
    week = 0
    week_updated = False
    day_updated = False
    reminded = False
    active = False
    while True:
        if not queue.empty():
            result = queue.get()
            if isinstance(result, int):
                chat_id = result
                start_day = pickle.load(open("start.pkl", "rb"))
                week = 0
                week_updated = False
                day_updated = False
                reminded = False
                active = True
        while active:
            if datetime.now().weekday() == start_day and not week_updated:
                week_updated = True
                week += 1
                bot.send_message(chat_id, "Пошла " + str(week) + "-ая неделя")
                users = pickle.load(open("users.pkl", "rb"))
                for user in users:
                    user.rests = 2
                save(users)
            if datetime.now().weekday() != start_day and week_updated:
                week_updated = False
            if datetime.now().hour == 0 and not day_updated:
                day_updated = True
                bot.send_message(chat_id, "День окончен.")
                users = pickle.load(open("users.pkl", "rb"))
                for user in users:
                    if not user.sick:
                        if not user.done_today:
                            if user.rests == 0:
                                user.fails += 1
                                bot.send_message(chat_id,
                                                 user.name + " забыл потренероваться!🤦‍♂️ Начислен штраф - " + str(getFine(user.fails) - getFine(user.fails - 1))
                                                 + "руб. (Общий - " + str(getFine(user.fails) + "руб.)"))
                            else:
                                user.rests -= 1
                    user.done_today = False
                save(users)
                bot.send_message(chat_id, get_leaderboard())
            if datetime.now().hour == 1 and day_updated:
                day_updated = False
            if datetime.now().hour == 20 and not reminded:
                reminded = True
                text = "Ежедневная напоминалка, кому еще надо потренероваться:\n"
                i = 0
                for user in pickle.load(open("users.pkl", "rb")):
                    if user.sick:
                        i += 1
                        text += user.name + " - выздоравливай."
                    elif not user.done_today:
                        i += 1
                        if user.rests > 0:
                            text += user.name + " - неплохо бы.\n"
                        else:
                            text += user.name + " - обязательно если не хочешь штраф.\n"
                if i == 0:
                    bot.send_message(chat_id, "Сегодня все молодцы и уже потренировались💪💪💪")
                else:
                    bot.send_message(chat_id, text)
            if datetime.now().hour == 21 and reminded:
                reminded = False
            if not queue.empty():
                if isinstance(queue.get, str):
                    active = False

@bot.message_handler(commands=['start'])
def start(message):
    global active
    if not active:
        pickle.dump(datetime.now().weekday(), open("start.pkl", "wb"))
        save([])
        bot.send_message(message.chat.id, "Чэллендж начался!")
        queue.put(message.chat.id)
        active = True
    else:
        bot.send_message(message.chat.id, "Челлендж уже запущен.")


@bot.message_handler(commands=['resume'])
def resume(message):
    global active
    if path.exists("start.pkl"):
        if not active:
            bot.send_message(message.chat.id, "Возобноляю челлендж.")
            queue.put(message.chat.id)
            active = True
        else:
            bot.send_message(message.chat.id, "Челлендж уже запущен.")
    else:
        bot.send_message(message.chat.id, "Челлендж еще ни разу не был запущен.")

@bot.message_handler(commands=['stop'])
def stop(message):
    global active
    if active:
        bot.send_message(message.chat.id, "Челлендж окончен.")
        queue.put("stop")
        active = False
        fines(message)
    else:
        bot.send_message(message.chat.id, "Челлендж не запущен.")

@bot.message_handler(commands=['sick'])
def sick(message):
    if active:
        users = pickle.load(open("users.pkl", "rb"))
        user = next((u for u in users if u.tel_id == message.from_user.id), None)
        if user == None:
            bot.send_message(message.chat.id, "Вы еще не выполнили ни одной тренеровки!")
        else:
            if not user.sick:
                user.sick = True
                bot.send_message(message.chat.id, user.name + ", вы теперь больной.")
            else:
                bot.send_message(message.chat.id, user.name + ", вы и так больной.")
        save(users)

@bot.message_handler(commands=['notsick'])
def sick(message):
    if active:
        users = pickle.load(open("users.pkl", "rb"))
        user = next((u for u in users if u.tel_id == message.from_user.id), None)
        if user == None:
            bot.send_message(message.chat.id, "Вы еще не выполнили ни одной тренеровки!")
        else:
            if user.sick:
                user.sick = False
                bot.send_message(message.chat.id, user.name + ", вы больше не больной.")
            else:
                bot.send_message(message.chat.id, user.name + ", вы и так не больной.")
        save(users)

@bot.message_handler(commands=['fines'])
def fines(message):
    users = pickle.load(open("users.pkl", "rb"))
    users.sort(key=lambda x: x.done, reverse=True)
    text = "Разбивка кто кому сколько должен:\n"
    total = 0
    for user in users:
        total += user.done
    for user in users:
        if user.fails > 0:
            text += user.name + " должен:\n"
            for other_user in users:
                if other_user.tel_id != user.tel_id:
                    Iowe = round((other_user.done / (total - user.done)) * getFine(user.fails))
                    TheyOwe = round((other_user.done / (total - other_user.done)) * getFine(other_user.fails))
                    if Iowe > TheyOwe:
                        text += str(Iowe - TheyOwe) + "руб. - " + other_user.name + "\n"
        else:
            text += user.name + " никому ничего не должен\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['sfines'])
def simpleFines(message):
    users = pickle.load(open("users.pkl", "rb"))
    users.sort(key=lambda x: x.done, reverse=True)
    text = "Разбивка кому сколько из общего банка:\n"
    total_ex = 0
    total_money = 0
    for user in users:
        total_ex += user.done
        total_money += getFine(user.fails)
    for user in users:
       text += str(round(total_money * (user.done/total_ex))) + "руб. - " + user.name + "\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["help", "commands"])
def help(message):
    text = "Список команд:\n" \
           "/start - начать чэллендж\n" \
           "/stop - остановить челлендж\n" \
           "/resume - возобновить чэллендж\n" \
           "/sick - отметиться как на больничном\n" \
           "/notsick - отметиться как не на боьничном\n" \
           "/leaderboard - показать лидерборд\n" \
           "/fines - посмотреть кто кому сколько должен"
    bot.send_message(message.chat.id, text)

@bot.message_handler(content_types=["photo"])
def done(message):
    if active:
        users = pickle.load(open("users.pkl", "rb"))
        user = next((u for u in users if u.tel_id == message.from_user.id), None)
        if user == None:
            users.append(User(tel_id=message.from_user.id, name=message.from_user.first_name))
            user = users[-1]
            bot.send_message(message.chat.id, user.name + " был зарегестрирован.")

        if not user.done_today:
            if user.sick:
                bot.reply_to(message, "Видимо вы больше не больны.")
                user.sick = False
            user.done_today = True
            user.done += 1
            bot.reply_to(message, f"Тренировка засчитана! Всего выполнено: {user.done}")
        else:
            bot.reply_to(message, f"2 раза за день перебор) Всего выполнено: {user.done}")
        save(users)
    else:
        bot.reply_to(message, "Челлендж еще не был запущен")


def get_leaderboard():
    mes = "Лидер борд 👊🏼\n\n"
    users = pickle.load(open("users.pkl", "rb"))
    users.sort(key=lambda x: x.done, reverse=True)
    for i, user in enumerate(users):
        if user.fails:
            mes += f"{i + 1}. {user.name} - {user.done} [{user.rests}] (-{getFine(user.fails)})"
        else:
            mes += f"{i + 1}. {user.name} - {user.done} [{user.rests}] 💪"
        if user.sick:
            mes += " - на больничном \n"
        else:
            mes += "\n"
    return mes


@bot.message_handler(commands=['leaderboard'])
def text_mes(message):
    bot.send_message(message.chat.id, get_leaderboard())



if __name__ == "__main__":
    print("Start")
    bot_process = mp.Process(target=timeMonitor, args=(queue, ))
    bot_process.daemon = True
    bot_process.start()
    bot.polling(none_stop=True, timeout=60)
