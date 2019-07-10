set -x
mydir="$(realpath $(dirname $0))"
source "${mydir}/config.sh"
log_file="${LOG_PATH}"
for BRANCH in master R5.0; do
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
    cd $mydir
    if [ "$result" -ne 0 ]; then
       echo "$(date) Found build number for ${BRANCH}: ${BUILD_NUMBER}, missing in the registry. Starting build." | tee -a "$log_file"
       searchStr="${BRANCH}: ${BUILD_NUMBER}, missing in the registry. Starting build"
       echo $searchStr
       count=`grep -i "$searchStr" /tmp/zuul_build_trigger.log | wc -l`
       if [ "$count" -le 3 ]; then
         zuul -c zuul.conf enqueue-ref --tenant "${TRIGGER_TENANT}" --trigger timer --pipeline "${TRIGGER_PIPELINE}" --project "${TRIGGER_PROJECT}" --ref refs/heads/$BRANCH --newrev "${TRIGGER_NEWREV}"
         #echo "execution check point"
       # sleep 180
       fi
    fi
done
