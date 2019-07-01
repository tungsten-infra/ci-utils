#!/usr/bin/env python
from __future__ import print_function
import sys
import logging
import yaml
import MySQLdb


log = logging.getLogger('listen_for_zuul_build')


def create_mysql_connection(conn_data):
    conn = MySQLdb.connect(host=conn_data["host"],
                         port=conn_data["port"],
                         user=conn_data["user"],
                         passwd=conn_data["password"],
                         db=conn_data["database"])
    return conn


def get_last_successful_build_number(zuul_db_conn_data, build_db_conn_data, branch='master', build_number_method='build_cache_db'):
    """ build_number_method: can be either build_cache_db or log_url"""
    zuul_db = create_mysql_connection(zuul_db_conn_data)
    c = zuul_db.cursor()
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
    buildset_id = last_buildset[1][1:]
    if build_number_method == 'build_cache_db':
        build_db = create_mysql_connection(build_db_conn_data)
        c2 = build_db.cursor()
        query = """SELECT build_number from build_metadata_cache where zuul_buildset_id = %s"""
        c2.execute(query, (buildset_id,))
        if c2.rowcount != 1:
            log.error("Error: build_number db should return 1 entry for buildset %s, returned %s, exiting.", buildset_id,  c2.rowcount)
            sys.exit(1)
        build_number = c2.fetchone()[0]
    elif build_number_method == 'log_url':
        query = """SELECT log_url FROM zuul_build where buildset_id = %s and log_url NOT LIKE '%%\_%%'"""
        try:
            c.execute(query, (last_buildset[0],))
        except Exception as e:
            log.error("Exception during query execution %s", e)
            sys.exit(1)
        build = c.fetchone()
        log_url = build[0]
        build_number = int(log_url.split('/')[-3])
    else:
        raise Exception('Unsupported build_number_method: ' + str(build_number_method))
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
    defaults = {
      'build_number_method': 'build_cache_db',
      'zuul_db': {},
      'build_db': {},
    }
    config = {}
    config.update(defaults)
    with open("config.yaml", "r") as config_file:
        config_from_file = yaml.load(config_file)
        config.update(config_from_file)
    branch = sys.argv[1]
    build_number = get_last_successful_build_number(config['zuul_db'], config['build_db'], branch=branch, build_number_method=config['build_number_method'])
    log.debug("Found last successful Tungsten build number for branch %s: %s", branch, build_number)
    print(build_number)
    sys.exit(0)
