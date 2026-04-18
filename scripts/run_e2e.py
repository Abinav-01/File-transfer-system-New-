"""Start isolated DropVault services and run the five Playwright browser journeys."""

import argparse
import os
import subprocess
import sys
import time
from urllib.request import urlopen
from _common import ROOT

COMPOSE = ["docker", "compose", "-p", "dropvault-e2e", "-f", "docker-compose.e2e.yml"]
BASE_URL = "http://127.0.0.1:3100"


def run(*arguments):
    return subprocess.run([*COMPOSE, *arguments], cwd=ROOT, check=False).returncode


def wait_for_backend(timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(BASE_URL + "/backend/health", timeout=3) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headed", action="store_true", help="Show Chromium during the tests"
    )
    args = parser.parse_args()
    try:
        if run("up", "-d", "--build", "frontend-e2e"):
            return 1
        if run("exec", "-T", "backend-e2e", "alembic", "upgrade", "head"):
            return 1
        if not wait_for_backend():
            print("FAIL: E2E frontend/backend did not become ready", file=sys.stderr)
            return 1
        environment = dict(os.environ, PLAYWRIGHT_BASE_URL=BASE_URL)
        command = ["npm", "run", "test:e2e"]
        if args.headed:
            command += ["--", "--headed"]
        result = subprocess.run(
            command, cwd=ROOT / "frontend", env=environment, check=False
        )
        return result.returncode
    except KeyboardInterrupt:
        print("E2E run interrupted", file=sys.stderr)
        return 130
    except OSError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    finally:
        try:
            run("down", "-v", "--remove-orphans")
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
