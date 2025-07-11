import logging
import os
import zipfile
from typing import Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def format_s3_path(bucket: str, base_path: str, request_id: str, key: str) -> str:
    """Formats a bucket and key into a valid S3 path."""
    if not bucket or not key:
        raise ValueError("Both bucket and key must be provided.")
    current_date = datetime.now().strftime("%Y-%m-%d")
    object_key = f"{base_path}/{current_date}/{request_id}/{key}"
    return object_key, f"s3://{bucket}/{object_key}"


def parse_s3_path(s3_path: str) -> Tuple[str, str]:
    """Parses an S3 path string into bucket and key components."""
    if not s3_path.startswith("s3://"):
        raise ValueError(f"Invalid S3 path format: {s3_path}")

    parts = s3_path[5:].split("/", 1)
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid S3 path format (missing bucket or key): {s3_path}")

    bucket = parts[0]
    key = parts[1]
    return bucket, key


def create_zip_archive(directory: str, zip_path: str) -> None:
    """Creates a ZIP archive from the contents of a directory."""
    logger.info(f"Creating ZIP archive for directory {directory} at {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory)
                zipf.write(file_path, arcname)
    logger.info(f"ZIP archive created successfully: {zip_path}")
