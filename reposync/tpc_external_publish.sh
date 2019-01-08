#!/bin/bash
set -e

for branch in master R5.0; do
    for component in binary source; do
        REPO=tungstenfabric-tpc-$branch-$component DL_PATH=./comb-$branch ./reposync.sh
    done
    rsync -vre "ssh -i ./id_rsa" ./comb-$branch/*.rpm tpc-sync@148.251.5.90:/var/www/html/tpc-sync-$branch
    ssh -i ./id_rsa tpc-sync@148.251.5.90 "cd /var/www/html/tpc-sync-$branch && createrepo -v ."
    ssh -i ./id_rsa tpc-sync@148.251.5.90 "cd /var/www/html/ && rsync -rv --delete tpc-sync-$branch/ tpc-$branch"
done    
# move to target dir only for master branch
ssh -i ./id_rsa tpc-sync@148.251.5.90 "cd /var/www/html/ && rsync -rv --delete tpc-sync-master/ tpc"
