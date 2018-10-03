#!/bin/bash

VERSION='7.3.0'
# NOTE: Maven artifacts have a naming scheme of '<artifactId>-<version>-<classifier>.<extension>
# ${file%%-{VERSION}*} removes everything after and including '-${VERSION}' in the 'file' variable.

for file in `ls -A1 artifacts`; do echo ${file%%-${VERSION}*} >> prefixes; done
cat prefixes | uniq > artifact_ids
rm prefixes

mkdir 1 2 3 4 2> /dev/null

artifact_ids=$(cat artifact_ids)

for artifact_id in ${artifact_ids}; do
  if [ `ls -A1 artifacts | grep "^$artifact_id-${VERSION}" | wc -l` -eq 4 ]; then
    mv "artifacts/$artifact_id-${VERSION}"* 4/
  fi
  if [ `ls -A1 artifacts | grep "^$artifact_id-${VERSION}" | wc -l` -eq 3 ]; then
    mv "artifacts/$artifact_id-${VERSION}"* 3/
  fi
  if [ `ls -A1 artifacts | grep "^$artifact_id-${VERSION}" | wc -l` -eq 2 ]; then
    mv "artifacts/$artifact_id-${VERSION}"* 2/
  fi
  if [ `ls -A1 artifacts | grep "^$artifact_id-${VERSION}" | wc -l` -eq 1 ]; then
    mv "artifacts/$artifact_id-${VERSION}"* 1/
  fi
done
