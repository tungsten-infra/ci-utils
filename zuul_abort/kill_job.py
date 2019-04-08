from __future__ import print_function
import psutil

def kill_ancestor(pid_list):
    """Kill the top process in the hierarchy. All the provided pids should form
    a single process hierarchy, otherwise the function exits without doing
    anything"""
    top_pid = 0
    return 0

def pgrep(word):
    """Searches commandlines of running processes for word. Returns a list of
    pids"""
    pids = []
    return []

if __name__ == "__main__":
    print(pgrep("vim"))
