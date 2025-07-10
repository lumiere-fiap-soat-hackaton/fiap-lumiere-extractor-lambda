import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from src.services.processing_service import VideoProcessingService


class TestVideoProcessingService:

    def setup_method(self):
        self.s3_bucket_name = "test-output-bucket"
        self.service = VideoProcessingService()
        self.request_id = "test-request-123"
        self.s3_path = "videos/sample.mp4"
        self.notification_queue_url = (
            "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        )

    def test_given_service_when_initializing_then_sets_attributes(self):
        # Given: VideoProcessingService
        # When: Initializing VideoProcessingService
        # Then: Should set the correct attributes
        assert self.service.processed_base_path == "processed"

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.format_s3_path")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_valid_video_when_processing_then_completes_successfully(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_format_s3_path,
        mock_upload_file,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: Valid video processing setup
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)  # 1GB free space
        mock_extract_frames.return_value = 10  # 10 frames extracted
        mock_format_s3_path.return_value = (
            "processed/test-request-123/sample_frames.zip",
            "s3://test-output-bucket/processed/test-request-123/sample_frames.zip",
        )
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 8000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 240,
        }.get(key, default)

        # When: Processing the video
        self.service.process_video(
            s3_bucket_name=self.s3_bucket_name,
            s3_path=self.s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should complete all steps successfully
        mock_download_file.assert_called_once()
        mock_extract_frames.assert_called_once_with(
            video_path="/tmp/test_tmpdir/test-request-123/sample.mp4",
            output_dir="/tmp/test_tmpdir/test-request-123/frames",
            max_frames=8000,
            timeout_seconds=240,
        )
        mock_create_zip_archive.assert_called_once()
        mock_upload_file.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="s3://test-output-bucket/processed/test-request-123/sample_frames.zip",
            status="SUCCESS",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_video_with_no_frames_when_processing_then_sends_no_frames_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_extract_frames,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: Video processing that extracts no frames
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)
        mock_extract_frames.return_value = 0  # No frames extracted
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 8000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 240,
        }.get(key, default)

        # When: Processing the video
        self.service.process_video(
            s3_bucket_name=self.s3_bucket_name,
            s3_path=self.s3_path,
            request_id=self.request_id,
            notification_queue_url=self.notification_queue_url,
        )

        # Then: Should send no frames notification and return early
        mock_download_file.assert_called_once()
        mock_extract_frames.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="NO_FRAMES_EXTRACTED",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_download_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: S3 download that fails
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)
        mock_download_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        mock_get_config.return_value = 8000

        # When: Processing the video with download failure
        # Then: Should raise exception and send failure notification
        with pytest.raises(ClientError):
            self.service.process_video(
                s3_bucket_name=self.s3_bucket_name,
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_download_file.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_frame_extraction_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_extract_frames,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: Frame extraction that fails
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)
        mock_extract_frames.side_effect = Exception("Frame extraction failed")
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 8000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 240,
        }.get(key, default)

        # When: Processing the video with extraction failure
        # Then: Should raise exception and send failure notification
        with pytest.raises(Exception, match="Frame extraction failed"):
            self.service.process_video(
                s3_bucket_name=self.s3_bucket_name,
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_download_file.assert_called_once()
        mock_extract_frames.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.format_s3_path")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_zip_creation_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_format_s3_path,
        mock_upload_file,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: Zip creation that fails
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)
        mock_extract_frames.return_value = 10
        mock_create_zip_archive.side_effect = Exception("Zip creation failed")
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 8000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 240,
        }.get(key, default)

        # When: Processing the video with zip creation failure
        # Then: Should raise exception and send failure notification
        with pytest.raises(Exception, match="Zip creation failed"):
            self.service.process_video(
                s3_bucket_name=self.s3_bucket_name,
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_download_file.assert_called_once()
        mock_extract_frames.assert_called_once()
        mock_create_zip_archive.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.sqs_handler.send_completion_notification")
    @patch("src.services.processing_service.s3_handler.upload_file")
    @patch("src.services.processing_service.utils.format_s3_path")
    @patch("src.services.processing_service.utils.create_zip_archive")
    @patch("src.services.processing_service.video_processor.extract_frames")
    @patch("src.services.processing_service.s3_handler.download_file")
    @patch("src.services.processing_service.shutil.disk_usage")
    @patch("src.services.processing_service.tempfile.TemporaryDirectory")
    @patch("os.makedirs")
    def test_given_upload_failure_when_processing_then_sends_failure_notification(
        self,
        mock_makedirs,
        mock_tmpdir,
        mock_disk_usage,
        mock_download_file,
        mock_extract_frames,
        mock_create_zip_archive,
        mock_format_s3_path,
        mock_upload_file,
        mock_send_notification,
        mock_get_config,
    ):
        # Given: S3 upload that fails
        mock_tmpdir.return_value.__enter__.return_value = "/tmp/test_tmpdir"
        mock_disk_usage.return_value = MagicMock(free=1024**3)
        mock_extract_frames.return_value = 10
        mock_format_s3_path.return_value = ("key", "s3://bucket/key")
        mock_upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 8000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 240,
        }.get(key, default)

        # When: Processing the video with upload failure
        # Then: Should raise exception and send failure notification
        with pytest.raises(ClientError):
            self.service.process_video(
                s3_bucket_name=self.s3_bucket_name,
                s3_path=self.s3_path,
                request_id=self.request_id,
                notification_queue_url=self.notification_queue_url,
            )

        mock_download_file.assert_called_once()
        mock_extract_frames.assert_called_once()
        mock_create_zip_archive.assert_called_once()
        mock_upload_file.assert_called_once()
        mock_send_notification.assert_called_once_with(
            queue_url=self.notification_queue_url,
            request_id=self.request_id,
            result_s3_path="",
            status="FAILURE",
        )

    @patch("src.services.processing_service.config.get_config_parameter")
    @patch("src.services.processing_service.shutil.disk_usage")
    def test_given_service_when_processing_starts_then_logs_disk_space(
        self, mock_disk_usage, mock_get_config
    ):
        # Given: Available disk space
        mock_disk_usage.return_value = MagicMock(free=2 * 1024**3)  # 2GB free
        mock_get_config.return_value = 8000

        # When: Starting video processing (we'll patch to stop early)
        with patch(
            "src.services.processing_service.tempfile.TemporaryDirectory"
        ) as mock_tmpdir:
            mock_tmpdir.return_value.__enter__.side_effect = Exception("Stop early")

            with patch("src.services.processing_service.logger") as mock_logger:
                try:
                    self.service.process_video(
                        s3_bucket_name=self.s3_bucket_name,
                        s3_path=self.s3_path,
                        request_id=self.request_id,
                        notification_queue_url=self.notification_queue_url,
                    )
                except Exception:
                    pass  # Expected to stop early

                # Then: Should log disk space information
                mock_logger.info.assert_any_call("Available /tmp space: 2.00GB")

    @patch("src.services.processing_service.config.get_config_parameter")
    def test_given_custom_config_when_processing_then_uses_config_values(
        self, mock_get_config
    ):
        # Given: Custom configuration values
        mock_get_config.side_effect = lambda key, default=None: {
            "VIDEO_PROCESSING_MAX_FRAMES": 5000,
            "VIDEO_PROCESSING_TIMEOUT_SECONDS": 180,
        }.get(key, default)

        # When: Processing video (mock to check extract_frames call)
        with patch(
            "src.services.processing_service.tempfile.TemporaryDirectory"
        ) as mock_tmpdir:
            with patch(
                "src.services.processing_service.shutil.disk_usage"
            ) as mock_disk_usage:
                with patch("src.services.processing_service.s3_handler.download_file"):
                    with patch(
                        "src.services.processing_service.video_processor.extract_frames"
                    ) as mock_extract:
                        with patch(
                            "src.services.processing_service.sqs_handler.send_completion_notification"
                        ):
                            with patch("os.makedirs"):
                                mock_tmpdir.return_value.__enter__.return_value = (
                                    "/tmp/test"
                                )
                                mock_disk_usage.return_value = MagicMock(
                                    free=1024**3
                                )  # 1GB free
                                mock_extract.return_value = (
                                    0  # No frames to trigger early return
                                )

                                self.service.process_video(
                                    s3_bucket_name=self.s3_bucket_name,
                                    s3_path=self.s3_path,
                                    request_id=self.request_id,
                                    notification_queue_url=self.notification_queue_url,
                                )

                                # Then: Should use custom config values
                                mock_extract.assert_called_once_with(
                                    video_path="/tmp/test/test-request-123/sample.mp4",
                                    output_dir="/tmp/test/test-request-123/frames",
                                    max_frames=5000,
                                    timeout_seconds=180,
                                )
