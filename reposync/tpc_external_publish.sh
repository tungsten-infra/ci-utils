#!/bin/bash
set -e
. ./env.sh

for branch in master R5.0 R5.1; do
    for component in binary source; do
        REPO=tungstenfabric-tpc-$branch-$component DL_PATH=./comb-$branch ./reposync.sh
    done
    rsync -vre "ssh -i ${SSH_KEY_PATH}" ./comb-$branch/*.rpm ${PUBLIC_REPO_USER}@${PUBLIC_REPO_ADDR}:/var/www/html/tpc-sync-$branch
    ssh -i ${SSH_KEY_PATH} ${PUBLIC_REPO_USER}@${PUBLIC_REPO_ADDR} "cd /var/www/html/tpc-sync-$branch && createrepo -v ."
    ssh -i ${SSH_KEY_PATH} ${PUBLIC_REPO_USER}@${PUBLIC_REPO_ADDR} "cd /var/www/html/ && rsync -rv --delete tpc-sync-$branch/ tpc-$branch"
done
# move to target dir only for master branch
ssh -i ${SSH_KEY_PATH} ${PUBLIC_REPO_USER}@${PUBLIC_REPO_ADDR} "cd /var/www/html/ && rsync -rv --delete tpc-sync-master/ tpc"
