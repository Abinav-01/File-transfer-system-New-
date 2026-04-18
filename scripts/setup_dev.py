"""Validate local configuration; optionally start services and apply migrations."""

import argparse
import sys
from _common import ROOT, compose, finish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start Compose services and apply database migrations",
    )
    args = parser.parse_args()
    required = [ROOT / "docker-compose.yml", ROOT / "backend" / "alembic.ini"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("FAIL: missing files: " + ", ".join(missing), file=sys.stderr)
        return 1
    result = compose("config", "--quiet", capture=True)
    if finish(result):
        return 1
    print("PASS: Compose configuration is valid")
    if args.start:
        if finish(compose("up", "-d", "--build")):
            return 1
        if finish(compose("exec", "-T", "backend", "alembic", "upgrade", "head")):
            return 1
        print("PASS: services started and migrations applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
