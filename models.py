import datetime

class User():
    def __init__(self, tel_id, name):
        self.tel_id = tel_id
        self.name = name
        self.done = 0
        self.done_today = False
        self.rests = 2
        self.fails = 0
        self.sick = False

    def __init__(self, tel_id, name, done, fails):
        self.tel_id = tel_id
        self.name = name
        self.done = done
        self.fails = fails
        self.fails_this_week = 0
        self.last_training = datetime.datetime.now().day - 1
        self.sick = False
