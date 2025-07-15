import cv2
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    output_dir: str,
    max_frames: int = None,
    timeout_seconds: int = 240,
) -> int:
    """
    Extracts frames from a video file and saves them as JPEG images.

    Args:
        video_path: Path to the input video file
        output_dir: Directory to save extracted frames
        max_frames: Maximum number of frames to extract (None for all)
        timeout_seconds: Maximum time to spend extracting frames

    Returns:
        Number of frames extracted
    """
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        raise ValueError(f"Error: Could not open video file {video_path}")

    # Get video properties for better planning
    total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video_capture.get(cv2.CAP_PROP_FPS)

    logger.info(
        f"Video info - Total frames: {total_frames}, FPS: {fps}, Duration: {total_frames/fps:.2f}s"
    )

    # Calculate effective max frames
    if max_frames is None:
        effective_max_frames = total_frames
    else:
        effective_max_frames = min(max_frames, total_frames)

    logger.info(f"Will extract up to {effective_max_frames} frames")

    frame_count = 0
    extracted_count = 0
    start_time = time.time()

    logger.info(f"-- Starting frame extraction from {Path(video_path).name}...")

    try:
        while True:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                logger.warning(
                    f"Timeout reached ({timeout_seconds}s). Stopping extraction."
                )
                break

            # Check max frames limit
            if max_frames and extracted_count >= max_frames:
                logger.info(
                    f"Reached maximum frames limit ({max_frames}). Stopping extraction."
                )
                break

            success, frame = video_capture.read()
            if not success:
                break

            # Extract all frames
            frame_filename = os.path.join(
                output_dir, f"frame_{extracted_count:08d}.jpg"
            )

            # Optimize JPEG quality for smaller file sizes
            cv2.imwrite(frame_filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            extracted_count += 1

            if extracted_count > 0 and extracted_count % 50 == 0:
                elapsed = time.time() - start_time
                logger.debug(f"Extracted {extracted_count} frames in {elapsed:.2f}s...")

                # Check available disk space in /tmp
                import shutil

                disk_usage = shutil.disk_usage("/tmp")
                free_mb = disk_usage.free / (1024 * 1024)
                if free_mb < 50:  # Less than 50MB free
                    logger.warning(
                        f"Low disk space in /tmp: {free_mb:.1f}MB. Stopping extraction."
                    )
                    break

            frame_count += 1

    except Exception as e:
        logger.error(f"Error during frame extraction: {e}")
        raise
    finally:
        video_capture.release()

    elapsed_time = time.time() - start_time
    logger.info(
        f"-- Finished extraction. Extracted {extracted_count} frames in {elapsed_time:.2f}s"
    )
    return extracted_count
