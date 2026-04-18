"""Run isolated backend pytest with HTML coverage and JUnit XML; optionally lint frontend."""

import argparse
import subprocess
import sys
from _common import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend", action="store_true", help="Also run frontend lint"
    )
    args = parser.parse_args()
    command = [
        "docker",
        "compose",
        "-p",
        "dropvault-tests",
        "-f",
        "docker-compose.test.yml",
    ]
    try:
        result = subprocess.run(
            command + ["run", "--build", "--rm", "tests"], cwd=ROOT, check=False
        )
    except OSError as error:
        print(f"FAIL: could not run Docker Compose: {error}", file=sys.stderr)
        return 1
    finally:
        try:
            subprocess.run(
                command + ["down", "-v", "--remove-orphans"],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass
    if result.returncode:
        return result.returncode
    print("Coverage: backend/test-results/htmlcov/index.html")
    print("JUnit XML: backend/test-results/junit.xml")
    if args.frontend:
        try:
            return subprocess.run(
                ["npm", "run", "lint"], cwd=ROOT / "frontend", check=False
            ).returncode
        except OSError as error:
            print(f"FAIL: frontend lint: {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
