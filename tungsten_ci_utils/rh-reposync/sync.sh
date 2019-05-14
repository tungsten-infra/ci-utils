#!/bin/bash

REPOSYNC="reposync --delete --newest-only"
REPOSYNC_BASE="reposync --delete"
SUBMAN="subscription-manager repos"
REPODIR=/var/www/html

BASE_REPOS="rhel-7-server-beta-rpms
rhel-7-server-rpms
"

REPOS="rhel-7-server-ansible-2.4-rpms
rhel-7-server-ansible-2.5-rpms
rhel-7-server-ansible-2.6-rpms
rhel-7-server-extras-rpms
rhel-7-server-openstack-11-devtools-rpms
rhel-7-server-openstack-11-rpms
rhel-7-server-openstack-11-tools-rpms
rhel-7-server-openstack-13-devtools-rpms
rhel-7-server-openstack-13-rpms
rhel-7-server-openstack-13-tools-rpms
rhel-7-server-openstack-beta-rpms
rhel-7-server-openstack-devtools-beta-rpms
rhel-7-server-openstack-optools-beta-rpms
rhel-7-server-optional-beta-rpms
rhel-7-server-optional-rpms
rhel-7-server-ose-3.9-rpms
rhel-7-server-ose-3.11-rpms
rhel-7-fast-datapath-rpms
rhel-server-rhscl-7-rpms
rhel-server-rhscl-7-beta-rpms"

for repoid in $BASE_REPOS; do
  mkdir -p ${REPODIR}/${repoid}
  REPOSYNC_BASE="${REPOSYNC_BASE} --repoid=${repoid}"
  SUBMAN="${SUBMAN} --enable=${repoid}"
done

for repoid in $REPOS; do
  mkdir -p ${REPODIR}/${repoid}
  REPOSYNC="${REPOSYNC} --newest-only --repoid=${repoid}"
  SUBMAN="${SUBMAN} --enable=${repoid}"
done

echo "`date --utc` UTC ---------- Starting reposync ----------"
${SUBMAN}
cd ${REPODIR}
echo "Syncing newest only from: ${REPOS}"
${REPOSYNC}
echo "Syncing all from: ${BASE_REPOS}"
${REPOSYNC_BASE}

for repoid in $BASE_REPOS; do
  echo `date` Updating repo ${repoid}
  createrepo --update ${repoid}
done

for repoid in $REPOS; do
  echo `date` Updating repo ${repoid}
  createrepo --update ${repoid}
done

echo "`date --utc` UTC ---------- Finished reposync ----------"
echo
echo
