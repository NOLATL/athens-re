#!/bin/bash
set -e
cd /home/site/wwwroot
source antenv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || true
python -m backend.jobs.nightly_batch --log-level INFO
