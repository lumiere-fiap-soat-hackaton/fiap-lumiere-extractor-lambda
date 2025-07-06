import pytest
import zipfile
from unittest.mock import patch, MagicMock

from src.common.utils import format_s3_path, parse_s3_path, create_zip_archive


class TestUtilsFunctions:

    def test_given_valid_parameters_when_formatting_s3_path_then_returns_correct_format(
        self,
    ):
        # Given: Valid S3 path parameters
        bucket = "test-bucket"
        base_path = "videos"
        request_id = "req-123"
        key = "output.zip"

        # When: Formatting S3 path with mocked datetime
        with patch("src.common.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-01-15"
            object_key, s3_path = format_s3_path(bucket, base_path, request_id, key)

        # Then: Should return properly formatted paths
        expected_object_key = "videos/2024-01-15/req-123/output.zip"
        expected_s3_path = "s3://test-bucket/videos/2024-01-15/req-123/output.zip"
        assert object_key == expected_object_key
        assert s3_path == expected_s3_path

    def test_given_empty_bucket_when_formatting_s3_path_then_raises_value_error(self):
        # Given: Empty bucket parameter
        # When: Formatting S3 path with empty bucket
        # Then: Should raise ValueError
        with pytest.raises(ValueError, match="Both bucket and key must be provided"):
            format_s3_path("", "base", "req-123", "file.zip")

    def test_given_empty_key_when_formatting_s3_path_then_raises_value_error(self):
        # Given: Empty key parameter
        # When: Formatting S3 path with empty key
        # Then: Should raise ValueError
        with pytest.raises(ValueError, match="Both bucket and key must be provided"):
            format_s3_path("bucket", "base", "req-123", "")

    def test_given_none_parameters_when_formatting_s3_path_then_raises_value_error(
        self,
    ):
        # Given: None parameters
        # When: Formatting S3 path with None values
        # Then: Should raise ValueError
        with pytest.raises(ValueError, match="Both bucket and key must be provided"):
            format_s3_path(None, "base", "req-123", "file.zip")

        with pytest.raises(ValueError, match="Both bucket and key must be provided"):
            format_s3_path("bucket", "base", "req-123", None)

    def test_given_special_characters_when_formatting_s3_path_then_handles_correctly(
        self,
    ):
        # Given: Parameters with special characters
        bucket = "test-bucket-123"
        base_path = "videos/processed"
        request_id = "req-456-abc"
        key = "output_file.zip"

        # When: Formatting S3 path with special characters
        with patch("src.common.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-12-25"
            object_key, s3_path = format_s3_path(bucket, base_path, request_id, key)

        # Then: Should handle special characters correctly
        expected_object_key = "videos/processed/2024-12-25/req-456-abc/output_file.zip"
        expected_s3_path = "s3://test-bucket-123/videos/processed/2024-12-25/req-456-abc/output_file.zip"
        assert object_key == expected_object_key
        assert s3_path == expected_s3_path

    def test_given_valid_s3_path_when_parsing_then_returns_bucket_and_key(self):
        # Given: Valid S3 path
        s3_path = "s3://my-bucket/path/to/file.jpg"

        # When: Parsing S3 path
        bucket, key = parse_s3_path(s3_path)

        # Then: Should return correct bucket and key
        assert bucket == "my-bucket"
        assert key == "path/to/file.jpg"

    def test_given_root_file_s3_path_when_parsing_then_returns_bucket_and_key(self):
        # Given: S3 path with file at root
        s3_path = "s3://my-bucket/file.jpg"

        # When: Parsing S3 path
        bucket, key = parse_s3_path(s3_path)

        # Then: Should return correct bucket and key
        assert bucket == "my-bucket"
        assert key == "file.jpg"

    def test_given_nested_s3_path_when_parsing_then_returns_bucket_and_key(self):
        # Given: S3 path with deeply nested structure
        s3_path = "s3://my-bucket/folder1/folder2/folder3/file.jpg"

        # When: Parsing S3 path
        bucket, key = parse_s3_path(s3_path)

        # Then: Should return correct bucket and key
        assert bucket == "my-bucket"
        assert key == "folder1/folder2/folder3/file.jpg"

    def test_given_invalid_scheme_when_parsing_s3_path_then_raises_value_error(self):
        # Given: Invalid scheme
        # When: Parsing path with invalid scheme
        # Then: Should raise ValueError
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            parse_s3_path("http://my-bucket/file.jpg")

    def test_given_no_scheme_when_parsing_s3_path_then_raises_value_error(self):
        # Given: Path without scheme
        # When: Parsing path without scheme
        # Then: Should raise ValueError
        with pytest.raises(ValueError, match="Invalid S3 path format"):
            parse_s3_path("my-bucket/file.jpg")

    def test_given_missing_bucket_or_key_when_parsing_s3_path_then_raises_value_error(
        self,
    ):
        # Given: S3 paths missing bucket or key
        # When: Parsing incomplete paths
        # Then: Should raise ValueError
        with pytest.raises(
            ValueError, match="Invalid S3 path format \\(missing bucket or key\\)"
        ):
            parse_s3_path("s3:///file.jpg")

        with pytest.raises(
            ValueError, match="Invalid S3 path format \\(missing bucket or key\\)"
        ):
            parse_s3_path("s3://my-bucket/")

        with pytest.raises(
            ValueError, match="Invalid S3 path format \\(missing bucket or key\\)"
        ):
            parse_s3_path("s3:///path/file.jpg")

        with pytest.raises(
            ValueError, match="Invalid S3 path format \\(missing bucket or key\\)"
        ):
            parse_s3_path("s3://my-bucket")

    def test_given_bucket_with_numbers_when_parsing_s3_path_then_handles_correctly(
        self,
    ):
        # Given: S3 path with bucket containing numbers
        s3_path = "s3://bucket123/file.jpg"

        # When: Parsing S3 path
        bucket, key = parse_s3_path(s3_path)

        # Then: Should handle numbers correctly
        assert bucket == "bucket123"
        assert key == "file.jpg"

    def test_given_bucket_with_hyphens_when_parsing_s3_path_then_handles_correctly(
        self,
    ):
        # Given: S3 path with bucket containing hyphens
        s3_path = "s3://my-test-bucket-123/path/file.jpg"

        # When: Parsing S3 path
        bucket, key = parse_s3_path(s3_path)

        # Then: Should handle hyphens correctly
        assert bucket == "my-test-bucket-123"
        assert key == "path/file.jpg"

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_directory_with_files_when_creating_zip_then_archives_all_files(
        self, mock_walk, mock_zipfile
    ):
        # Given: Directory with multiple files
        mock_walk.return_value = [
            ("/test/dir", [], ["file1.txt", "file2.txt"]),
            ("/test/dir/subdir", [], ["file3.txt"]),
        ]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # When: Creating ZIP archive
        with patch("src.common.utils.os.path.join") as mock_join, patch(
            "src.common.utils.os.path.relpath"
        ) as mock_relpath:
            mock_join.side_effect = [
                "/test/dir/file1.txt",
                "/test/dir/file2.txt",
                "/test/dir/subdir/file3.txt",
            ]
            mock_relpath.side_effect = ["file1.txt", "file2.txt", "subdir/file3.txt"]
            create_zip_archive("/test/dir", "/test/output.zip")

        # Then: Should create ZIP with all files
        mock_zipfile.assert_called_once_with(
            "/test/output.zip", "w", zipfile.ZIP_DEFLATED
        )
        assert mock_zip.write.call_count == 3
        mock_zip.write.assert_any_call("/test/dir/file1.txt", "file1.txt")
        mock_zip.write.assert_any_call("/test/dir/file2.txt", "file2.txt")
        mock_zip.write.assert_any_call("/test/dir/subdir/file3.txt", "subdir/file3.txt")

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_empty_directory_when_creating_zip_then_creates_empty_archive(
        self, mock_walk, mock_zipfile
    ):
        # Given: Empty directory
        mock_walk.return_value = [("/test/empty", [], [])]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # When: Creating ZIP archive from empty directory
        create_zip_archive("/test/empty", "/test/empty.zip")

        # Then: Should create ZIP but add no files
        mock_zipfile.assert_called_once_with(
            "/test/empty.zip", "w", zipfile.ZIP_DEFLATED
        )
        mock_zip.write.assert_not_called()

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_single_file_when_creating_zip_then_archives_single_file(
        self, mock_walk, mock_zipfile
    ):
        # Given: Directory with single file
        mock_walk.return_value = [("/test/dir", [], ["single.txt"])]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # When: Creating ZIP archive
        with patch("src.common.utils.os.path.join") as mock_join, patch(
            "src.common.utils.os.path.relpath"
        ) as mock_relpath:
            mock_join.return_value = "/test/dir/single.txt"
            mock_relpath.return_value = "single.txt"
            create_zip_archive("/test/dir", "/test/single.zip")

        # Then: Should archive single file
        mock_zip.write.assert_called_once_with("/test/dir/single.txt", "single.txt")

    @patch("src.common.utils.zipfile.ZipFile")
    def test_given_zipfile_error_when_creating_zip_then_raises_exception(
        self, mock_zipfile
    ):
        # Given: ZipFile that raises error
        mock_zipfile.side_effect = zipfile.BadZipFile("Cannot create zip file")

        # When: Creating ZIP archive
        # Then: Should raise BadZipFile exception
        with pytest.raises(zipfile.BadZipFile, match="Cannot create zip file"):
            create_zip_archive("/test/dir", "/test/output.zip")

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_write_error_when_creating_zip_then_raises_exception(
        self, mock_walk, mock_zipfile
    ):
        # Given: Directory with file and write operation that fails
        mock_walk.return_value = [("/test/dir", [], ["file1.txt"])]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        mock_zip.write.side_effect = OSError("Permission denied")

        # When: Creating ZIP archive and write fails
        with patch("src.common.utils.os.path.join") as mock_join, patch(
            "src.common.utils.os.path.relpath"
        ) as mock_relpath:
            mock_join.return_value = "/test/dir/file1.txt"
            mock_relpath.return_value = "file1.txt"

            # Then: Should raise OSError
            with pytest.raises(OSError, match="Permission denied"):
                create_zip_archive("/test/dir", "/test/output.zip")

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_os_walk_error_when_creating_zip_then_raises_exception(
        self, mock_walk, mock_zipfile
    ):
        # Given: os.walk that raises error
        mock_walk.side_effect = OSError("Directory not found")

        # When: Creating ZIP archive and os.walk fails
        # Then: Should raise OSError
        with pytest.raises(OSError, match="Directory not found"):
            create_zip_archive("/test/nonexistent", "/test/output.zip")

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_nested_directories_when_creating_zip_then_preserves_structure(
        self, mock_walk, mock_zipfile
    ):
        # Given: Nested directory structure
        mock_walk.return_value = [
            ("/test/dir", ["sub1", "sub2"], ["root.txt"]),
            ("/test/dir/sub1", [], ["sub1_file.txt"]),
            ("/test/dir/sub2", ["subsub"], ["sub2_file.txt"]),
            ("/test/dir/sub2/subsub", [], ["deep_file.txt"]),
        ]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # When: Creating ZIP archive
        with patch("src.common.utils.os.path.join") as mock_join, patch(
            "src.common.utils.os.path.relpath"
        ) as mock_relpath:
            mock_join.side_effect = [
                "/test/dir/root.txt",
                "/test/dir/sub1/sub1_file.txt",
                "/test/dir/sub2/sub2_file.txt",
                "/test/dir/sub2/subsub/deep_file.txt",
            ]
            mock_relpath.side_effect = [
                "root.txt",
                "sub1/sub1_file.txt",
                "sub2/sub2_file.txt",
                "sub2/subsub/deep_file.txt",
            ]
            create_zip_archive("/test/dir", "/test/nested.zip")

        # Then: Should preserve nested structure
        assert mock_zip.write.call_count == 4
        mock_zip.write.assert_any_call("/test/dir/root.txt", "root.txt")
        mock_zip.write.assert_any_call(
            "/test/dir/sub1/sub1_file.txt", "sub1/sub1_file.txt"
        )
        mock_zip.write.assert_any_call(
            "/test/dir/sub2/sub2_file.txt", "sub2/sub2_file.txt"
        )
        mock_zip.write.assert_any_call(
            "/test/dir/sub2/subsub/deep_file.txt", "sub2/subsub/deep_file.txt"
        )

    @patch("src.common.utils.zipfile.ZipFile")
    @patch("src.common.utils.os.walk")
    def test_given_special_characters_when_creating_zip_then_handles_correctly(
        self, mock_walk, mock_zipfile
    ):
        # Given: Files with special characters
        mock_walk.return_value = [
            (
                "/test/dir",
                [],
                [
                    "file with spaces.txt",
                    "file-with-dashes.txt",
                    "file_with_underscores.txt",
                ],
            ),
        ]
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # When: Creating ZIP archive
        with patch("src.common.utils.os.path.join") as mock_join, patch(
            "src.common.utils.os.path.relpath"
        ) as mock_relpath:
            mock_join.side_effect = [
                "/test/dir/file with spaces.txt",
                "/test/dir/file-with-dashes.txt",
                "/test/dir/file_with_underscores.txt",
            ]
            mock_relpath.side_effect = [
                "file with spaces.txt",
                "file-with-dashes.txt",
                "file_with_underscores.txt",
            ]
            create_zip_archive("/test/dir", "/test/special.zip")

        # Then: Should handle special characters correctly
        assert mock_zip.write.call_count == 3
        mock_zip.write.assert_any_call(
            "/test/dir/file with spaces.txt", "file with spaces.txt"
        )
        mock_zip.write.assert_any_call(
            "/test/dir/file-with-dashes.txt", "file-with-dashes.txt"
        )
        mock_zip.write.assert_any_call(
            "/test/dir/file_with_underscores.txt", "file_with_underscores.txt"
        )
