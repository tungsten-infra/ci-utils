from peewee import *
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

db_host = config['DATABASE']['host']
db_port = int(config['DATABASE']['port'])
db_name = config['DATABASE']['database']
db_table = config['DATABASE']['table']
user = config['DATABASE']['user']
password = config['DATABASE']['password']

db = MySQLDatabase(db_name, user=user, password=password, host=db_host, port=db_port)


class TestStats(Model):
    change = IntegerField(index=True)
    patchset = IntegerField()
    suitename = CharField()
    no_testcases = IntegerField()
    duration = IntegerField()
    result = CharField()

    class Meta:
        database = db
        table_name = db_table


db.connect()
db.create_tables([TestStats])
