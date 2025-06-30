# s3_handler.py

import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
s3_client = boto3.client("s3")


def download_file(bucket: str, key: str, download_path: str) -> None:
    """Downloads a file from an S3 bucket."""
    try:
        logger.info(f"Downloading s3://{bucket}/{key} to {download_path}")
        s3_client.download_file(bucket, key, download_path)
        logger.info("Download successful.")
    except ClientError as e:
        logger.error(f"Failed to download file from s3://{bucket}/{key}. Error: {e}")
        raise


def upload_file(file_path: str, bucket: str, key: str) -> None:
    """Uploads a file to an S3 bucket."""
    try:
        logger.info(f"Uploading {file_path} to s3://{bucket}/{key}")
        s3_client.upload_file(file_path, bucket, key)
        logger.info("Upload successful.")
    except ClientError as e:
        logger.error(f"Failed to upload file to s3://{bucket}/{key}. Error: {e}")
        raise
