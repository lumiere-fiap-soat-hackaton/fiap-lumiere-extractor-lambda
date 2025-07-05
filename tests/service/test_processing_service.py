import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from src.services.processing_service import VideoProcessingService


class TestVideoProcessingService:

    def setup_method(self):
        self.output_bucket_name = "test-output-bucket"
        self.service = VideoProcessingService(self.output_bucket_name)
        self.request_id = "test-request-123"
        self.s3_path = "s3://test-bucket/videos/sample.mp4"
        self.notification_queue_url = (
            "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        )

    def test_given_output_bucket_when_initializing_service_then_sets_attributes(self):
        # Given: An output bucket name
        # When: Initializing VideoProcessingService
        # Then: Should set the correct attributes
        assert self.service.output_bucket_name == self.output_bucket_name
        assert self.service.processed_base_path == "processed"

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_valid_video_when_processing_then_completes_successfully(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_upload_file,
        mock_send_notification,
    ):
        # Given: A valid video file and processing configuration
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 100

        # When: Processing the video
        self.service.process_video(
            s3_path=self.s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should complete all processing steps successfully
        mock_download_file.assert_called_once_with(
            "test-bucket", "videos/sample.mp4", "/tmp/test/test-request-123/sample.mp4"
        )
        mock_makedirs.assert_called_once_with("/tmp/test/test-request-123/frames")
        mock_extract_frames.assert_called_once_with(
            "/tmp/test/test-request-123/sample.mp4", "/tmp/test/test-request-123/frames"
        )
        mock_create_zip_archive.assert_called_once_with(
            "/tmp/test/test-request-123/frames",
            "/tmp/test/test-request-123/sample_frames.zip",
        )
        mock_upload_file.assert_called_once()
        mock_send_notification.assert_called_once()

        notification_call = mock_send_notification.call_args
        assert notification_call[1]["queue_url"] == self.notification_queue_url
        assert notification_call[1]["request_id"] == self.request_id
        assert notification_call[1]["status"] == "SUCCESS"
        assert "processed/" in notification_call[1]["result_s3_path"]

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_video_with_no_frames_when_processing_then_sends_no_frames_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_send_notification,
    ):
        # Given: A video file that produces no frames
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 0

        # When: Processing the video
        self.service.process_video(
            s3_path=self.s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should send notification about no frames extracted
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="NO_FRAMES_EXTRACTED",
        )

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_download_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_send_notification,
    ):
        # Given: S3 download operation that fails
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_download_file.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey"}}, operation_name="GetObject"
        )

        # When: Processing the video and download fails
        # Then: Should raise ClientError and send failure notification
        with pytest.raises(ClientError):
            self.service.process_video(
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_frame_extraction_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_send_notification,
    ):
        # Given: Frame extraction operation that fails
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.side_effect = ValueError("Could not open video file")

        # When: Processing the video and frame extraction fails
        # Then: Should raise ValueError and send failure notification
        with pytest.raises(ValueError):
            self.service.process_video(
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_upload_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_upload_file,
        mock_send_notification,
    ):
        # Given: S3 upload operation that fails
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 50
        mock_upload_file.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied"}},
            operation_name="PutObject",
        )

        # When: Processing the video and upload fails
        # Then: Should raise ClientError and send failure notification
        with pytest.raises(ClientError):
            self.service.process_video(
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.utils.parse_s3_path")
    def test_given_invalid_s3_path_when_processing_then_raises_value_error(
        self, mock_parse_s3_path
    ):
        # Given: Invalid S3 path format
        mock_parse_s3_path.side_effect = ValueError("Invalid S3 path format")

        # When: Processing with invalid S3 path
        # Then: Should raise ValueError
        with pytest.raises(ValueError):
            self.service.process_video(
                s3_path="invalid-path",
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_zip_creation_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_send_notification,
    ):
        # Given: ZIP archive creation that fails
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 25
        mock_create_zip_archive.side_effect = OSError("Permission denied")

        # When: Processing the video and zip creation fails
        # Then: Should raise OSError and send failure notification
        with pytest.raises(OSError):
            self.service.process_video(
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_nested_s3_path_when_processing_then_handles_correctly(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_upload_file,
        mock_send_notification,
    ):
        # Given: Video file with nested S3 path
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 30
        nested_s3_path = "s3://test-bucket/folder/subfolder/video.mp4"

        # When: Processing video with nested path
        self.service.process_video(
            s3_path=nested_s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should handle nested path correctly
        mock_download_file.assert_called_once_with(
            "test-bucket",
            "folder/subfolder/video.mp4",
            "/tmp/test/test-request-123/video.mp4",
        )
        mock_extract_frames.assert_called_once()
        mock_create_zip_archive.assert_called_once()
        mock_upload_file.assert_called_once()
        mock_send_notification.assert_called_once()

    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_video_processing_when_complete_then_formats_output_path_correctly(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_upload_file,
        mock_send_notification,
    ):
        # Given: Video processing configuration
        mock_tmpdir_instance = MagicMock()
        mock_tmpdir_instance.__enter__.return_value = "/tmp/test"
        mock_tmpdir.return_value = mock_tmpdir_instance
        mock_extract_frames.return_value = 15

        # When: Processing the video successfully
        self.service.process_video(
            s3_path=self.s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should format output path correctly
        upload_call = mock_upload_file.call_args
        assert upload_call[0][1] == self.output_bucket_name
        assert "processed/" in upload_call[0][2]
        assert self.request_id in upload_call[0][2]

        notification_call = mock_send_notification.call_args
        result_s3_path = notification_call[1]["result_s3_path"]
        assert result_s3_path.startswith(f"s3://{self.output_bucket_name}/processed/")
        assert self.request_id in result_s3_path
        assert "sample_frames.zip" in result_s3_path
