import os
import sys
import re
import requests
import tempfile
import subprocess
import yaml
import json
import logging
import pygit2
from jinja2 import Template
import io

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

#git_dir = tempfile.mkdtemp(prefix='build_changes')
git_dir = '/tmp/build_changes'

ignored_project_attributes = ['required']


def log_url(branch, build_number):
    return 'http://logs.tungsten.io/periodic-nightly/review.opencontrail.org/{}/{}/'.format(branch, build_number)


def get_by_value(dict_list, key, value):
    for d in dict_list:
        if (key, value) in d.items():
            return d
    return None


def dict_equal_but(d1, d2, ignored_keys):
    return True


def remove_keys(d, keys):
    for k in keys:
        del d[k]


def fetch_projects_from_job(branch, build_number, job_name):
    log.debug('fetch_projects_from_job: %s %s %s',
              branch, build_number, job_name)
    projects = {}
    job_log_url = log_url(branch, build_number) + '/' + job_name
    inventory_url = job_log_url + '/zuul-info/inventory.yaml'
    inventory_req = requests.get(inventory_url)
    if inventory_req.status_code != 200:
        log.warning("Non-200 status code for %s, skipping job %s %s",
                    inventory_url, job_name, build_number)
        return projects
    inventory = yaml.load(inventory_req.text)
    gitlog_url = job_log_url + '/zuul-info/gitlog.builder.md'
    gitlog_req = requests.get(gitlog_url)
    if gitlog_req.status_code != 200:
        log.warning("Non-200 status code for %s, skipping job %s %s",
                    gitlog_url, job_name, build_number)
        return projects
    gitlog = gitlog_req.text
    try:
        projects = inventory['all']['vars']['zuul']['projects']
    except TypeError:
        log.error(inventory)
        sys.exit(1)
    project = None
    for line in gitlog.splitlines():
        if line.startswith('#'):
            project = line.split()[1]
        elif project is not None:
            sha = line.split()[0]
            get_by_value(projects, 'short_name', project)["sha"] = sha
            project = None
    for p in projects:
        remove_keys(p, ignored_project_attributes)
    return projects


def fetch_all_projects_from_buildset(branch, build_number, job_list):
    projects = {}
    for job_name in job_list:
        job_projects = fetch_projects_from_job(branch, build_number, job_name)
        for p in job_projects:
            canonical_name = p['canonical_name']
            if canonical_name in projects:
                if projects[canonical_name] != p:
                    log.error("Two different project states for %s: %s %s, error occured during fetching job %s. (Overriding)",
                              canonical_name, branch, build_number, job_name)
                    log.error("Existing: " +
                              json.dumps(projects[canonical_name], indent=4))
                    log.error("New: " + json.dumps(p, indent=4))
            projects[canonical_name] = p
    return projects


projects = {
    'Juniper/contrail-controller': {'previous': 'abcd', 'current': '1234'},
    'Juniper/contrail-vrouter': {'previous': 'abcd', 'current': '1234'},
}


def merge_projects(previous, current):
    # TODO check if both projects sets are equal
    for canonical_name, project in current.items():
        prev_sha = previous.get(canonical_name, {}).get("sha", None)
        project["revisions"] = {
            "previous": prev_sha, "current": project["sha"]}
        del project["sha"]


def sync_git_repos(git_dir, projects, branch):
    if not os.path.isdir(git_dir):
        os.mkdir(git_dir)
    for canonical_name, project in projects.items():
        repo_path = os.path.join(git_dir, project['short_name'])
        if not os.path.isdir(repo_path):
            # TODO check for remote branch existence and clone with
            # --single-branch to save time
            subprocess.check_call(
                ["git", "clone", "https://" + canonical_name], cwd=git_dir)
        else:
            log.info("Fetching origin for %s", canonical_name)
            subprocess.check_call(["git", "fetch", "origin"], cwd=repo_path)


def get_commit_list_git_cli(previous_sha, current_sha, cwd=None, args=[]):
    """Use regular git command line to obtain a list of commit SHAs to dump (as
    strings)"""
    if previous_sha == current_sha or previous_sha is None or current_sha is None:
        return []
    cmd = ["git", "log", "--format=%H", previous_sha + '..' + current_sha]
    shas = subprocess.check_output(cmd, cwd=cwd).decode('utf8')
    shas = shas.splitlines()
    return shas


def get_repo_obj(git_workspace_path=None):
    if git_workspace_path is None:
        git_workspace_path = os.getcwd()
    repository_path = pygit2.discover_repository(git_workspace_path)
    repo = pygit2.Repository(repository_path)
    return repo


def get_change_info(change_id, gerrit_host='https://review.opencontrail.org'):
    change_id_quoted = requests.utils.quote(change_id, safe='~')
    req = requests.get(gerrit_host + "/changes/" + change_id_quoted)
    resp = '\n'.join(req.text.splitlines()[1:])
    if req.status_code != 200:
        print('non-200', change_id)
    try:
        info = json.loads(resp)
    except Exception as e:
        print(resp)
    converted = {
        "topic": info.get("topic", ""),
        "number": info["_number"],
        "url": gerrit_host + '/' + str(info["_number"]),
        "id": change_id
    }
    return converted


def dump_commit(sha, project, branch, repo_path=None):
    repo = get_repo_obj(repo_path)
    data = []
    commit = repo.get(sha)
    assert(sha == commit.hex)
    message_lines = commit.message.splitlines()
    title = message_lines[0]
    message = message_lines[1:]
    if len(message) > 0:
        if message[0] == "":
            del message[0]
    message = '\n'.join(message)
    obj = {"sha": commit.hex,
           "author": {
               "email": commit.author.email,
               "name": commit.author.name},
           "timestamp": commit.commit_time,
           "title": title,
           "message": message}
    obj["change"] = None
    obj["bugs"] = []
    for line in message_lines:
        if line.startswith("Change-Id:"):
            change_id = line.split()[1]
            change_info = get_change_info(
                project["name"] + "~" + branch + "~" + change_id)
            obj["change"] = change_info
        else:
            bug_match = re.match(r'^(\S+)-Bug: +#(\d+)', line)
            if bug_match is not None:
                bug_id = bug_match.group(2)
                resolution = bug_match.group(1)
                obj["bugs"].append(
                    {"id": bug_id, "url": "https://launchpad.net/bugs/" + bug_id, "resolution": resolution})
    return obj


def get_changes(git_dir, projects, branch):
    for canonical_name, project in projects.items():
        repo_path = os.path.join(git_dir, project['short_name'])
        try:
            sha_list = get_commit_list_git_cli(
                project["revisions"]["previous"], project["revisions"]["current"], cwd=repo_path)
        except subprocess.CalledProcessError as cpe:
            log.warning("Failed to obtain sha list for %s, %s",
                        canonical_name, cpe)
            project["errors"] = project.get("errors", [])
            project["errors"].append("Failed to obtain sha list")
            project["changes"] = []
            return
        commits = [dump_commit(sha, project, branch, repo_path)
                   for sha in sha_list]
        project["changes"] = commits


def render_changes(projects, context):
    with io.open('changes.html.tpl', 'r', encoding='utf-8') as template_file:
        template = template_file.read()
    template = Template(template)
    out = template.render(**context)
    return out


job_list = [
    'build-variables-init',
    'contrail-build-vro-plugin',
    'contrail-go-docker',
    'contrail-vnc-build-containers-centos7-newton',
    'contrail-vnc-build-containers-centos7-ocata',
    'contrail-vnc-build-containers-centos7-queens',
    'contrail-vnc-build-containers-rhel7-ocata',
    'contrail-vnc-build-containers-rhel7-queens',
    'contrail-vnc-build-package-centos74',
    'contrail-vnc-build-package-rhel7-ocata',
    'contrail-vnc-build-package-rhel7-queens',
    'contrail-vnc-build-test-containers',
    'contrail-vnc-publish-containers-nightly',
    'post-nightly-registry-port'
]

job_blacklist = ['build-variables-init', 'post-nightly-registry-port']
job_list = [j for j in job_list if j not in job_blacklist]


def main():
    branch = sys.argv[1]
    build_number = sys.argv[2]
    current_job_list = job_list
    previous_build_number = str(int(build_number)-1)
    previous_job_list = job_list

    read_projects_from_logserver = True
    do_sync_git_repos = True

    if read_projects_from_logserver:
        current_projects = fetch_all_projects_from_buildset(
            branch, build_number, job_list)
        previous_projects = fetch_all_projects_from_buildset(
            branch, previous_build_number, previous_job_list)
        with open('projects.json', 'w') as pfile:
            json.dump(current_projects, pfile, indent=4)
        with open('projects_prev.json', 'w') as pfile:
            json.dump(previous_projects, pfile, indent=4)
    else:
        with io.open('projects.json', 'r', encoding='utf-8') as pfile:
            current_projects = json.load(pfile)
        with io.open('projects_prev.json', 'r', encoding='utf-8') as pfile:
            previous_projects = json.load(pfile)

    merge_projects(previous_projects, current_projects)
    projects = current_projects
    if do_sync_git_repos:
        sync_git_repos(git_dir, projects, branch)
    get_changes(git_dir, projects, branch)
    #print(json.dumps(projects, indent=4))
    # with open('final.json', 'w') as out:
    #    json.dump(projects, out, indent=4)
    # with open('final.json', 'r') as pfile:
    #    projects = json.load(pfile)

    context = {
        "projects": projects,
        "build_number_prev": previous_build_number,
        "build_number": build_number
    }
    with open('changes.json', 'w') as out:
        json.dump(projects, out, indent=4)
    with io.open('changes.html', 'w', encoding='utf-8') as out:
        out.write(render_changes(projects, context))


if __name__ == '__main__':
    main()
