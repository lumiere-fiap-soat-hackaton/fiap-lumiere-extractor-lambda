import pytest
from unittest.mock import patch, MagicMock, call
import cv2

from src.services.video_processor import extract_frames


class TestVideoProcessor:

    def setup_method(self):
        self.test_video_path = "/tmp/test_video.mp4"
        self.test_output_dir = "/tmp/frames"

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_valid_video_when_extracting_frames_then_returns_correct_count(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A valid video file with 3 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            3 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.side_effect = [
            (True, "frame1"),
            (True, "frame2"),
            (True, "frame3"),
            (False, None),
        ]
        mock_join.side_effect = [
            "/tmp/frames/frame_00000000.jpg",
            "/tmp/frames/frame_00000001.jpg",
            "/tmp/frames/frame_00000002.jpg",
        ]
        # Provide enough time values for all time.time() calls
        mock_time.return_value = 0

        # When: Extracting frames from the video
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should return the correct frame count and save all frames
        assert frame_count == 3
        mock_video_capture.assert_called_once_with(self.test_video_path)
        mock_capture.isOpened.assert_called_once()
        assert mock_capture.read.call_count == 4
        assert mock_imwrite.call_count == 3
        mock_capture.release.assert_called_once()
        expected_calls = [
            call(
                "/tmp/frames/frame_00000000.jpg",
                "frame1",
                [cv2.IMWRITE_JPEG_QUALITY, 85],
            ),
            call(
                "/tmp/frames/frame_00000001.jpg",
                "frame2",
                [cv2.IMWRITE_JPEG_QUALITY, 85],
            ),
            call(
                "/tmp/frames/frame_00000002.jpg",
                "frame3",
                [cv2.IMWRITE_JPEG_QUALITY, 85],
            ),
        ]
        mock_imwrite.assert_has_calls(expected_calls)

    @patch("src.services.video_processor.cv2.VideoCapture")
    def test_given_invalid_video_when_extracting_frames_then_raises_value_error(
        self, mock_video_capture
    ):
        # Given: A video file that cannot be opened
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = False

        # When: Attempting to extract frames from the invalid video
        # Then: Should raise ValueError with appropriate message
        with pytest.raises(ValueError, match="Error: Could not open video file"):
            extract_frames(self.test_video_path, self.test_output_dir)

        mock_video_capture.assert_called_once_with(self.test_video_path)
        mock_capture.isOpened.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_empty_video_when_extracting_frames_then_returns_zero_count(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: An empty video file with no frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            0 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.return_value = (False, None)
        mock_time.return_value = 0

        # When: Extracting frames from the empty video
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should return zero frames and not save any files
        assert frame_count == 0
        mock_capture.read.assert_called_once()
        mock_imwrite.assert_not_called()
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_max_frames_limit_when_extracting_frames_then_stops_at_limit(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A video file with many frames but max_frames limit of 2
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            100 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.side_effect = [
            (True, "frame1"),
            (True, "frame2"),
            (True, "frame3"),  # This should not be processed due to max_frames=2
            (False, None),
        ]
        mock_join.side_effect = [
            "/tmp/frames/frame_00000000.jpg",
            "/tmp/frames/frame_00000001.jpg",
        ]
        mock_time.return_value = 0

        # When: Extracting frames with max_frames limit
        frame_count = extract_frames(
            self.test_video_path, self.test_output_dir, max_frames=2
        )

        # Then: Should stop at max_frames limit
        assert frame_count == 2
        assert mock_imwrite.call_count == 2
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_timeout_when_extracting_frames_then_stops_at_timeout(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A video file and timeout of 2 seconds
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            100 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.side_effect = [
            (True, "frame1"),
            (True, "frame2"),
            (True, "frame3"),  # This should trigger timeout check
            (False, None),
        ]
        mock_join.side_effect = [
            "/tmp/frames/frame_00000000.jpg",
            "/tmp/frames/frame_00000001.jpg",
        ]
        # Mock time to simulate timeout after 2 frames
        mock_time.side_effect = [0, 1, 1.5, 3, 3, 3, 3, 3]  # Extra values for logging

        # When: Extracting frames with timeout
        frame_count = extract_frames(
            self.test_video_path, self.test_output_dir, timeout_seconds=2
        )

        # Then: Should stop due to timeout
        assert frame_count == 2
        assert mock_imwrite.call_count == 2
        mock_capture.release.assert_called_once()

    @patch("shutil.disk_usage")
    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_low_disk_space_when_extracting_frames_then_stops_extraction(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time, mock_disk_usage
    ):
        # Given: A video file and low disk space after 50 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            100 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )

        # Create 52 frames to trigger disk space check at frame 50
        mock_capture.read.side_effect = [(True, f"frame{i}") for i in range(52)] + [
            (False, None)
        ]
        mock_join.side_effect = [f"/tmp/frames/frame_{i:08d}.jpg" for i in range(52)]
        mock_time.return_value = 0  # Keep time constant to avoid timeout

        # Mock disk usage to show low space
        mock_disk_usage.return_value = MagicMock(
            free=30 * 1024 * 1024
        )  # 30MB free (< 50MB threshold)

        # When: Extracting frames with low disk space
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should stop due to low disk space after 50 frames
        assert frame_count == 50
        assert mock_imwrite.call_count == 50
        mock_disk_usage.assert_called_with("/tmp")
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_imwrite_failure_when_extracting_frames_then_raises_exception(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A video file and cv2.imwrite that fails
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            1 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.return_value = (True, "frame1")
        mock_join.return_value = "/tmp/frames/frame_00000000.jpg"
        mock_imwrite.side_effect = Exception("Write failed")
        mock_time.return_value = 0

        # When: Attempting to extract frames with imwrite failure
        # Then: Should raise the exception and still release video capture
        with pytest.raises(Exception, match="Write failed"):
            extract_frames(self.test_video_path, self.test_output_dir)

        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_custom_parameters_when_extracting_frames_then_uses_custom_values(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: Custom output directory, max_frames, and timeout
        custom_output_dir = "/custom/output"
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            10 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.side_effect = [(True, f"frame{i}") for i in range(5)] + [
            (False, None)
        ]
        mock_join.side_effect = [
            f"{custom_output_dir}/frame_{i:08d}.jpg" for i in range(5)
        ]
        mock_time.return_value = 0

        # When: Extracting frames with custom parameters
        frame_count = extract_frames(
            self.test_video_path, custom_output_dir, max_frames=5, timeout_seconds=10
        )

        # Then: Should use custom values
        assert frame_count == 5
        for i in range(5):
            mock_join.assert_any_call(custom_output_dir, f"frame_{i:08d}.jpg")
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    def test_given_video_capture_exception_when_extracting_frames_then_raises_exception(
        self, mock_video_capture, mock_time
    ):
        # Given: VideoCapture that raises an exception
        mock_video_capture.side_effect = Exception("VideoCapture failed")
        mock_time.return_value = 0

        # When: Attempting to extract frames with VideoCapture failure
        # Then: Should raise the exception
        with pytest.raises(Exception, match="VideoCapture failed"):
            extract_frames(self.test_video_path, self.test_output_dir)

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_video_properties_when_extracting_frames_then_logs_video_info(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A video file with specific properties
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            10 if prop == cv2.CAP_PROP_FRAME_COUNT else 25.0
        )
        mock_capture.read.side_effect = [(True, f"frame{i}") for i in range(2)] + [
            (False, None)
        ]
        mock_join.side_effect = [f"/tmp/frames/frame_{i:08d}.jpg" for i in range(2)]
        mock_time.return_value = 0

        # When: Extracting frames
        with patch("src.services.video_processor.logger") as mock_logger:
            frame_count = extract_frames(
                self.test_video_path, self.test_output_dir, max_frames=2
            )

            # Then: Should log video properties
            mock_logger.info.assert_any_call(
                "Video info - Total frames: 10, FPS: 25.0, Duration: 0.40s"
            )
            mock_logger.info.assert_any_call("Will extract up to 2 frames")
            assert frame_count == 2

    @patch("src.services.video_processor.time.time")
    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_progress_logging_when_extracting_many_frames_then_logs_progress(
        self, mock_join, mock_imwrite, mock_video_capture, mock_time
    ):
        # Given: A video file with 100 frames to trigger progress logging
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: (
            100 if prop == cv2.CAP_PROP_FRAME_COUNT else 30.0
        )
        mock_capture.read.side_effect = [(True, f"frame{i}") for i in range(100)] + [
            (False, None)
        ]
        mock_join.side_effect = [f"/tmp/frames/frame_{i:08d}.jpg" for i in range(100)]
        mock_time.return_value = 5  # Fixed time for progress calculation

        # When: Extracting frames with progress logging
        with patch("src.services.video_processor.logger") as mock_logger:
            frame_count = extract_frames(self.test_video_path, self.test_output_dir)

            # Then: Should log progress at frame 50 and 100
            progress_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "Extracted" in str(call) and "frames in" in str(call)
            ]
            assert len(progress_calls) >= 2  # Should have progress logs at 50 and 100
            assert frame_count == 100
