import os
import json
import subprocess
import pygit2

def get_repo_obj():
    current_working_directory = os.getcwd()
    repository_path = pygit2.discover_repository(current_working_directory)
    repo = pygit2.Repository(repository_path)
    return repo

def dump_commits(sha_list):
    repo = get_repo_obj()
    data = []
    for sha in sha_list:
        commit = repo.get(sha)
        assert(sha == commit.hex)
        message_lines = commit.message.splitlines()
        title = message_lines[0]
        message = message_lines[1:]
        if len(message) > 0:
            if message[0] == "":
                del message[0]
        message = '\n'.join(message)
        obj = { "sha": commit.hex,
                "author": {
                    "email": commit.author.email,
                    "name": commit.author.name },
                "timestamp": commit.commit_time,
                "title": title,
                "message": message }
        data.append(obj)
    return data

def get_commit_list_simple(count=None):
    """Use pygit2 commit listing to return a
    Returns a list of strings: commit SHAs"""
    repo = get_repo_obj()
    commits = []
    last = repo[repo.head.target]
    walk = repo.walk(last.id, pygit2.GIT_SORT_TIME)
    i = 0
    while i is None or i < count:
        try:
            commit = next(walk)
        except StopIteration:
            break
        commits.append(commit.hex)
        i += 1
    return commits

def get_commit_list_git_cli(args):
    """Use regular git command line to obtain a list of commit SHAs to dump (as
    strings)"""
    cmd = ["git", "log", "--format=%H"]
    cmd += args
    shas = subprocess.check_output(cmd).decode('utf8')
    print(shas)
    shas = shas.splitlines()
    print(shas)
    return shas

if __name__ == "__main__":
    sha_list = get_commit_list_simple(10)
    log_data = dump_commits(sha_list)
    print(json.dumps(log_data, indent=4))
