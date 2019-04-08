from __future__ import print_function
from lxml import etree
import json
import os
import database
import argparse
import gzip
import shutil
import tempfile
import re


def read_xml_gz(path):
    tmpfile = tempfile.TemporaryFile()
    with gzip.open(path, 'rb') as f_in:
        shutil.copyfileobj(f_in, tmpfile)

    tmpfile.seek(0)
    return read_xml(tmpfile)


def read_xml(filename):
    doc = etree.parse(filename)
    return doc


class SafeObjectEncoder(json.JSONEncoder):
    def default(self, obj): return str(obj)


def pretty_json(obj):
    return json.dumps(obj, cls=SafeObjectEncoder, indent=4)


def read_test_info_from_xml(doc):
    testsuites = []
    records = []
    if doc.getroot().tag == "testsuites":
        testsuites += doc.findall("testsuite")
    elif doc.getroot().tag == "testsuite":
        testsuites.append(doc.getroot())

    for testsuite in testsuites:
        suitename = testsuite.get("name")
        for testcase in testsuite.findall("testcase"):
            testcase_duration_s = testcase.get("time")
            testcase_duration = int(float(testcase_duration_s) * 1000)
            caseclass = testcase.get("classname")
            casename = testcase.get("name")
            if testcase.find("failure") is not None:
                result = "FAILED"
            elif testcase.find("skipped") is not None:
                result = "SKIPPED"
            else:
                result = "SUCCESS"

            # test cases may be generated, suffixed with consecutive natural numbers
            # e.g.
            # GracefulRestart_Flap_Some_2_3/0
            # GracefulRestart_Flap_Some_2_3/1
            # GracefulRestart_Flap_Some_2_3/2
            # GracefulRestart_Flap_Some_2_3/3
            # Handle them as a single test case as there can be thousands of variations
            # further aggregation happens in aggregate_test_records
            casename = casename.split('/')[0]
            record = {
                "suitename": suitename,
                "caseclass": caseclass,
                "casename": casename,
                "duration": testcase_duration,
                "result": result,
            }
            records.append(record)
    return records


# same suitename/caseclass/casenames records can be in multiple XML report files
# aggregate them to one single record
def aggregate_test_records(records, records_to_aggregate):
    for rta in records_to_aggregate:
        matching_records = [record for record in records if record['casename'] == rta['casename'] and
                                                            record['suitename'] == rta['suitename'] and
                                                            record['caseclass'] == rta['caseclass']]
        if matching_records:
            r = matching_records[0]
            r['duration'] += rta['duration']
            if rta['result'] == "FAILED":
                r['result'] = rta['result']
        else:
            records.append(rta)
    return records


def save_records(records):
    batch_size = 100
    with database.db.atomic():
        for idx in range(0, len(records), batch_size):
            database.TestStats.insert_many(records[idx:idx+batch_size]).execute()


"""
the file names in unittest_target.json paths are not the actual file names
the testrunner renames the file with each test target retry
so e.g.
/home/zuul/unittest_output/xmls/build/debug/config/api-server/test-results.xml
becomes
/home/zuul/unittest_output/xmls/build/debug/config/api-server/test-results.bzfaorps.xml
"""
def find_xmls(reports_root_dir, file_path):
    dir, file_name = os.path.split(file_path)
    dir = '{}/{}'.format(reports_root_dir, dir)
    filename_prefix = file_name.split('.')[0]

    archived_xml_paths = []
    filename_pattern = re.compile(r'^{}\..*\.xml.gz$'.format(filename_prefix))

    for root, dirs, files in os.walk(dir, topdown=False):
        for f in files:
            if filename_pattern.match(f):
                archived_xml_paths.append(os.path.join(root,f))

    return archived_xml_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("unittest_targets_file", type=str)
    parser.add_argument("--xml_reports_root_dir", type=str, default=os.getcwd())
    parser.add_argument("--change", type=int, default=-1)
    parser.add_argument("--patchset", type=int,default=-1)

    args = parser.parse_args()

    records = []

    with open(args.unittest_targets_file) as f:
        unittest_targets = json.load(f)

        for unittest_target in [x for x in unittest_targets if "xml_path" in x]:
            archived_xml_paths = find_xmls(args.xml_reports_root_dir,
                                           unittest_target["xml_path"])

            for archived_xml in archived_xml_paths:
                test_results_xml = read_xml_gz(archived_xml)
                test_records = read_test_info_from_xml(test_results_xml)
                records = aggregate_test_records(records, test_records)

    for record in records:
        if args.change: record["change"] = args.change
        if args.patchset: record["patchset"] = args.patchset

    save_records(records)


if __name__ == "__main__":
    main()
