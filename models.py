import datetime
from peewee import *
from playhouse.postgres_ext import PostgresqlExtDatabase, ArrayField, JSONField
import config

db = PostgresqlExtDatabase(config.dbname, user=config.dbuser, password=config.dbpass,
                           host=config.dbhost, port=5432)

class Users(Model):
    tel_id = BigIntegerField(unique=True);
    name = TextField(default="")
    username = TextField(default="")
    done = IntegerField(default=0)
    done_today = BooleanField(default=False)
    rests = IntegerField(default=2)
    fails = IntegerField(default=0)
    sick = BooleanField(default=False)
    phone = TextField(default="")
    bank = TextField(default="")

    class Meta:
        database = db