"""
Pytest configuration file for shared fixtures across all test modules.
"""

import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws


@pytest.fixture
def aws_sqs_client():
    """
    AWS SQS client fixture that mocks AWS services and provides a test SQS queue.

    This fixture provides a fully mocked SQS environment for testing purposes.
    It creates a mock SQS client, test queue, and patches the SQS client in the handler module.

    Returns:
        dict: Dictionary containing mocked SQS client, queue URL, and test data
            - sqs_client: Mocked boto3 SQS client
            - queue_url: URL of the test queue
            - test_queue_name: Name of the test queue
            - test_request_id: Sample request ID for testing
            - test_result_s3_path: Sample S3 path for testing
            - test_status: Sample status for testing
    """
    with mock_aws():
        # Create mock SQS client
        mock_sqs_client = boto3.client("sqs", region_name="us-east-1")

        # Create test queue
        test_queue_name = "test-queue"
        queue_response = mock_sqs_client.create_queue(QueueName=test_queue_name)
        queue_url = queue_response["QueueUrl"]

        # Test data
        test_data = {
            "sqs_client": mock_sqs_client,
            "queue_url": queue_url,
            "test_queue_name": test_queue_name,
            "test_request_id": "test-request-123",
            "test_result_s3_path": "s3://test-bucket/processed/result.zip",
            "test_status": "SUCCESS",
        }

        # Patch the sqs_client in the handler module
        with patch("src.infra.sqs_handler.sqs_client", mock_sqs_client):
            yield test_data


@pytest.fixture
def aws_s3_client():
    """
    AWS S3 client fixture that mocks AWS services and provides a test S3 bucket.

    Returns:
        dict: Dictionary containing mocked S3 client, bucket name, and test data
    """
    with mock_aws():
        # Create mock S3 client
        mock_s3_client = boto3.client("s3", region_name="us-east-1")

        # Create test bucket
        test_bucket = "test-bucket"
        mock_s3_client.create_bucket(Bucket=test_bucket)

        # Test data
        test_data = {
            "s3_client": mock_s3_client,
            "test_bucket": test_bucket,
            "test_key": "test-key.mp4",
            "test_file_path": "/tmp/test-file.mp4",
        }

        # Patch the s3_client in the handler module
        with patch("src.infra.s3_handler.s3_client", mock_s3_client):
            yield test_data
