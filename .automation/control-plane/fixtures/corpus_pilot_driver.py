#!/usr/bin/env python3
"""Corpus Factory pilot CLI driver -- isolated, synthetic, mirrors ADR-023's
cli_driver.py *pattern* only (a thin CLI boundary the executor subprocess-
invokes) without touching any real NAE/registration code.

Governance boundary
--------------------
Zero imports from NAE.* or core.*. This script's only job is to prove the
CLI-driver-boundary pattern (executor never inlines corpus_pilot_echo logic,
always shells out) -- it does one fixed, safe thing and nothing else.

Usage
-----
    python3 corpus_pilot_driver.py --task-id <id>
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print(f"CORPUS_PILOT_DRIVER_OK task_id={args.task_id} ts={ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
