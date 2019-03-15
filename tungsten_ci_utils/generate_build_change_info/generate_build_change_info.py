import os
import sys
import re
import requests
from requests.auth import HTTPBasicAuth
import tempfile
import subprocess
import yaml
import json
import logging
import pygit2
from jinja2 import Template
import io
import argparse


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
git_dir = '/tmp/build_changes'
ignored_project_attributes = ['required']


def log_url(branch, build_number, config):
    return config["log_url_template"].format(branch, build_number)


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


def fetch_projects_from_job(branch, build_number, job_name, config):
    log.debug('fetch_projects_from_job: %s %s %s',
              branch, build_number, job_name)
    projects = {}
    job_log_url = log_url(branch, build_number, config) + '/' + job_name
    inventory_url = job_log_url + '/zuul-info/inventory.yaml'
    inventory_req = requests.get(inventory_url)
    if inventory_req.status_code != 200:
        log.warning("Non-200 status code for %s, skipping job %s %s",
                    inventory_url, job_name, build_number)
        return projects
    inventory = yaml.load(inventory_req.text)
    gitlog_url = job_log_url + '/' + config["gitlog_path"]
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
    project_key = "short_name"
    if config["new_inventory"]:
        projects2 = []
        for canonical_name, p in projects.items():
            projects2.append(p)
        projects = projects2
        project_key = "canonical_name"
    for line in gitlog.splitlines():
        if line.startswith('#'):
            project = line.split()[1]
        elif project is not None:
            sha = line.split()[0]
            get_by_value(projects, project_key, project)["sha"] = sha
            project = None
    for p in projects:
        remove_keys(p, ignored_project_attributes)
    return projects


def fetch_all_projects_from_buildset(branch, build_number, config):
    projects = {}
    for job_name in config["job_list"]:
        job_projects = fetch_projects_from_job(branch, build_number, job_name,
                                               config)
        for p in job_projects:
            canonical_name = p['canonical_name']
            if canonical_name in projects:
                if projects[canonical_name] != p:
                    # TODO support the case when this happens legitimately,
                    # e.g. when we'll have two different branch checkouts of
                    # the same project (contrail-dpdk for different SKUs)
                    # The logic should be rewritten to find differences between
                    # jobs and not the whole set of projects in buildset.
                    log.error("Two different project states for %s: %s %s, "
                              "error occured during fetching job %s. "
                              "(Overriding)",
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


def sync_git_repos(projects, branch, config):
    if not os.path.isdir(config["git_dir"]):
        os.mkdir(config["git_dir"])
    for canonical_name, project in projects.items():
        repo_path = get_repo_path(config, project)
        if not os.path.isdir(repo_path):
            # TODO check for remote branch existence and clone with
            # --single-branch to save time
            subprocess.check_call(
                ["git", "clone", "https://" + canonical_name, canonical_name],
                cwd=config["git_dir"])
        else:
            log.info("Fetching origin for %s", canonical_name)
            subprocess.check_call(["git", "fetch", "origin"], cwd=repo_path)


def get_commit_list_git_cli(previous_sha, current_sha, cwd=None, args=[]):
    """Use regular git command line to obtain a list of commit SHAs to dump (as
    strings)"""
    if (previous_sha == current_sha or
        previous_sha is None or
            current_sha is None):
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


def get_change_info(change_id, config):
    change_id_quoted = requests.utils.quote(change_id, safe='~')
    if config.get("gerrit_http_password", None):
        auth_prefix = '/a'
        auth = (config["gerrit_username"], config["gerrit_http_password"])
    else:
        auth_prefix = ''
        auth = None
    change_url = config["gerrit_host"] + \
        auth_prefix + "/changes/" + change_id_quoted
    print(change_url, change_id, config["verify_gerrit_ssl"])
    req = requests.get(
        change_url, verify=config["verify_gerrit_ssl"], auth=auth)
    resp = '\n'.join(req.text.splitlines()[1:])
    if req.status_code != 200:
        print(change_url, 'non-200', change_id, resp, req.status_code)
        return None
    try:
        info = json.loads(resp)
    except Exception as e:
        print(change_url, 'non-json', change_id, resp, req.status_code)
        return None
    converted = {
        "topic": info.get("topic", ""),
        "number": info["_number"],
        "url": config["gerrit_host"] + '/' + str(info["_number"]),
        "id": change_id
    }
    return converted


def get_lp_bug_info(bug_id):
    bug_url = 'https://api.launchpad.net/1.0/bugs/{}'.format(bug_id)
    bug = {"description": "Not found", "title": "Not found"}
    req = requests.get(bug_url)
    if req.status_code == 200:
        bug_info = req.json()
        bug["description"] = bug_info["description"]
        bug["title"] = bug_info["title"]
    elif req.status_code == 404:
        log.warning("Bug %s not found in LP", bug_url)
    else:
        log.warning("Bug %s: unexpected return code %s", req.status_code)
    return bug


def dump_commit(sha, project, branch, config, repo_path=None):
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
    obj = {
        "sha": commit.hex,
        "author": {
            "email": commit.author.email,
            "name": commit.author.name},
        "timestamp": commit.commit_time,
        "title": title,
        "message": message
    }
    obj["change"] = None
    obj["bugs"] = []
    for line in message_lines:
        if line.startswith("Change-Id:"):
            change_id = line.split()[1]
            # first, try to fetch the change info by plain Change Id
            # this will work for unique change-ids and return 404 for
            # duplicates (e.g. duplicates are created during cherry-picking)
            change_info = get_change_info(change_id, config)
            # now, try to fetch the change info using full id
            # (project+branch+id)
            # TODO with Zuul's override-checkout, the branch doesn't have to be
            # the build branch, in this case this fetch will fail.
            if change_info is None:
                change_info = get_change_info(
                    project["name"] + "~" + branch + "~" + change_id, config)
            obj["change"] = change_info
        else:
            bug_match = re.match(r'^(\S+)-Bug: +#(\d+)', line)
            if bug_match is not None:
                bug_id = bug_match.group(2)
                resolution = bug_match.group(1)
                bug_info = get_lp_bug_info(bug_id)
                bug_info.update({
                    "id": bug_id,
                    "url": "https://launchpad.net/bugs/" + bug_id,
                    "resolution": resolution
                })
                obj["bugs"].append(bug_info)
    return obj


def get_repo_path(config, project):
    return os.path.join(config["git_dir"], project["canonical_name"])


def get_changes(git_dir, projects, branch, config):
    for canonical_name, project in projects.items():
        repo_path = get_repo_path(config, project)
        try:
            sha_list = get_commit_list_git_cli(
                project["revisions"]["previous"],
                project["revisions"]["current"],
                cwd=repo_path)
        except subprocess.CalledProcessError as cpe:
            log.warning("Failed to obtain sha list for %s, %s",
                        canonical_name, cpe)
            project["errors"] = project.get("errors", [])
            project["errors"].append("Failed to obtain sha list")
            project["changes"] = []
            return
        commits = [dump_commit(sha, project, branch, config, repo_path)
                   for sha in sha_list]
        project["changes"] = commits


def render_template(context, template):
    with io.open(template, 'r', encoding='utf-8') as template_file:
        template = template_file.read()
    template = Template(template)
    out = template.render(**context)
    return out


def summarize_bug_info(projects):
    bugs = {}
    for canonical_name, project in projects.items():
        for change in project["changes"]:
            for bug in change["bugs"]:
                int_id = int(bug["id"])
                if int_id not in bugs:
                    bugs[int_id] = {
                        "changes": [],
                        "url": bug["url"],
                        "title": bug["title"]
                    }
                bugs[int_id]["changes"].append(
                    {"project": canonical_name,
                     "commit": change,
                     "resolution": bug["resolution"]})
    bugs_list = sorted(list(bugs.items()))
    for bug_id, bug in bugs_list:
        bug["changes"].sort(key=lambda x: x["commit"]["change"]["number"])
    return bugs_list


def load_config():
    # TODO implement dynamic loading of buildset job names from Zuul DB
    config = {}
    with open('config_default.yaml', 'r') as default_config_file:
        config = yaml.load(default_config_file)
    try:
        with open('config.yaml', 'r') as config_file:
            config.update(yaml.load(config_file))
    except IOError as ioe:
        pass
    config["job_list"] = [j for j in config["job_list"]
                          if j not in config["job_blacklist"]]
    return config


def fetch_json(source):
    if source.startswith('http'):
        req = requests.get(source)
        if req.status_code != 200:
            log.warning('JSON HTTP request failed for %s: (%s) %s',
                        source, req.status_code, req.text)
            return {}
        json_str = req.text
    else:
        with open(source, 'r') as source_file:
            json_str = source_file.read()
    try:
        obj = json.loads(json_str)
        return obj
    except Exception as e:
        log.warning('JSON HTTP decoding failed for %s: %s %s',
                    source, e, req.text)
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--changes-json", action="append")
    parser.add_argument("--deployment-run", action="store_true") # a flag helpful to determine if the script was run via ansible or manually
    parser.add_argument("branch")
    parser.add_argument("build_number")
    parser.add_argument("previous_build_number", nargs='?')
    args = parser.parse_args()
    branch = args.branch
    deployment_run = args.deployment_run

    if args.previous_build_number is not None:
        previous_build_number, build_number = sorted([int(args.previous_build_number), int(args.build_number)])
    else:
        build_number = int(args.build_number)
        previous_build_number = str(int(build_number)-1)
        

    # if pointed to already generated json file(s), load the data and skip the
    # whole generation process directly to the html rendering step
    if args.changes_json is not None:
        projects = {}
        for source in args.changes_json:
            projects.update(fetch_json(source))
    else:
        config = load_config()

        read_projects_from_logserver = True

        if read_projects_from_logserver:
            current_projects = fetch_all_projects_from_buildset(
                branch, build_number, config)
            previous_projects = fetch_all_projects_from_buildset(
                branch, previous_build_number, config)
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
        if config["fetch_repos"]:
            sync_git_repos(projects, branch, config)
        get_changes(git_dir, projects, branch, config)

    bugs = summarize_bug_info(projects)

    context = {
        "projects": projects,
        "build_number_prev": previous_build_number,
        "build_number": build_number,
        "bugs": bugs,
        "deployment_run": deployment_run
    }
    with open('changes.json', 'w') as out:
        json.dump(projects, out, indent=4)
    with io.open('changes.html', 'w', encoding='utf-8') as out:
        out.write(render_template(context, 'changes.html.tpl'))
    with io.open('bugs.html', 'w', encoding='utf-8') as out:
        out.write(render_template(context, 'bugs.html.tpl'))


if __name__ == '__main__':
    main()
