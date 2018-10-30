from __future__ import print_function
from lxml import etree
import json
import os
import yaml
import db
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
                    if count >= limit:
                        return found
    return found


def get_job_metadata(path):
    while path != '/':
        path = os.path.dirname(path)
        dirs = [d for d in os.listdir(
            path) if os.path.isdir(os.path.join(path, d))]
        if 'zuul-info' in dirs:
            try:
                with open(path + '/zuul-info/inventory.yaml',
                          'r') as inventory_file:
                    inventory = yaml.load(inventory_file)
                    metadata = inventory['all']['vars']['zuul']
                    return metadata
            except IOError:
                return None


def read_xml(filename):
    doc = etree.parse(filename)
    return doc


def dump_xml(node):
    return etree.tostring(node, pretty_print=True).decode()


class SafeObjectEncoder(json.JSONEncoder):
    def default(self, obj): return str(obj)


def pretty_json(obj):
    return json.dumps(obj, cls=SafeObjectEncoder, indent=4)


def load_properties_from_xml(node):
    props = {}
    for prop in node:
        assert(prop.tag == 'property')
        props[prop.get('name')] = prop.get('value')
    return props


def read_test_info_from_xml(doc, quirks=None):
    # naive schema tests
    assert(doc.getroot().tag == "testsuites")
    for testsuite in doc.getroot():
        assert(testsuite.tag == "testsuite")
        for testcase in testsuite:
            print(testcase.tag)
            assert(testcase.tag in ["testcase", "properties"])
    # for child in doc.getroot():
    #    print(child.tag)
    testsuites = doc.findall("testsuite")
    testsuite_records = []
    records = []
    for testsuite in testsuites:
        print(testsuite.attrib)
        suitename = testsuite.get("name")
        suitepackage = testsuite.get("package")
        for testcase in testsuite.findall('testcase'):
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
                if '[' in casename:
                    casename, tags = casename.split('[')
                    tags = tags[:-1]
                    tags = tags.split(',')
                    record['casename'] = casename
                    record['tags'] = tags
            # testrun = db.TestRun(**record)
            # testrun.save()
            records.append(record)
        properties = {}
        for properties_node in testsuite.findall('properties'):
            print('reading props')
            properties.update(load_properties_from_xml(properties_node))
        print(json.dumps(properties, indent=4))
    return records


def save_records(records):
    for r in records:
        db_record = db.TestRun(**r)
        db_record.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("junit_xml_files", nargs="*")
    parser.add_argument("--quirks", type=str, help="flag to enable special parsing behavior for different flavors of junit xml files. Possible values: sanity")
    parser.add_argument("--read-job-metadata", action='store_true', default=False, help="Whether to find and parse inventory.yaml files with Zuul job metadata")
    parser.add_argument("--job-logs-dir", type=str)
    parser.add_argument("--report-file-pattern", type=str, default=re.compile(r'TESTS-TestSuites.xml'))

    args = parser.parse_args()
    build_id = "deadbeef"
    project = "github.com/Juniper/contrail-test"
    project_commit = "12345"
    execution = 1
    build_info = {
        'build_id': build_id,
        'project': project,
        'project_commit': project_commit,
        'execution': execution
    }
    tests = []
    if args.job_logs_dir:
        file_list = search_for_files(path=args.job_logs_dir, filename_pattern=args.report_file_pattern)
        junit_xml_files = file_list
    else:
        junit_xml_files = args.junit_xml_files
    for f in junit_xml_files:
        doc = read_xml(f)
        if args.read_job_metadata:
            metadata = get_job_metadata(f)
            print(metadata)
            if metadata is None:
                continue
        build_info = {
            'build_id': metadata['build'],
            'project': metadata['project']['canonical_name'],
            'project_commit': project_commit,
            'execution': execution
        }
        records = read_test_info_from_xml(doc, args.quirks)
        for r in records:
            r.update(build_info)
        tests += records
        save_records(records)
    print(pretty_json(tests))
    save_records(tests)


if __name__ == "__main__":
    main()
