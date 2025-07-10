import logging
import os
import tempfile
import shutil
from pathlib import Path

# Import infrastructure modules that the service depends on
from ..infra import s3_handler, sqs_handler, config
from ..common import utils
from . import video_processor

PROCESSED_VIDEO_BASE_PATH = "processed"
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
        s3_path: str,
        request_id: str,
        notification_queue_url: str,
    ) -> None:
        """
        Orchestrates the entire video processing and notification workflow.

        Args:
            s3_bucket_name (str): The S3 bucket where the video is stored.
            s3_path (str): The S3 path to the video file.
            request_id (str): Unique identifier for the processing request.
            notification_queue_url (str): URL of the SQS queue to send notifications.
        """
        # Parse the S3 path to extract bucket and object key
        object_key = s3_path
        base_filename = Path(object_key).stem

        logger.info(
            f"Starting video processing workflow for request ID: {request_id}, S3 path: {s3_path}, bucket: {s3_bucket_name}"
        )

        # Check available disk space at start
        disk_info = shutil.disk_usage("/tmp")
        logger.info(f"Available /tmp space: {disk_info.free / (1024**3):.2f}GB")

        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            local_video_path = os.path.join(tmpdir, request_id, Path(object_key).name)
            frames_output_dir = os.path.join(tmpdir, request_id, "frames")

            # Create directories for video file and frames
            os.makedirs(os.path.dirname(local_video_path), exist_ok=True)
            os.makedirs(os.path.dirname(frames_output_dir), exist_ok=True)

            try:
                # Download the video file from S3
                s3_handler.download_file(s3_bucket_name, object_key, local_video_path)

                # Process the video to extract frames with optimizations
                max_frames = config.get_config_parameter(
                    "VIDEO_PROCESSING_MAX_FRAMES",
                    default=8000,  # Limit frames to prevent timeout/memory issues
                )
                timeout_seconds = config.get_config_parameter(
                    "VIDEO_PROCESSING_TIMEOUT_SECONDS",
                    default=240,  # 4 minute timeout (less than Lambda's 5 min)
                )

                frame_count = video_processor.extract_frames(
                    video_path=local_video_path,
                    output_dir=frames_output_dir,
                    max_frames=max_frames,
                    timeout_seconds=timeout_seconds,
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
                output_key, output_s3_path = utils.format_s3_path(
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
                    result_s3_path=output_s3_path,
                    status="SUCCESS",
                )

                logger.info(
                    f"Successfully completed workflow for request {request_id}. "
                    f"Output available at: {output_s3_path}"
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
