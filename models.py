import datetime

class User():
    def __init__(self, tel_id, name, done_per_week):
        self.tel_id = tel_id
        self.name = name
        self.done = 0
        self.done_per_week = done_per_week
        self.fails = 0
        self.fails_this_week = 0
        self.last_training = datetime.datetime.now().day - 1
        self.sick = False
