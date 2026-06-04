#!/bin/bash
set -e

cd /home/site/wwwroot
unset PYTHONPATH
unset PYTHONHOME

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting Athens RE nightly batch..."
echo "nightly_batch.py md5: $(md5sum /home/site/wwwroot/backend/jobs/nightly_batch.py 2>/dev/null || echo 'file not found')"
/home/site/wwwroot/antenv/bin/python -m backend.jobs.nightly_batch --log-level INFO
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly batch finished."
