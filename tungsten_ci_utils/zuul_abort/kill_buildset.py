#!/usr/bin/env python
from __future__ import print_function
import sys
import time
import json
import yaml
import requests
from multiprocessing.dummy import Pool
import subprocess
import argparse
try:
    import queue
except ImportError:
    import Queue
    queue = Queue


local_zuul_status = False
config = {}
worker_addresses = {}


def get_element_by_kv(l, key, value):
    for elem in l:
        if key in elem:
            if elem[key] == value:
                return elem
    return None


class RetryStrategy:

    def get_wait_time(self, retry):
        pass


class InstantRetryStrategy(RetryStrategy):

    def get_wait_time(self, retry):
        return 0


class ConstantRetryStrategy(RetryStrategy):

    def __init__(self, wait_time):
        self.wait_time = wait_time

    def get_wait_time(self, retry):
        if retry == 0:
            return 0
        return self.wait_time


class Retrier:

    def __init__(self, strategy):
        self.strategy = strategy

    def retry_call(self, callable, callable_args=[], callable_kwargs={},
                   max_tries=3):
        returned = None
        success = False
        if max_tries is None:
            max_tries = -1
        retry = 0
        while not success and retry != max_tries:
            if retry > 0:
                print("Retry, attempt {}".format(retry + 1))
            time.sleep(self.strategy.get_wait_time(retry))
            try:
                returned = callable(*callable_args, **callable_kwargs)
                if returned is not None:
                    success = True
                else:
                    print("Retrier: callable returned None")
            except Exception as e:
                # TODO print exception info, backtrace
                print("Retrier: callable raised exception {}". format(e))
            retry += 1
        if not success:
            print("Retrier: giving up after {} attempts".format(retry))
        return returned

    def retry_http_request(self):
        pass

    def retry_process(self, args):
        pass


def exceptioning_fun():
    raise Exception()


def pretty_print(obj):
    out = json.dumps(obj, indent=4)
    print(out)


_zuul_status = None


def get_zuul_status(force_fetch=False):
    global _zuul_status
    if local_zuul_status:
        with open('status.json', 'r') as status_file:
            _zuul_status = json.loads(status_file.read())
    else:
        if _zuul_status is None or force_fetch:
            zuul_status_url = 'http://zuulv3.opencontrail.org/status.json'
            req = requests.get(zuul_status_url)
            _zuul_status = req.json()
    return _zuul_status


def kill_job(arg):
    uuid, worker = arg
    ssh_key_path = config["ssh_key_path"]
    worker_address = worker_addresses.get(worker, worker)
    print("Attempting to kill {} on {} ({})".format(
        uuid, worker, worker_address))
    cmd = ["ssh", "-T", "-i", ssh_key_path, "-l", "zuul", worker_address, uuid]
    try:
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT).decode('utf8')
        ret = 0
    except subprocess.CalledProcessError as cpe:
        output = cpe.output.decode('utf8')
        ret = cpe.returncode
    print("Command {} returned code {}, output:\n{}".format(cmd, ret, output))
    return ret == 0


def kill_jobs(jobs):
    pool = Pool(processes=4)
    job_kill_results = pool.map(kill_job, jobs)
    return all(job_kill_results)


def get_buildset(buildset_id, force_fetch=False):
    zuul_status = get_zuul_status(force_fetch)
    buildset = None
    for pipeline in zuul_status["pipelines"]:
        for queue in pipeline['change_queues']:
            if len(queue['heads']) > 0:
                for head in queue['heads'][0]:
                    if head["zuul_ref"] == "Z" + buildset_id:
                        buildset = head
    if buildset is None:
        print("Buildset {} not found, exiting".format(buildset_id))
    return buildset


def buildset_is_running(buildset_id):
    return get_buildset(buildset_id, force_fetch=True) is not None


def kill_buildset(buildset_id):
    buildset = get_buildset(buildset_id)
    if buildset is None:
        print(("kill_buildset: buildset"
               " {} not found, exiting").format(buildset_id))
    jobs = []
    print('kill_buildset - killing jobs:')
    for job in buildset["jobs"]:
        if (job["end_time"] is None and job["worker"] is not None and
            job["uuid"] is not None):
            # kill running jobs
            if job["worker"]["name"] != "Unknown":
                print('job {name}, uuid {uuid}, worker {worker}'.format(**job))
                jobs.append((job["uuid"], job["worker"]["name"]))
    kill_jobs(jobs)
    return None if buildset_is_running(buildset_id) else True


def get_nightly_zuul_ref(branch="master"):
    zuul_status = get_zuul_status()
    nightly_pipeline = get_element_by_kv(
        zuul_status["pipelines"], 'name', 'periodic-nightly')
    for queue in nightly_pipeline['change_queues']:
        for head in queue['heads'][0]:
            pretty_print(head["jobs"])
            for job in head["jobs"]:
                print("uuid:", job["uuid"])
                if job["report_url"] is not None:
                    if branch in job["report_url"]:
                        return head["zuul_ref"]
    return None


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("branch")
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    branch = args.branch

    config_path = args.config
    try:
        with open(config_path, 'r') as config_file:
            config_loaded = yaml.load(config_file)
    except IOError as ioe:
        print("Config file ({}) not found, loading empty".format(config_path))
        config_loaded = {}
    config.update(config_loaded)
    worker_addresses.update(config.get("worker_addresses", {}))
    if len(branch) > 15:
        # directly specify buildset id for testing
        buildset_id = branch
    else:
        zuul_ref = get_nightly_zuul_ref(branch)
        if zuul_ref is None:
            print("Buildset for branch {} not found - exiting".format(branch))
            sys.exit(1)
        buildset_id = zuul_ref[1:]
    r = Retrier(ConstantRetryStrategy(5))
    if args.forever:
        max_tries = None
    else:
        max_tries = 20
    r.retry_call(kill_buildset, [buildset_id], max_tries=max_tries)


if __name__ == '__main__':
    main()
