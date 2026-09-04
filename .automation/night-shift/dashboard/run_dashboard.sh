#!/bin/bash
# NAE Live Dashboard — launchd entry point.
#
# Starts the read-only Monitor API (FastAPI) which also serves the built
# Vue app as static files, both on 127.0.0.1:8799. This script does not
# loop or retry itself — it execs uvicorn directly so launchd's own
# KeepAlive owns restart-on-exit (see com.dbma.nae.dashboard.plist).
#
# Read-only: this process never writes to NAE/corpus/tsu/, NAE/pipeline/,
# or sends any command to the TSU runner, Ollama, or Qdrant. It only reads
# tsu_report.json / queue logs / ps aux / Ollama's health endpoint.
set -uo pipefail
cd "$(dirname "$0")/backend" || exit 1
source ~/envs/dbma311/bin/activate
exec uvicorn app:app --host 127.0.0.1 --port 8799
