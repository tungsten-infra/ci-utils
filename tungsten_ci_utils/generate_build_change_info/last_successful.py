import sys
import argparse
import MySQLdb
import logging
import json
import re

log = logging.getLogger(__name__)

def set_logging():
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    log.addHandler(console)

set_logging()

def get_json_data(file):
    with open(file, 'r') as json_file:
        data = json.load(json_file)
    return data

def get_build_number_from_log_url(log_url,branch):
    regex = '(?<=' + branch + '\/)(.*?)(?=\/)'
    number = re.search(regex, log_url).group(1)
    return number

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials-json")
    parser.add_argument("branch")
    parser.add_argument("build_number", type=int)
    args = parser.parse_args()

    branch = str(args.branch)
    build_number = args.build_number
    credentials_json = args.credentials_json

    db_config = get_json_data(credentials_json)

    try:
        db = MySQLdb.connect(
            user=db_config["user"],
            passwd=db_config["passwd"],
            db=db_config["db"],
            host=db_config["host"],
            port=db_config["port"]
        )
        cur = db.cursor()
    except:
        log.error('database connection error')
        sys.exit(1)

    query_get_buildset = """
    SELECT max(buildset_id), max(end_time) FROM zuul_build
    WHERE log_url LIKE CONCAT('%%', %s, '/%s/%%')
    """

    query_success_id = """
    SELECT max(buildset_id) FROM zuul_buildset
    JOIN zuul_build ON zuul_buildset.id = zuul_build.buildset_id
    WHERE zuul_buildset.result = 'SUCCESS'
    AND zuul_buildset.pipeline = 'periodic-nightly'
    AND zuul_buildset.ref LIKE CONCAT('refs/heads/', %s)
    AND zuul_buildset.id < %s
    AND zuul_build.end_time < %s
    """

    query_success_log_url = """
    SELECT log_url FROM zuul_build
    WHERE buildset_id = %s
    ORDER BY end_time DESC
    LIMIT 1
    """

    try:
        log.debug('getting zuul buildset_id and end_time for current build number')
        cur.execute(query_get_buildset, (branch, build_number))
        current_buildset_id, end_time = list(cur)[0]
                
        log.debug('getting id of last successful buildset before current')
        cur.execute(query_success_id, (branch, current_buildset_id, end_time))
        last_success_id = list(cur)[0][0]

        log.debug('getting log url of last successful buildset')
        cur.execute(query_success_log_url,(last_success_id,))
        log_url = list(cur)[0][0]

    except MySQLdb.OperationalError:
        log.error('error executing query, aborting')
        sys.exit(1)

    except IndexError:
        log.error('invalid values fetched from database or last successful buildset not found, aborting')
        sys.exit(1)

    except:
        log.error('unknown error (not raising exception)')
        sys.exit(1)

    finally:
        cur.close()
        db.close()
    
    last_successful = get_build_number_from_log_url(log_url,branch)
    print(last_successful)

if __name__ == '__main__':
    main()