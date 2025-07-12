import logging
import os
import tempfile
from pathlib import Path

# Import infrastructure modules that the service depends on
from ..infra import s3_handler, sqs_handler, config
from ..common import utils
from . import video_processor

PROCESSED_VIDEO_BASE_PATH = "results"
logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Encapsulates the core business logic for processing a video.
    This service is framework-agnostic and can be used by any entry point.
    """

    def __init__(self):
        """
        Initialize the service with output bucket configuration.

        Args:
            s3_bucket_name (str): The S3 bucket to store processed results.
        """
        self.processed_base_path = PROCESSED_VIDEO_BASE_PATH

    def process_video(
        self,
        s3_bucket_name: str,
        s3_key: str,
        request_id: str,
        notification_queue_url: str,
    ) -> None:
        """
        Orchestrates the entire video processing and notification workflow.

        Args:
            s3_bucket_name (str): The S3 bucket containing the video.
            s3_key (str): The S3 key/path to the video (e.g., "videos/filename.mp4").
            request_id (str): The unique ID for this processing request.
            notification_queue_url (str): The SQS queue to send completion notifications to.
        """
        logger.info(
            f"Starting video processing workflow for request ID: {request_id}, S3 key: {s3_key}"
        )

        source_bucket = s3_bucket_name
        source_key = s3_key
        base_filename = Path(source_key).stem

        with tempfile.TemporaryDirectory() as tmpdir:
            local_video_path = os.path.join(tmpdir, request_id, Path(source_key).name)
            frames_output_dir = os.path.join(tmpdir, request_id, "frames")
            os.makedirs(os.path.dirname(local_video_path), exist_ok=True)
            os.makedirs(frames_output_dir)

            try:
                # Download the video file from S3
                s3_handler.download_file(source_bucket, source_key, local_video_path)

                # Process the video to extract frames with Lambda-optimized settings
                max_frames = int(
                    config.get_config_parameter("VIDEO_PROCESSING_MAX_FRAMES", "20000")
                )
                timeout_seconds = int(
                    config.get_config_parameter(
                        "VIDEO_PROCESSING_TIMEOUT_SECONDS", "240"
                    )
                )

                # Process the video to extract frames
                frame_count = video_processor.extract_frames(
                    local_video_path, frames_output_dir, max_frames, timeout_seconds
                )

                if frame_count == 0:
                    logger.warning(f"No frames extracted for request {request_id}.")
                    # Still notify completion via SQS, but indicate no frames were extracted
                    sqs_handler.send_completion_notification(
                        queue_url=notification_queue_url,
                        request_id=request_id,
                        result_s3_path="",
                        status="NO_FRAMES_EXTRACTED",
                    )
                    logger.info(f"Sent no-frames notification for request {request_id}")
                    return

                # Package resulting frames into a zip archive
                local_zip_path = os.path.join(
                    tmpdir, request_id, f"{base_filename}_frames.zip"
                )
                utils.create_zip_archive(frames_output_dir, local_zip_path)

                # Upload the zip archive back to S3
                logger.info(
                    f"Uploading processed frames zip to S3: processed/{Path(local_zip_path).name} to {s3_bucket_name}"
                )
                output_key = utils.format_s3_path(
                    bucket=s3_bucket_name,
                    base_path=self.processed_base_path,
                    request_id=request_id,
                    key=Path(local_zip_path).name,
                )
                s3_handler.upload_file(local_zip_path, s3_bucket_name, output_key)

                # Notify completion via SQS
                sqs_handler.send_completion_notification(
                    queue_url=notification_queue_url,
                    request_id=request_id,
                    result_s3_path=output_key,
                    status="SUCCESS",
                )

                logger.info(
                    f"Successfully completed workflow for request {request_id}. "
                )
            except Exception as e:
                logger.error(f"Error processing video for request {request_id}: {e}")
                # Notify failure via SQS
                sqs_handler.send_completion_notification(
                    queue_url=notification_queue_url,
                    request_id=request_id,
                    result_s3_path="",
                    status="FAILURE",
                )
                logger.info(f"Sent failure notification for request {request_id}")
                raise
