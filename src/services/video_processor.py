import cv2
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_frames(video_path: str, output_dir: str) -> int:
    """Extracts all frames from a video file and saves them as JPEG images."""
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        raise ValueError(f"Error: Could not open video file {video_path}")

    frame_count = 0
    logger.info(f"Starting frame extraction from {Path(video_path).name}...")

    try:
        while True:
            success, frame = video_capture.read()
            if not success:
                break

            frame_filename = os.path.join(output_dir, f"frame_{frame_count:08d}.jpg")
            cv2.imwrite(frame_filename, frame)
            frame_count += 1

            if frame_count > 0 and frame_count % 100 == 0:
                logger.info(f"Extracted {frame_count} frames...")
    finally:
        video_capture.release()

    logger.info(f"Finished extraction. Total frames: {frame_count}")
    return frame_count
