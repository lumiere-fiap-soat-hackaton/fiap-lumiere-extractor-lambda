import pytest
from unittest.mock import patch, MagicMock, call
import cv2

from src.services.video_processor import extract_frames


class TestVideoProcessor:

    def setup_method(self):
        self.test_video_path = "/tmp/test_video.mp4"
        self.test_output_dir = "/tmp/frames"

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_valid_video_when_extracting_frames_then_returns_correct_count(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A valid video file with 3 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
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
            call("/tmp/frames/frame_00000000.jpg", "frame1"),
            call("/tmp/frames/frame_00000001.jpg", "frame2"),
            call("/tmp/frames/frame_00000002.jpg", "frame3"),
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

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_empty_video_when_extracting_frames_then_returns_zero_count(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: An empty video file with no frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.return_value = (False, None)

        # When: Extracting frames from the empty video
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should return zero frames and not save any files
        assert frame_count == 0
        mock_capture.read.assert_called_once()
        mock_imwrite.assert_not_called()
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_large_video_when_extracting_frames_then_processes_all_frames(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A large video file with 150 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        successful_reads = [(True, f"frame{i}") for i in range(150)]
        successful_reads.append((False, None))
        mock_capture.read.side_effect = successful_reads
        mock_join.side_effect = [f"/tmp/frames/frame_{i:08d}.jpg" for i in range(150)]

        # When: Extracting frames from the large video
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should process all 150 frames
        assert frame_count == 150
        assert mock_capture.read.call_count == 151
        assert mock_imwrite.call_count == 150
        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_video_frames_when_extracting_then_numbers_frames_correctly(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A video file with 5 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.side_effect = [
            (True, "frame0"),
            (True, "frame1"),
            (True, "frame2"),
            (True, "frame3"),
            (True, "frame4"),
            (False, None),
        ]
        mock_join.side_effect = [
            "/tmp/frames/frame_00000000.jpg",
            "/tmp/frames/frame_00000001.jpg",
            "/tmp/frames/frame_00000002.jpg",
            "/tmp/frames/frame_00000003.jpg",
            "/tmp/frames/frame_00000004.jpg",
        ]

        # When: Extracting frames from the video
        frame_count = extract_frames(self.test_video_path, self.test_output_dir)

        # Then: Should number frames correctly with zero-padding
        assert frame_count == 5
        expected_join_calls = [
            call(self.test_output_dir, "frame_00000000.jpg"),
            call(self.test_output_dir, "frame_00000001.jpg"),
            call(self.test_output_dir, "frame_00000002.jpg"),
            call(self.test_output_dir, "frame_00000003.jpg"),
            call(self.test_output_dir, "frame_00000004.jpg"),
        ]
        mock_join.assert_has_calls(expected_join_calls)

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_imwrite_failure_when_extracting_frames_then_raises_exception(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A video file with imwrite operation that fails
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.side_effect = [(True, "frame1"), (False, None)]
        mock_join.return_value = "/tmp/frames/frame_00000000.jpg"
        mock_imwrite.side_effect = cv2.error("Failed to write image")

        # When: Extracting frames and imwrite fails
        # Then: Should raise cv2.error and cleanup resources
        with pytest.raises(cv2.error):
            extract_frames(self.test_video_path, self.test_output_dir)

        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_custom_output_directory_when_extracting_frames_then_uses_custom_path(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A video file and custom output directory
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.side_effect = [(True, "frame1"), (False, None)]
        custom_output_dir = "/custom/output/directory"
        expected_frame_path = "/custom/output/directory/frame_00000000.jpg"
        mock_join.return_value = expected_frame_path

        # When: Extracting frames with custom output directory
        frame_count = extract_frames(self.test_video_path, custom_output_dir)

        # Then: Should use custom output directory for frame storage
        assert frame_count == 1
        mock_join.assert_called_once_with(custom_output_dir, "frame_00000000.jpg")
        mock_imwrite.assert_called_once_with(expected_frame_path, "frame1")

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_large_video_when_extracting_frames_then_logs_progress(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A large video file with 250 frames
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        successful_reads = [(True, f"frame{i}") for i in range(250)]
        successful_reads.append((False, None))
        mock_capture.read.side_effect = successful_reads
        mock_join.side_effect = [f"/tmp/frames/frame_{i:08d}.jpg" for i in range(250)]

        # When: Extracting frames from the large video
        with patch("src.services.video_processor.logger.info") as mock_logger:
            frame_count = extract_frames(self.test_video_path, self.test_output_dir)

            # Then: Should log progress at 100-frame intervals
            assert frame_count == 250
            progress_calls = [
                call
                for call in mock_logger.call_args_list
                if "Extracted" in str(call) and "frames..." in str(call)
            ]
            assert len(progress_calls) == 2

    @patch("src.services.video_processor.cv2.VideoCapture")
    def test_given_video_capture_exception_when_extracting_frames_then_raises_exception(
        self, mock_video_capture
    ):
        # Given: VideoCapture constructor that raises exception
        mock_video_capture.side_effect = Exception("Failed to create VideoCapture")

        # When: Attempting to extract frames
        # Then: Should raise the exception
        with pytest.raises(Exception, match="Failed to create VideoCapture"):
            extract_frames(self.test_video_path, self.test_output_dir)

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_video_read_exception_when_extracting_frames_then_raises_exception(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: A video file where read operation raises exception
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.side_effect = Exception("Failed to read frame")

        # When: Attempting to read frames
        # Then: Should raise exception and cleanup resources
        with pytest.raises(Exception, match="Failed to read frame"):
            extract_frames(self.test_video_path, self.test_output_dir)

        mock_capture.release.assert_called_once()

    @patch("src.services.video_processor.cv2.VideoCapture")
    @patch("src.services.video_processor.cv2.imwrite")
    @patch("os.path.join")
    def test_given_paths_with_spaces_when_extracting_frames_then_handles_correctly(
        self, mock_join, mock_imwrite, mock_video_capture
    ):
        # Given: File paths containing spaces
        mock_capture = MagicMock()
        mock_video_capture.return_value = mock_capture
        mock_capture.isOpened.return_value = True
        mock_capture.read.side_effect = [(True, "frame1"), (False, None)]
        video_path_with_spaces = "/tmp/my video file.mp4"
        output_dir_with_spaces = "/tmp/output frames"
        expected_frame_path = "/tmp/output frames/frame_00000000.jpg"
        mock_join.return_value = expected_frame_path

        # When: Extracting frames with paths containing spaces
        frame_count = extract_frames(video_path_with_spaces, output_dir_with_spaces)

        # Then: Should handle paths with spaces correctly
        assert frame_count == 1
        mock_video_capture.assert_called_once_with(video_path_with_spaces)
        mock_join.assert_called_once_with(output_dir_with_spaces, "frame_00000000.jpg")
        mock_imwrite.assert_called_once_with(expected_frame_path, "frame1")
