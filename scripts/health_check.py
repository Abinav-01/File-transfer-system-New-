"""Check the backend and its PostgreSQL, Redis, and MinIO dependencies."""

import argparse
import json
import sys
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000/health", help="Backend health URL"
    )
    args = parser.parse_args()
    try:
        with urlopen(args.url, timeout=5) as response:
            data = json.load(response)
    except Exception as error:
        print(f"FAIL: backend: {error}", file=sys.stderr)
        return 1
    print("PASS: backend")
    failed = False
    for name in ("postgres", "redis", "minio"):
        healthy = data.get(name) == "up"
        print(f"{'PASS' if healthy else 'FAIL'}: {name}")
        failed |= not healthy
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
