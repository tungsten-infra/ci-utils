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


ZUUL_CONFIG = {
    'user': cfg['zuul_db']['user'],
    'passwd': cfg['zuul_db']['password'],
    'host': cfg['zuul_db']['host'],
    'database': cfg['zuul_db']['database'],
    'port': cfg['zuul_db']['port']
}
CACHE_CONFIG = {
    'user': cfg['zuul_cache']['user'],
    'passwd': cfg['zuul_cache']['password'],
    'host': cfg['zuul_cache']['host'],
    'database': cfg['zuul_cache']['db'],
    'port': cfg['zuul_cache']['port']
}
JIRA_OPTIONS = {
    'server': cfg['jira']['host']
}


class DatabaseConnector(object):
    def __init__(self, config):
        self.dbconn = mysql.connector.connect(**config)

    def __enter__(self):
        return self.dbconn.cursor(buffered=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dbconn.close()


def get_last_build_info(buildset_id):
    """
    Search for last nightly build in zuul database
    :param buildset_id: zuul build id
    :return: { ref_url : link, result : build result}:dict
    """
    with DatabaseConnector(ZUUL_CONFIG) as c:
        log.info('connected to zuul cache database')
        c.execute(
            "SELECT ref_url, result FROM zuul_buildset WHERE zuul_ref = %s", (('z' + buildset_id),))
        data = c.fetchone()
        return {'ref_url': data[0], 'result': data[1]}


def get_build_on_branch(version):
    """
    get mapping of build number and buildset_id
    :param version: branch of target build
    :return: [build_number, buildset_id]:list
    """
    with DatabaseConnector(CACHE_CONFIG) as c:
        c.execute(
            "SELECT build_number,zuul_buildset_id FROM build_metadata_cache WHERE build_number = (SELECT max(build_number) FROM build_metadata_cache WHERE version = %s)",
            (version,))
        data = c.fetchall()
        return [data[-1][0], data[-1][1]]


def search_for_ticket(jira, version, build_number):
    """
Function responsible for searching jira issues by summary
    :param jira: open connection to Jira: jira.JIRA
    :param version: target build branch: str
    :param build_number: zuul build number: str
    :return: issue found: bool
    """
    print(version, build_number)
    log.info('connected to jira - {}'.format(jira.server_info()))
    issues = jira.search_issues('project = JD AND type=Incident AND updated >= -21d')
    #found = [issue for issue in issues if version in issue.fields.summary and str(build_number) in issue.fields.summary]
    found = []
    for issue in issues:
        if version in issue.fields.summary and str(build_number) in issue.fields.summary:
            found.append(issue)
    if found:
        log.info('found issue - {}'.format(*[issue.permalink() for issue in found]))
        return [issue.permalink() for issue in found]
    else:
        log.info('issue not found in jira')


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

    jira = JIRA(JIRA_OPTIONS, basic_auth=(cfg['jira']['username'], cfg['jira']['password']))
    for branch in cfg['branches']:
        build_number, buildset_id = get_build_on_branch(branch)
        info = get_last_build_info(buildset_id)
        if info['result'] == 'FAILURE':
            found = search_for_ticket(jira, branch, build_number)
            if not found:
                create_new_issue(jira, branch, build_number, info['ref_url'])


if __name__ == '__main__':
    main()
