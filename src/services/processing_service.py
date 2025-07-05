import logging
import os
import tempfile
from pathlib import Path

# Import infrastructure modules that the service depends on
from ..infra import s3_handler, sqs_handler
from ..common import utils
from . import video_processor

PROCESSED_VIDEO_BASE_PATH = "processed"
logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Encapsulates the core business logic for processing a video.
    This service is framework-agnostic and can be used by any entry point.
    """

    def __init__(self, output_bucket_name: str):
        """
        Initialize the service with output bucket configuration.

        Args:
            output_bucket (str, optional): The S3 bucket to store processed results.
                If None, the source bucket will be used.
        """
        self.output_bucket_name = output_bucket_name
        self.processed_base_path = PROCESSED_VIDEO_BASE_PATH

    def process_video(
        self, s3_path: str, request_id: str, notification_queue_url: str
    ) -> None:
        """
        Orchestrates the entire video processing and notification workflow.

        Args:
            s3_path (str): The full S3 path to the video (e.g., "s3://bucket/key").
            request_id (str): The unique ID for this processing request.
            notification_queue_url (str): The SQS queue to send completion notifications to.
        """
        logger.info(
            f"Starting video processing workflow for request ID: {request_id}, S3 path: {s3_path}"
        )

        source_bucket, source_key = utils.parse_s3_path(s3_path)
        base_filename = Path(source_key).stem

        with tempfile.TemporaryDirectory() as tmpdir:
            local_video_path = os.path.join(tmpdir, request_id, Path(source_key).name)
            frames_output_dir = os.path.join(tmpdir, request_id, "frames")
            os.makedirs(frames_output_dir)

            try:
                # Download the video file from S3
                s3_handler.download_file(source_bucket, source_key, local_video_path)

                # Process the video to extract frames
                frame_count = video_processor.extract_frames(
                    local_video_path, frames_output_dir
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
                    f"Uploading processed frames zip to S3: processed/{Path(local_zip_path).name} to {self.output_bucket_name}"
                )
                output_key, output_s3_path = utils.format_s3_path(
                    bucket=self.output_bucket_name,
                    base_path=self.processed_base_path,
                    request_id=request_id,
                    key=Path(local_zip_path).name,
                )
                s3_handler.upload_file(
                    local_zip_path, self.output_bucket_name, output_key
                )

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
