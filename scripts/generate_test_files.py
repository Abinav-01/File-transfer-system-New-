"""Generate small deterministic samples for manual upload testing."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("test-files"), help="Output directory"
    )
    parser.add_argument(
        "--max-size-mb", type=int, default=5, help="Largest binary sample in MiB"
    )
    args = parser.parse_args()
    if args.max_size_mb < 1 or args.max_size_mb > 1024:
        parser.error("--max-size-mb must be between 1 and 1024")
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "sample.txt").write_text(
            "DropVault sample text\n", encoding="utf-8"
        )
        (args.output / "sample.json").write_text(
            '{"project":"DropVault","sample":true}\n', encoding="utf-8"
        )
        (args.output / "empty.txt").touch()
        with (args.output / f"sample-{args.max_size_mb}mb.bin").open("wb") as target:
            block = bytes(range(256)) * 4096
            for _ in range(args.max_size_mb):
                target.write(block)
    except OSError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: generated text, JSON, empty, and binary files in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
