#!/bin/bash

NEXUS=http://localhost:8081

set -o pipefail
set -o errexit
set -o nounset

if [[ ${PASS+defined} != defined || ${1+defined} != defined || ${2+defined} == defined ]]; then
    echo 'Execute the Groovy code for Sonatype Nexus3 (one-time run via their REST API)'
    echo 'Useful when developing code intended for the periodic Tasks'
    echo ''
    echo 'Usage:'
    echo '      sudo apt install jq'
    echo '      read -s PASS && export PASS   # password for user "admin"'
    echo "      $0  myscript.groovy"
    echo ''
    echo '      unset PASS'
    echo ''
    exit 1
fi

#readonly script=$( sed 's/	/  /g;s/\(\\\|"\)/\\\1/g;s/$/\\n/g' "$1"  | tr -d '\012\015' )  # poor man's jq

readonly script_json=$( echo '{ "name":"kubit", "type":"groovy" }' | jq --arg c "$(cat "$1")" '.content=$c' )

#echo ''
#echo '---------- script  -----------'
#echo "$script_json"

#if ! curl -f -u "admin:$PASS" "$NEXUS"/service/rest/v1/script/kubit   2>&1 ; then

#echo ''
#echo '---------- PUT -------------'
#if ! curl -f -u "admin:$PASS" -X PUT -H 'Content-Type: application/json'  "$NEXUS"/service/rest/v1/script/kubit -d "$script_json" ; then

echo ''
echo '--------- POST -----------'
if ! curl -f -u "admin:$PASS" -H 'Content-Type: application/json'  "$NEXUS"/service/rest/v1/script -d "$script_json" ; then
    echo "We cannot POST that script, did you left over an existing script with the same name?"
    echo ""
    echo 'curl -u "admin:$PASS" -X DELETE  '"$NEXUS"'/service/rest/v1/script/kubit'
    exit 1
fi

#echo ''
#echo '---------- GET -------------'
# curl -v -u "admin:$PASS" "$NEXUS"/service/rest/v1/script/kubit

echo ''
echo '---------- run -------------'
curl -u "admin:$PASS" -X POST  --header 'Content-Type: text/plain'  "$NEXUS"/service/rest/v1/script/kubit/run

echo ''
echo '---------- DEL -------------'
curl -u "admin:$PASS" -X DELETE  "$NEXUS"/service/rest/v1/script/kubit

echo ''
echo '--------- success ----------'
