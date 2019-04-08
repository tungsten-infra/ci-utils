#!/bin/sh
mydir="$(dirname $0)"
cd "$mydir" || exit 1
python kill_job.py "$SSH_ORIGINAL_COMMAND"
