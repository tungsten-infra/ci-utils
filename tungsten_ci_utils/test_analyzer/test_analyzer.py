from __future__ import print_function
from lxml import etree
import json
import os
import yaml
# import db
import datetime
import argparse
import re


def search_for_files(path='/var/www/logs',
                     filename_pattern=re.compile(r'.*\.xml'), limit=None):
    found = []
    count = 0
    for d, dirs, files in os.walk(path):
        for f in files:
            if filename_pattern.match(f):
                found.append(os.path.join(d, f))
                count += 1
                print(d, f)
                if limit is not None:
                    if count > limit:
                        return found
    return found


def get_job_metadata(path):
    while path != '/':
        path = os.path.dirname(path)
        dirs = [d for d in os.listdir(
            path) if os.path.isdir(os.path.join(path, d))]
        if 'zuul-info' in dirs:
            with open(path + '/zuul-info/inventory.yaml',
                      'r') as inventory_file:
                inventory = yaml.load(inventory_file)
                metadata = inventory['all']['vars']['zuul']
                return metadata


def main():
    reports = search_for_files(filename_pattern=re.compile(
        'TESTS-TestSuites.xml'), limit=100)
    for r in reports:
        metadata = get_job_metadata(r)
        print(r)
        print(json.dumps(metadata, indent=4))


def read_xml(filename):
    doc = etree.parse(filename)
    return doc


def dump_xml(node):
    return etree.tostring(node, pretty_print=True).decode()


class SafeObjectEncoder(json.JSONEncoder):
    def default(self, obj): return str(obj)


def pretty_json(obj):
    return json.dumps(obj, cls=SafeObjectEncoder, indent=4)


def read_test_info_from_xml(doc, quirks=None):
    # naive schema tests
    assert(doc.getroot().tag == "testsuites")
    for testsuite in doc.getroot():
        assert(testsuite.tag == "testsuite")
        for testcase in testsuite:
            assert(testcase.tag == "testcase")
    # for child in doc.getroot():
    #    print(child.tag)
    testsuites = doc.findall("testsuite")
    records = []
    for testsuite in testsuites:
        print(testsuite.attrib)
        suitename = testsuite.get("name")
        suitepackage = testsuite.get("package")
        for testcase in testsuite:
            assert('.' in testcase.get("time"))
            time = testcase.get("time").split('.')
            milliseconds = int(time[0])*1000 + int(time[1])
            caseclass = testcase.get("classname")
            casename = testcase.get("name")
            if testcase.find("failure") is not None:
                result = "FAILED"
            elif testcase.find("skipped") is not None:
                result = "SKIPPED"
            else:
                result = "SUCCESS"
            record = {
                "casename": casename,
                "caseclass": caseclass,
                "suitename": suitename,
                "suitepackage": suitepackage,
                "milliseconds": milliseconds,
                "result": result,
                "finish_datetime": datetime.datetime.now()
            }
            if quirks == 'sanity':
                casename, tags = casename.split('[')
                tags = tags[:-1]
                tags = tags.split(',')
                record['casename'] = casename
                record['tags'] = tags
            # testrun = db.TestRun(**record)
            # testrun.save()
            records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("junit_xml_files", nargs="*")
    parser.add_argument("--quirks", type=str)
    parser.add_argument("--read-job-metadata", action='store_true')
    args = parser.parse_args()
    build_id = "abcdef"
    project = "github.com/Juniper/contrail-test"
    project_commit = "abcdef123"
    execution = 1
    build_info = {
        'build_id': build_id,
        'project': project,
        'project_commit': project_commit,
        'execution': execution
    }
    tests = []
    for f in args.junit_xml_files:
        doc = read_xml("sanity.xml")
        records = read_test_info_from_xml(doc, args.quirks)
        for r in records:
            r.update(build_info)
        tests += records
    print(pretty_json(tests))


if __name__ == "__main__":
    main()
