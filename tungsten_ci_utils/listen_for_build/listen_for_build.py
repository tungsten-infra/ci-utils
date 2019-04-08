#!/usr/bin/env python
from __future__ import print_function
import sys
import logging
import yaml
import MySQLdb
#import requests

log = logging.getLogger('listen_for_zuul_build')

def get_last_successful_build_number(db, db_build_numbers, branch='master'):
    c = db.cursor()
    pipeline = 'periodic-nightly'
    ref = 'refs/heads/' + branch
    result = 'SUCCESS'
    query = """SELECT id, zuul_ref, result FROM zuul_buildset where id IN ( SELECT max(id) FROM zuul_buildset where pipeline = %s and ref = %s and result = %s )"""
    try:
        c.execute(query, (pipeline, ref, result))
    except Exception as e:
        log.error("Exception during query execution %s", e)
        sys.exit(1)
    if c.rowcount < 1:
        log.error("No buildsets found for branch %s, exiting...", ref)
        sys.exit(1)
    last_buildset = c.fetchone()
    c2 = db_build_numbers.cursor()
    buildset_id = last_buildset[1][1:]
    query = """SELECT build_number from build_metadata_cache where zuul_buildset_id = %s"""
    c2.execute(query, (buildset_id,))
    if c2.rowcount != 1:
        log.error("Error: build_number db should return 1 entry for buildset %s, returned %s, exiting.", buildset_id,  c2.rowcount)
        sys.exit(1)
    build_number = c2.fetchone()[0]
    return build_number


def set_logging(args):
    log_filename = '/tmp/listen_for_zuul_builds.log'
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    log.addHandler(console)

    fileHandler = logging.FileHandler(log_filename)
    fileHandler.setFormatter(formatter)
    log.addHandler(fileHandler)

if __name__ == '__main__':
    set_logging(None)
    with open("config.yaml", "r") as config_file:
        config = yaml.load(config_file)
    branch = sys.argv[1]
    zuul_db = config["zuul_db"]
    build_db = config["build_db"]
    zuul_db_conn = MySQLdb.connect(host=zuul_db["host"],
                         port=zuul_db["port"],
                         user=zuul_db["user"],
                         passwd=zuul_db["password"],
                         db=zuul_db["database"])
    build_db_conn = MySQLdb.connect(host=build_db["host"],
                         port=build_db["port"],
                         user=build_db["user"],
                         passwd=build_db["password"],
                         db=build_db["database"])
    build_number = get_last_successful_build_number(zuul_db_conn, build_db_conn, branch=branch)
    log.debug("Found last successful Tungsten build number for branch %s: %s", branch, build_number)
    print(build_number)
    sys.exit(0)
