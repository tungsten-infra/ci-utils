#!/bin/bash
set -x
mydir="$(realpath $(dirname $0))"
. "${mydir}/config.sh"
log_file="${LOG_PATH}"
# 2019-06-07 workaround # for BRANCH in master R5.0 R5.1 R1907; do
# 2019-06-11 turned back R5.1 and R5.0 builds.
# 2019-06-18 swap of R5.0 with R1907
# 2019-07-22 remove R5.1
for BRANCH in master R1907; do
    echo ""
    echo "Running for branch: $BRANCH"
    TAGBRANCH=$(echo $BRANCH | sed -s 's/^R//')
    cd "$mydir"
    cd listen_for_build
    ./install.sh
    . venv-*/bin/activate
    BUILD_NUMBER=$(python listen_for_build.py $BRANCH)
    if [ $? -ne 0 ]; then
      echo "$(date) Error checking build number information. Skipping further run.." | tee -a "$log_file"
      continue
    fi
    echo "$(date) Found build number: $BUILD_NUMBER for $BRANCH." | tee -a "$log_file"
    deactivate
    cd "$mydir"
    cd verify_docker_registry
    ./install.sh
    . venv-*/bin/activate
    TAG=${TAGBRANCH}-${BUILD_NUMBER}
    python verify_docker_registry.py --registry "${VERIFICATION_REGISTRY_URL}" --repository "${VERIFICATION_REPOSITORY_NAME}" --tag $TAG is_tag_present
    result=$?
    cd "$mydir"
    if [ "$result" -ne 0 ]; then
       echo "$(date) Found build number for ${BRANCH}: ${BUILD_NUMBER}, missing in the registry" | tee -a "$log_file"
       searchStr="Started ${BRANCH}: ${BUILD_NUMBER}."
       count=$(grep -F "$searchStr" "$log_file" | wc -l)
       if [ "$count" -le 240 ]; then
         zuul -c zuul.conf enqueue-ref --tenant "${TRIGGER_TENANT}" --trigger timer --pipeline "${TRIGGER_PIPELINE}" --project "${TRIGGER_PROJECT}" --ref refs/heads/$BRANCH --newrev "${TRIGGER_NEWREV}"
         echo "$searchStr The zuul enqueue-ref returned $?" | tee -a "$log_file"
       else
         echo "$(date) Ignoring build ${BRANCH}: ${BUILD_NUMBER}, too many attempts" | tee -a "$log_file"
       fi
    fi
done
