from datetime import datetime
import multiprocessing as mp
import telebot
from models import Users
import pickle
from os import path
import re
from PIL import Image
import pytesseract as pts

TB_BOT_TOKEN = "1432792475:AAHAvDJiucpui_hPDyOLeGVtYCQJhMCbFFA"

bot = telebot.TeleBot(TB_BOT_TOKEN)
queue = mp.Queue()
active = False
phone_pattern = re.compile("(?:\+7|8)[0-9]{10}")
time_pattern = re.compile("^[0-9]{1,2}:([0-9]{2}){1,2}$")
date_pattern = re.compile("^[0-9]{1,2}([.][0-9]{1,4}){1,2}$")
stime_pattern = re.compile("^[0-9]{1,2}$")

def recognise(img):
    #pts.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'
    times = []
    data = re.findall(r"[\S']+", pts.image_to_string(img, lang='rus', config='--psm 6'))
    for i in range(len(data) - 1):
        #print(data[i])
        if time_pattern.match(data[i].strip()) and data[i + 1].lower().find("рм") == -1 and data[i + 1].lower().find(
                "ам") == -1 and not date_pattern.match(data[i - 1]):
            #print(time_pattern)
            times.append(data[i])
        if stime_pattern.match(data[i]) and data[i - 2].lower() == "мин":
            #print(data[i])
            times.append(data[i])

    if len(times) == 0:
        return "хз"
    elif len(times) > 1:
        parts = times[1].split(":")
        if len(parts) == 3:
            return parts[1] + "мин"
        else:
            return parts[0] + "мин"
    else:
        parts = times[0].split(":")
        if len(parts) == 3:
            return parts[1] + " мин"
        else:
            return parts[0] + " мин"

def getFine(times):
    if times == 0:
        return 0
    else:
        return getFine(times - 1) + times * 35 - 5

def timeMonitor(queue):
    chat_id = 0
    start_day = 0
    week = 1
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
                week = 1
                week_updated = False
                day_updated = False
                reminded = False
                active = True
        while active:
            if datetime.now().hour == 0 and datetime.now().weekday() == start_day and not week_updated:
                week_updated = True
                week += 1
                bot.send_message(chat_id, "Пошла " + str(week) + "-ая неделя")
                for user in Users.select().execute():
                    user.rests = 2
                    user.save()
            if datetime.now().weekday() != start_day and week_updated:
                week_updated = False
            if datetime.now().hour == 21 and not day_updated:
                day_updated = True
                bot.send_message(chat_id, "День окончен.")
                for user in Users.select().execute():
                    if not user.sick:
                        if not user.done_today:
                            if user.rests == 0:
                                user.fails += 1
                                bot.send_message(chat_id,
                                                 user.name + " забыл потренероваться!🤦‍♂️ Начислен штраф - " + str(getFine(user.fails) - getFine(user.fails - 1))
                                                 + "руб. (Общий - " + str(getFine(user.fails)) + "руб.)")
                            else:
                                user.rests -= 1
                    user.done_today = False
                    user.save()
                bot.send_message(chat_id, get_leaderboard())
            if datetime.now().hour == 22 and day_updated:
                print("Resetting day update")
                day_updated = False
            if datetime.now().hour == 20 and not reminded:
                reminded = True
                text = "Ежедневная напоминалка, кому еще надо потренероваться:\n"
                i = 0
                for user in Users.select().execute():
                    if user.sick:
                        i += 1
                        text += user.name + " - выздоравливай."
                    elif not user.done_today:
                        i += 1
                        if user.rests > 0:
                            if user.username != None:
                                text += "@" + user.username + " - неплохо бы.\n"
                            else:
                                text += "@" + user.name + " - неплохо бы.\n"
                        else:
                            if user.username != None:
                                text += "@" + user.username + " - обязательно если не хочешь штраф.\n"
                            else:
                                text += "@" + user.name + " - обязательно если не хочешь штраф.\n"
                if i == 0:
                    bot.send_message(chat_id, "Сегодня все молодцы и уже потренировались💪💪💪")
                else:
                    bot.send_message(chat_id, text)
            if datetime.now().hour == 21 and reminded:
                print("Resetting reminder")
                reminded = False
            if not queue.empty():
                if isinstance(queue.get, str):
                    active = False

@bot.message_handler(commands=['start'])
def start(message):
    global active
    if not active:
        pickle.dump(datetime.now().weekday(), open("start.pkl", "wb"))
        Users.truncate_table()
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
        user = Users.get_or_none(tel_id=message.from_user.id)
        if user == None:
            bot.send_message(message.chat.id, "Вы еще не выполнили ни одной тренеровки!")
        else:
            if not user.sick:
                user.sick = True
                user.save()
                bot.send_message(message.chat.id, user.name + ", вы теперь больной.")
            else:
                bot.send_message(message.chat.id, user.name + ", вы и так больной.")

@bot.message_handler(commands=['notsick'])
def sick(message):
    if active:
        user = Users.get_or_none(tel_id=message.from_user.id)
        if user == None:
            bot.send_message(message.chat.id, "Вы еще не выполнили ни одной тренеровки!")
        else:
            if user.sick:
                user.sick = False
                user.save()
                bot.send_message(message.chat.id, user.name + ", вы больше не больной.")
            else:
                bot.send_message(message.chat.id, user.name + ", вы и так не больной.")


@bot.message_handler(commands=['fines'])
def fines(message):
    text = "Разбивка кто кому сколько должен:\n"
    total = 0
    for user in Users.select().order_by(Users.fails.asc()).execute():
        total += user.done
    for user in Users.select().execute():
        if user.fails > 0:
            text += user.name + "(" + user.phone + " " + user.bank + ")" + " должен:\n"
            for other_user in Users.select().execute():
                if other_user.tel_id != user.tel_id:
                    Iowe = round((other_user.done / (total - user.done)) * getFine(user.fails))
                    TheyOwe = round((other_user.done / (total - other_user.done)) * getFine(other_user.fails))
                    if Iowe > TheyOwe:
                        text += str(Iowe - TheyOwe) + "руб. - " + other_user.name + "\n"
        else:
            text += user.name + "(" + user.phone + " " + user.bank + ")" + " никому ничего не должен\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['sfines'])
def simpleFines(message):
    text = "Разбивка кому сколько из общего банка:\n"
    total_ex = 0
    total_money = 0
    for user in Users.select().order_by(Users.fails.asc()).execute():
        total_ex += user.done
        total_money += getFine(user.fails)
    for user in Users.select().execute():
       text += str(round(total_money * (user.done/total_ex))) + "руб. - " + user.name + "\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setphone'])
def setPhone(message):
    parts = message.text.split(" ")
    if len(parts) == 3:
        if phone_pattern.match(parts[1]):
            user = Users.get_or_none(tel_id=message.from_user.id)
            if user != None:
                user.phone = parts[1]
                user.bank = parts[2]
                bot.reply_to(message, "Номер телефона и банк сохранен ")
                user.save()
            else:
                bot.reply_to(message, "Вы еще не зарагестрированы в челлендже.")
        else:
            bot.reply_to(message, "Неправильный формат телефона.")
    else:
        bot.reply_to(message, "Неправильный формат ввода.")

@bot.message_handler(commands=["help", "commands"])
def help(message):
    text = "Список команд:\n" \
           "/start - начать чэллендж\n" \
           "/stop - остановить челлендж\n" \
           "/resume - возобновить чэллендж\n" \
           "/sick - отметиться как на больничном\n" \
           "/notsick - отметиться как не на боьничном\n" \
           "/leaderboard - показать лидерборд\n" \
           "/fines - посмотреть кто кому сколько должен\n" \
           "/setphone <телефон> <банк> - установить свой телефон и банк"
    bot.send_message(message.chat.id, text)

@bot.message_handler(content_types=["photo"])
def done(message):
    if active:
        user = Users.get_or_none(tel_id=message.from_user.id)
        if user == None:
            Users.create(tel_id=message.from_user.id, name=message.from_user.first_name, username=message.from_user.username)
            user = Users.get(tel_id=message.from_user.id)
            bot.send_message(message.chat.id, user.name + " был зарегистрирован.")

        if not user.done_today:
            if user.sick:
                bot.reply_to(message, "Видимо вы больше не больны.")
                user.sick = False
            user.done_today = True
            user.done += 1
            user.save()
            bot.reply_to(message, f"Тренировка засчитана! Всего выполнено: {user.done}")
            fileID = message.photo[-1].file_id
            file = bot.get_file(fileID)
            downloaded = bot.download_file(file.file_path)
            new_img = open("received_img.jpg", "wb")
            new_img.write(downloaded)
            new_img.close()
            bot.reply_to(message, f"Предположитнльная продлжительность: {recognise(Image.open('received_img.jpg'))}.")
        else:
            bot.reply_to(message, f"2 раза за день перебор) Всего выполнено: {user.done}")


def get_leaderboard():
    mes = "Лидер борд 👊🏼\n\n"
    for i, user in enumerate(Users.select().order_by(Users.done.desc()).execute()):
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
