"""Mark one E2E fixture expired in the isolated E2E database."""

import argparse
import uuid
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.upload import Upload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upload_id", type=uuid.UUID)
    args = parser.parse_args()
    if "dropvault_e2e" not in settings.DATABASE_URL:
        parser.error("This helper only runs against the isolated E2E database")
    with SessionLocal() as db:
        upload = db.get(Upload, args.upload_id)
        if upload is None:
            parser.error("Upload not found")
        upload.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()


if __name__ == "__main__":
    main()
