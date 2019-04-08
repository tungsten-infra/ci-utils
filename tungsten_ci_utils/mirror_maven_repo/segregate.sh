#!/bin/bash

# Maven artifacts can be composed of different file groups
# There can be .pom files, .jar files, .jar's with dependencies, .jar files containing sources or javadocs
# A maven artifact can be any subset of these
# This script splits a given directory of maven artifacts into four directories:
# poms - a directory containing only .pom files
# jars - a directory containing only .pom and .jar files and eventually a .jar with dependencies
# sources - a directory containing only a .pom, .jar and a .jar with sources
# javadocs - a directory containing only a .pom, .jar and a .jar with javadocs
# all - a directory containing a .pom, .jar, a .jar with sources and a .jar with javadocs

usage() {
  echo "Usage: $0 -d <directory> -v <version>"
  exit 1
}

while getopts "d:v:" opt; do
  case "${opt}" in
    d)
      directory="${OPTARG}"
      ;;
    v)
      VERSION="${OPTARG}"
      ;;
    *)
      usage
      ;;
  esac
done

if [ "x" == "x${directory}" ] || [ "x" == "x${VERSION}" ]; then
  usage
fi

# NOTE: Maven artifacts have a naming scheme of '<artifactId>-<version>-<classifier>.<extension>
# ${file%%-{VERSION}*} removes everything after and including '-${VERSION}' in the 'file' variable.

for file in `ls -A1 ${directory}`; do echo ${file%%-${VERSION}*} >> prefixes; done
cat prefixes | uniq > artifact_ids
rm prefixes

mkdir poms jars sources javadocs all > /dev/null

artifact_ids=$(cat artifact_ids)

for artifact_id in ${artifact_ids}; do
  if [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}" | wc -l` -eq 4 ]; then
    mv "${directory}/$artifact_id-${VERSION}"* all/
  elif [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}-jar-with-dependencies"` ]; then
    mv "${directory}/$artifact_id-${VERSION}"* jars/
  elif [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}-sources"` ]; then
    mv "${directory}/$artifact_id-${VERSION}"* sources/
  elif [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}-javadoc"` ]; then
    mv "${directory}/$artifact_id-${VERSION}"* javadocs/
  elif [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}" | wc -l` -eq 2 ]; then
    mv "${directory}/$artifact_id-${VERSION}"* jars/
  elif [ `ls -A1 ${directory} | grep "^$artifact_id-${VERSION}" | wc -l` -eq 1 ]; then
    mv "${directory}/$artifact_id-${VERSION}"* poms/
  fi
done
