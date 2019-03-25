#!/bin/bash
if [ x"$(lsb_release -is)" == x"Ubuntu" ]; then
    echo "Ubuntu"
    apt install -y python3-venv
fi
name=verify-docker-registry
python3.5 -m venv venv-$name && \
. venv-$name/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt
