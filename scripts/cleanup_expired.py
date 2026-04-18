"""Run the cleanup job synchronously inside the backend container."""

import argparse
import sys
from _common import compose, finish


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = compose(
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        "from app.workers.tasks import cleanup_expired_uploads; print(cleanup_expired_uploads())",
    )
    return finish(result)


if __name__ == "__main__":
    sys.exit(main())
