#!/bin/bash
set -e
echo "=== DIAG ==="
echo "PYTHONHOME=$PYTHONHOME"
echo "PYTHONPATH=$PYTHONPATH"
echo "PATH=$PATH"
/home/site/wwwroot/antenv/bin/python -c "import sys; print('EXE:', sys.executable); print('PATH:', sys.path)"
/home/site/wwwroot/antenv/bin/python -c "import requests; print('requests OK')" || echo "requests MISSING"
echo "=== END DIAG ==="
unset PYTHONPATH
unset PYTHONHOME
cd /home/site/wwwroot
/home/site/wwwroot/antenv/bin/python -m backend.jobs.nightly_batch --log-level INFO
