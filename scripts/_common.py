"""Shared portable helpers for local Compose scripts."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compose(*args, capture=False):
    command = ["docker", "compose", *args]
    try:
        return subprocess.run(
            command, cwd=ROOT, check=False, text=True, capture_output=capture
        )
    except OSError as error:
        print(f"FAIL: could not run Docker Compose: {error}", file=sys.stderr)
        return None


def finish(result):
    if result is None:
        return 1
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode or 1
    return 0
