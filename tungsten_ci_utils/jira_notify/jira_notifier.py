import logging
import yaml
import mysql.connector

from jira import JIRA

with open('config.yaml', 'r') as yf:
    cfg = yaml.load(yf)

log = logging.getLogger(__name__)


def set_logging():
    log.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    log.addHandler(console)


C_DB_NAME = cfg['zuul_cache']['db']
C_DB_PASS = cfg['zuul_cache']['password']
C_DB_USER = cfg['zuul_cache']['user']
C_DB_HOST = cfg['zuul_cache']['host']
C_DB_PORT = cfg['zuul_cache']['port']

Z_DB_NAME = cfg['zuul_db']['database']
Z_DB_PASS = cfg['zuul_db']['password']
Z_DB_USER = cfg['zuul_db']['user']
Z_DB_HOST = cfg['zuul_db']['host']
Z_DB_PORT = cfg['zuul_db']['port']

J_HOST = cfg['jira']['host']
J_USER = cfg['jira']['username']
J_PASS = cfg['jira']['password']

ZUUL_CONFIG = {
    'user': Z_DB_USER,
    'passwd': Z_DB_PASS,
    'host': Z_DB_HOST,
    'database': Z_DB_NAME,
    'port': Z_DB_PORT
}
CACHE_NUMBER = {
    'user': C_DB_USER,
    'passwd': C_DB_PASS,
    'host': C_DB_HOST,
    'database': C_DB_NAME,
    'port': C_DB_PORT
}
JIRA_OPTIONS = {
    'server': J_HOST
}


class CacheConnector(object):
    def __init__(self, config):
        self.dbconn = mysql.connector.connect(**config)

    def __enter__(self):
        return self.dbconn.cursor(buffered=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dbconn.close()


def get_last_fail_buildset():
    """
    Search for last failed nightly build in zuul database
    :return: { buildset : buildset_id, change_ref : link }:dict
    """
    with CacheConnector(ZUUL_CONFIG) as c:
        log.info('connected to zuul cache database')
        c.execute(
            "SELECT zuul_ref, ref_url FROM zuul_buildset WHERE zuul_ref = (SELECT max(zuul_ref) FROM zuul_buildset WHERE result = 'FAILURE' AND pipeline = 'periodic-nightly')")
        data = c.fetchone()
        log.info('buildset - {} | change_ref - {}'.format(data[0], data[1]))
        return {'buildset': data[0],
                'change_ref': data[1]}


def get_failed_build_num(buildset):
    """
    :param buildset: buildset zuul number: str
    :return {'version: branch, build_number: special build number}:dict
    """
    with CacheConnector(CACHE_NUMBER) as c:
        log.info('connected to zuul builds database')
        c.execute("SELECT version, build_number FROM build_metadata_cache WHERE zuul_buildset_id = %s", (buildset[1:],))
        data = c.fetchone()
        logging.info('version - {} | build number - {}'.format(data[0], data[1]))
        return {'version': data[0], 'build_number': data[1]}


def search_for_ticket(jira, version, build_number):
    """
Function responsible for searching jira issues by summary
    :param jira: open connection to Jira: jira.JIRA
    :param version: target build branch: str
    :param build_number: zuul build number: str
    :return: issue found: bool
    """
    log.info('connected to jira - {}'.format(jira.server_info()))
    issues = jira.search_issues('project = JD AND type=Incident AND updated >= -21d')
    found = [issue for issue in issues if version in issue.fields.summary and str(build_number) in issue.fields.summary]
    log.info('found issue - {}'.format(*[issue.permalink() for issue in found]))
    if found:
        return [issue.permalink() for issue in found]


def create_new_issue(jira, version, build_number, details):
    """
    :param jira: open connection to Jira: jira.JIRA
    :param version: target build branch: str
    :param build_number: zuul build number: str
    :param details: zuul link to log: str
    :return: new issue link: str
    """
    log.info('creating ticket')
    issue_dict = {
        'project': {'id': '10004'},
        'summary': 'Nightly - {} - {} - FAILED!'.format(version, build_number),
        'description': 'Build number {} on branch {} FAILED!\nLogs can be found here: {}'.format(build_number, version,
                                                                                                 details),
        'issuetype': {'name': 'Incident'},
        "components": [{"name": 'Buildcop'}],
    }
    log.info('parameters - {}'.format(issue_dict))
    new_issue = jira.create_issue(fields=issue_dict)
    log.info('new issue link - {}'.format(new_issue.permalink()))
    return new_issue.permalink()


def main():
    set_logging()
    build = get_last_fail_buildset()
    identy_dict = get_failed_build_num(build['buildset'])
    build_number = identy_dict['build_number']
    version = identy_dict['version']
    jira = JIRA(JIRA_OPTIONS, basic_auth=(J_USER, J_PASS))
    issue = search_for_ticket(jira, version, build_number)
    if not issue:
        create_new_issue(jira, version, build_number, build['change_ref'])


if __name__ == '__main__':
    main()
