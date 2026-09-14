"""infra/logger.py — debug for replays (docs/AGENTS.md:244)"""
import sys
def log(msg):
    print(msg, file=sys.stderr)
