#!/usr/bin/python
from __future__ import print_function
import os
import sys
import psutil


def find_ancestor(pid_list):
    """Get the top process in the hierarchy"""
    external_parent = None
    top_pid = None
    for pid in pid_list:
        proc = psutil.Process(pid)
        while proc.pid in pid_list:
            last_pid = proc.pid
            proc = proc.parent()
        if proc.pid != 1:
            if external_parent is None:
                external_parent = proc.pid
                top_pid = last_pid
            else:
                if external_parent != proc.pid:
                    print("Multiple job process roots, exiting")
                    sys.exit(1)
    return top_pid


def find_child(pid_list):
    """Get the lowest (one of the lowest) process in the hierarchy"""
    child_pid = None
    parents = set()
    for pid in pid_list:
        proc = psutil.Process(pid)
        parent = proc.ppid()
        if parent in pid_list:
            parents.add(parent)
    for pid in pid_list:
        if pid not in parents:
            child_pid = pid
    if child_pid is None:
        try:
            child_pid = pid_list[0]
        except IndexError:
            return None
    return child_pid


def pgrep(word):
    """Searches commandlines of running processes for word. Returns a list of
    pids"""
    pids = []
    for proc in psutil.process_iter():
        cmd = ' '.join(proc.cmdline())
        if word in cmd and proc.pid != os.getpid():
            pids.append(proc.pid)
            print('=======================', proc.ppid(), proc.pid, cmd[:20])
    return pids


if __name__ == "__main__":
    job_pids = pgrep(sys.argv[1])
    if len(job_pids) > 0:
        # find_child will cause the JOB to fail
        # find_ancestor will cause the job to be ABORTED and RESTARTED
        youngest_pid = find_child(job_pids)
    else:
        print('No running job processes found, exiting')
        return
    print(youngest_pid)
    if youngest_pid is not None:
        youngest_proc = psutil.Process(youngest_pid)
        youngest_proc.kill()
