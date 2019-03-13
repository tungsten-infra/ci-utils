import sys
import argparse
import MySQLdb
import logging
import json

log = logging.getLogger(__name__)

def set_logging():
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    log.addHandler(console)

set_logging()

def get_json_data(file):
    json_file = open(file).read()
    data = json.loads(json_file)
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials-json", action="append")
    parser.add_argument("branch")
    parser.add_argument("build_number")
    args = parser.parse_args()
    branch = str(args.branch)
    credentials_json = args.credentials_json[0]

    build_number = int(args.build_number)
    og_build_number = build_number
    build_number -= 1

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
        log.error('Database connection error')
        sys.exit(1)

    last_successful = False

    while (build_number > 0) and (not last_successful):
        query = """
        SELECT result FROM zuul_buildset WHERE id IN 
        (SELECT buildset_id FROM zuul_build WHERE log_url LIKE CONCAT('%%periodic-nightly%%/', %s, '/%s%%'))
        """

        log.debug('checking if buildset %s was successful', build_number)

        try:
            cur.execute(query, (branch, build_number))
            result = list(cur)
        except:
            log.error('Query execution error')
            sys.exit(1)

        if len(result) > 0:
            if result[0][0] == 'SUCCESS':
                last_successful = build_number
                log.debug('last successful buildset before %s found, number: %s', og_build_number, last_successful)
                print(last_successful)
            elif result[0][0] == 'FAILURE':
                log.debug('buildset %s was a failure', build_number)
                build_number -= 1
            else:
                log.warning('unknown buildset result for current iteration (build number %s)', build_number)
        else:
            log.debug('last successful build not found in the database')
            break

    db.close()

if __name__ == '__main__':
    main()