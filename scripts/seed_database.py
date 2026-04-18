"""Create sample uploads through the public API and print their tokens."""

import argparse
import json
import sys
import uuid
from urllib.request import Request, urlopen


def create(base, filename, data, password=None, max_downloads=None):
    boundary = uuid.uuid4().hex
    fields = {"expires_in": "60"}
    if password:
        fields["password"] = password
    if max_downloads:
        fields["max_downloads"] = str(max_downloads)
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        for key, value in fields.items()
    )
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'.encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    request = Request(
        base.rstrip("/") + "/api/uploads",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="Backend base URL"
    )
    parser.add_argument(
        "--password", default="sample-password", help="Password for protected sample"
    )
    args = parser.parse_args()
    try:
        samples = [
            create(args.url, "welcome.txt", b"Welcome to DropVault\n"),
            create(args.url, "limited.txt", b"One download only\n", max_downloads=1),
            create(
                args.url,
                "protected.txt",
                b"Protected example\n",
                password=args.password,
            ),
        ]
    except Exception as error:
        print(f"FAIL: sample creation: {error}", file=sys.stderr)
        return 1
    for sample in samples:
        print(
            json.dumps(
                {
                    "id": sample["id"],
                    "filename": sample["original_filename"],
                    "share_token": sample["share_token"],
                    "management_token": sample["management_token"],
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
