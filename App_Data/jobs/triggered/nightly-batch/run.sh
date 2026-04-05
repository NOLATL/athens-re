#!/bin/bash
set -e
cd /home/site/wwwroot
/home/site/wwwroot/antenv/bin/python -m backend.jobs.nightly_batch --log-level INFO
