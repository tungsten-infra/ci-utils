#!/bin/bash

# prepares a list of image tags to remove from a registry
# leaves TAGS_TO_LEAVE number of most recent tags

DIR=$(dirname $0)

REGISTRY="localhost:5000"

OPENSTACK_VERSIONS="
newton
ocata
queens
rocky
"

TAG_SUFFIX_LIST_TO_PRESERVE="
master
latest
"

while getopts ":r::" opt; do
  case $opt in
    r)
      REGISTRY=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

timestamp=$(date '+%Y-%m-%d-%H-%M-%S')
tag_file="/tmp/tags-public-$timestamp"

# get all tags from the registry
. venv/bin/activate
python docker_tagtool.py --registry ${REGISTRY} list_tags > ${tag_file}

# remove standalone openstack version tags
for openstack_version in ${OPENSTACK_VERSIONS}; do
  sed -i "/^${openstack_version}$/d" ${tag_file}
done

# remove entries from tag list to preserve
for tag in ${TAG_SUFFIX_LIST_TO_PRESERVE}; do
  sed -i "/.*${tag}$/d" ${tag_file}
done

TAGS_TO_LEAVE=4
OUTPUT_TAGS_FILE="${DIR}/public_tags_list_to_delete"

rm "${OUTPUT_TAGS_FILE}"

# leave only last N tags for given set {rhel-}{openstack_version}-{release}
for release in 5.0 master; do
  cat ${tag_file} | egrep "^${release}" | head -n -$((TAGS_TO_LEAVE+1)) >> "${OUTPUT_TAGS_FILE}"
  cat ${tag_file} | egrep "^rhel-${release}" | head -n -$((TAGS_TO_LEAVE+1)) >> "${OUTPUT_TAGS_FILE}"
  for openstack_version in ${OPENSTACK_VERSIONS}; do
    cat ${tag_file} | egrep "^rhel-${openstack_version}-${release}" | head -n -$((TAGS_TO_LEAVE+1)) >> "${OUTPUT_TAGS_FILE}"
    cat ${tag_file} | egrep "^${openstack_version}-${release}" | head -n -$((TAGS_TO_LEAVE+1)) >> "${OUTPUT_TAGS_FILE}"
  done
done

rm ${tag_file1}
