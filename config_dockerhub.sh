#!/bin/bash
export PYTHON_INTERPRETER="python3"
export LOG_PATH="/tmp/dockerhub_trigger.log"
export VERIFICATION_REGISTRY_URL="index.docker.io"
export VERIFICATION_REPOSITORY_NAME="opencontrailnightly/contrail-general-base"
export TRIGGER_NEWREV="0000000000000000000000000000000000000000"
export TRIGGER_PROJECT="tungstenfabric-infra/periodic-nightly"
export TRIGGER_TENANT="opencontrail"
export TRIGGER_PIPELINE="manual"
