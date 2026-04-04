#!/bin/bash
# Azure WebJob entry point — runs the nightly batch pipeline.
#
# Azure App Service (Linux) convention:
#   - Place this file alongside settings.job in the WebJob folder.
#   - The virtual environment is named "antenv" by Azure's Oryx build system.
#   - stdout/stderr are captured by Azure and visible in the WebJob log stream.
#
# Deploy path (relative to site root):
#   App_Data/jobs/triggered/nightly-batch/run.sh
#   App_Data/jobs/triggered/nightly-batch/settings.job

set -e

SITE_ROOT="/home/site/wwwroot"
cd "$SITE_ROOT"

# Activate the virtual environment created by Azure Oryx
if [ -f "antenv/bin/activate" ]; then
    source antenv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "WARNING: No virtual environment found — using system Python"
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting Athens RE nightly batch..."
python -m backend.jobs.nightly_batch --log-level INFO
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Nightly batch finished."
