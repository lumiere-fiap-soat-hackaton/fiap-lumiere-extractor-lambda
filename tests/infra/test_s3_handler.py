import pytest
import os
import tempfile
from unittest.mock import patch
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError
from moto import mock_aws
import boto3

from src.infra.s3_handler import download_file, upload_file, s3_client


@mock_aws
class TestS3Handler:

    def setup_method(self, method):
        self.test_bucket = "test-bucket"
        self.test_key = "test-key.mp4"
        self.test_file_path = "/tmp/test-file.mp4"

        # Create mock S3 bucket
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket=self.test_bucket)

    def test_given_valid_s3_object_when_downloading_then_succeeds(self):
        # Given: S3 object exists in bucket
        test_content = b"test video content"
        self.s3_client.put_object(
            Bucket=self.test_bucket, Key=self.test_key, Body=test_content
        )

        # When: Downloading the file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            download_file(self.test_bucket, self.test_key, temp_path)

            # Then: File should be downloaded successfully
            assert os.path.exists(temp_path)
            with open(temp_path, "rb") as f:
                assert f.read() == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_nonexistent_key_when_downloading_then_raises_client_error(self):
        # Given: S3 key that doesn't exist
        nonexistent_key = "nonexistent-key.mp4"

        # When: Attempting to download nonexistent file
        # Then: Should raise ClientError with NoSuchKey
        with pytest.raises(ClientError) as exc_info:
            download_file(self.test_bucket, nonexistent_key, self.test_file_path)

        # moto returns "404" instead of "NoSuchKey" for this case
        assert exc_info.value.response["Error"]["Code"] in ["NoSuchKey", "404"]

    def test_given_nonexistent_bucket_when_downloading_then_raises_client_error(self):
        # Given: S3 bucket that doesn't exist
        nonexistent_bucket = "nonexistent-bucket"

        # When: Attempting to download from nonexistent bucket
        # Then: Should raise ClientError with NoSuchBucket
        with pytest.raises(ClientError) as exc_info:
            download_file(nonexistent_bucket, self.test_key, self.test_file_path)

        assert exc_info.value.response["Error"]["Code"] == "NoSuchBucket"

    def test_given_valid_file_when_uploading_then_succeeds(self):
        # Given: A valid file to upload
        test_content = b"test upload content"
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Uploading the file to S3
            upload_file(temp_path, self.test_bucket, self.test_key)

            # Then: File should be uploaded successfully
            response = self.s3_client.get_object(
                Bucket=self.test_bucket, Key=self.test_key
            )
            uploaded_content = response["Body"].read()
            assert uploaded_content == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_nonexistent_bucket_when_uploading_then_raises_client_error(self):
        # Given: A bucket that doesn't exist
        nonexistent_bucket = "nonexistent-bucket"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Attempting to upload to nonexistent bucket
            # Then: Should raise S3UploadFailedError or ClientError
            with pytest.raises((ClientError, S3UploadFailedError)) as exc_info:
                upload_file(temp_path, nonexistent_bucket, self.test_key)

            # moto might raise S3UploadFailedError instead of ClientError
            assert "NoSuchBucket" in str(exc_info.value)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_paths_with_special_characters_when_downloading_then_handles_correctly(
        self,
    ):
        # Given: S3 object with special characters in path
        bucket = "test-bucket"
        key = "path/with spaces/file-name.mp4"
        test_content = b"test special chars content"

        self.s3_client.put_object(Bucket=bucket, Key=key, Body=test_content)

        # When: Downloading file with special characters
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            download_file(bucket, key, temp_path)

            # Then: Should handle special characters correctly
            assert os.path.exists(temp_path)
            with open(temp_path, "rb") as f:
                assert f.read() == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_paths_with_special_characters_when_uploading_then_handles_correctly(
        self,
    ):
        # Given: File with special characters in path
        key = "processed/output file.zip"
        test_content = b"test special chars upload"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Uploading file with special characters
            upload_file(temp_path, self.test_bucket, key)

            # Then: Should handle special characters correctly
            response = self.s3_client.get_object(Bucket=self.test_bucket, Key=key)
            uploaded_content = response["Body"].read()
            assert uploaded_content == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_unicode_paths_when_downloading_then_handles_correctly(self):
        # Given: S3 object with unicode characters in path
        key = "folder/视频文件.mp4"
        test_content = b"test unicode content"

        self.s3_client.put_object(Bucket=self.test_bucket, Key=key, Body=test_content)

        # When: Downloading file with unicode characters
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            download_file(self.test_bucket, key, temp_path)

            # Then: Should handle unicode characters correctly
            assert os.path.exists(temp_path)
            with open(temp_path, "rb") as f:
                assert f.read() == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_unicode_paths_when_uploading_then_handles_correctly(self):
        # Given: File with unicode characters in path
        key = "processed/结果文件.zip"
        test_content = b"test unicode upload"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Uploading file with unicode characters
            upload_file(temp_path, self.test_bucket, key)

            # Then: Should handle unicode characters correctly
            response = self.s3_client.get_object(Bucket=self.test_bucket, Key=key)
            uploaded_content = response["Body"].read()
            assert uploaded_content == test_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_given_s3_client_when_checking_initialization_then_has_required_methods(
        self,
    ):
        # Given: S3 client instance
        # When: Checking client attributes
        # Then: Should have required methods
        assert hasattr(s3_client, "download_file")
        assert hasattr(s3_client, "upload_file")
        assert hasattr(s3_client, "list_objects_v2")

    @patch("src.infra.s3_handler.logger")
    def test_given_successful_download_when_logging_then_logs_info_messages(
        self, mock_logger
    ):
        # Given: Valid S3 object for download
        test_content = b"test logging content"
        self.s3_client.put_object(
            Bucket=self.test_bucket, Key=self.test_key, Body=test_content
        )

        # When: Downloading file with logging enabled
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            download_file(self.test_bucket, self.test_key, temp_path)

            # Then: Should log appropriate messages
            mock_logger.info.assert_any_call(
                f"Downloading s3://{self.test_bucket}/{self.test_key} to {temp_path}"
            )
            mock_logger.info.assert_any_call("Download successful.")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.infra.s3_handler.logger")
    def test_given_successful_upload_when_logging_then_logs_info_messages(
        self, mock_logger
    ):
        # Given: Valid file for upload
        test_content = b"test upload logging"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Uploading file with logging enabled
            upload_file(temp_path, self.test_bucket, self.test_key)

            # Then: Should log appropriate messages
            mock_logger.info.assert_any_call(
                f"Uploading {temp_path} to s3://{self.test_bucket}/{self.test_key}"
            )
            mock_logger.info.assert_any_call("Upload successful.")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.infra.s3_handler.s3_client")
    @patch("src.infra.s3_handler.logger")
    def test_given_upload_failure_when_client_error_occurs_then_logs_error_and_raises(
        self, mock_logger, mock_s3_client
    ):
        # Given: S3 client that raises ClientError
        mock_error = ClientError(
            error_response={
                "Error": {"Code": "AccessDenied", "Message": "Access Denied"}
            },
            operation_name="PutObject",
        )
        mock_s3_client.upload_file.side_effect = mock_error

        test_content = b"test upload error"
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(test_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            # When: Uploading file that causes ClientError
            # Then: Should raise ClientError and log error
            with pytest.raises(ClientError) as exc_info:
                upload_file(temp_path, self.test_bucket, self.test_key)

            assert exc_info.value == mock_error
            mock_logger.error.assert_called_once_with(
                f"Failed to upload file to s3://{self.test_bucket}/{self.test_key}. Error: {mock_error}"
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.infra.s3_handler.s3_client")
    @patch("src.infra.s3_handler.logger")
    def test_given_download_failure_when_client_error_occurs_then_logs_error_and_raises(
        self, mock_logger, mock_s3_client
    ):
        # Given: S3 client that raises ClientError
        mock_error = ClientError(
            error_response={
                "Error": {"Code": "AccessDenied", "Message": "Access Denied"}
            },
            operation_name="GetObject",
        )
        mock_s3_client.download_file.side_effect = mock_error

        # When: Downloading file that causes ClientError
        # Then: Should raise ClientError and log error
        with pytest.raises(ClientError) as exc_info:
            download_file(self.test_bucket, self.test_key, self.test_file_path)

        assert exc_info.value == mock_error
        mock_logger.error.assert_called_once_with(
            f"Failed to download file from s3://{self.test_bucket}/{self.test_key}. Error: {mock_error}"
        )
