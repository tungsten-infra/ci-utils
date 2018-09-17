from peewee import *

db = SqliteDatabase('testruns.db')

class TestRun(Model):
    build_id = CharField()
    milliseconds = IntegerField()
    finish_datetime = DateTimeField()
    casename = CharField()
    result = CharField()

    class Meta:
        database = db

db.connect()
db.create_tables([TestRun])
