#!/bin/bash
python3.5 -m venv venv-listen-for-build && \
. venv-listen-for-build/bin/activate && \
pip install --upgrade --no-cache-dir pip && \
pip install -r requirements.txt
