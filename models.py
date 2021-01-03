import datetime

from peewee import *
from playhouse.postgres_ext import PostgresqlExtDatabase, ArrayField, JSONField

bdname = 'fizrabot'
bduser = 'postgres'
bdpassword = '-'
bdhost = 'sw.neafiol.site'
bdport = 5432

db = PostgresqlExtDatabase(bdname, user=bduser, password=bdpassword,
                           host=bdhost, port=bdport)  # .rollback()


class Users(Model):
    tel_id = BigIntegerField(unique=True)
    name = TextField(default="")
    username = TextField(default="")
    done = IntegerField(default=0)
    done_per_week = IntegerField(default=0)
    fails = IntegerField(default=0)
    fails_this_week = IntegerField(default=0)
    last_trening = DateField(default=lambda: datetime.date.today() - datetime.timedelta(days=1))

    class Meta:
        database = db


# Users.drop_table()
# Users.create_table()
# user = Users.get()
# Users.update({Users.done:0}).where(Users.tel_id==445330281).execute()
# print(datetime.date.today() < user.last_trening)
