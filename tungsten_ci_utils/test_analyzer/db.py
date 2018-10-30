from peewee import *

#db = SqliteDatabase('testruns.db')
db = MySQLDatabase('test_statistics', user='user', password='secret', host='localhost', port=8080)

class TestRun(Model):
    build_id = CharField(index=True)
    milliseconds = IntegerField()
    finish_datetime = DateTimeField()
    casename = CharField()
    suitename = CharField()
    result = CharField()

    class Meta:
        database = db

db.connect()
db.create_tables([TestRun])
