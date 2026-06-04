#!/bin/bash
set -e

cd /home/site/wwwroot
unset PYTHONPATH
unset PYTHONHOME

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting Athens RE nightly batch..."
/home/site/wwwroot/antenv/bin/python -m backend.jobs.nightly_batch --log-level INFO
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly batch finished."
