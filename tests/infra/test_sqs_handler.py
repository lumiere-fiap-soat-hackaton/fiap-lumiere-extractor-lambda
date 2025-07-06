import pytest
import json
from unittest.mock import patch
from botocore.exceptions import ClientError

from src.infra.sqs_handler import send_completion_notification, sqs_client


class TestSQSHandler:
    """Test class for SQS handler functionality using AWS fixture."""

    def test_given_success_status_when_sending_notification_then_sends_correct_message(
        self, aws_sqs_client
    ):
        # Given: Successful processing completion
        # When: Sending completion notification
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            aws_sqs_client["test_result_s3_path"],
            aws_sqs_client["test_status"],
        )

        # Then: Should send message with correct content
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == aws_sqs_client["test_request_id"]
        assert message_body["result_s3_path"] == aws_sqs_client["test_result_s3_path"]
        assert message_body["status"] == aws_sqs_client["test_status"]

    def test_given_failure_status_when_sending_notification_then_sends_failure_message(
        self, aws_sqs_client
    ):
        # Given: Failed processing completion
        status = "FAILURE"
        result_path = ""

        # When: Sending failure notification
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            result_path,
            status,
        )

        # Then: Should send message with failure status
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == aws_sqs_client["test_request_id"]
        assert message_body["result_s3_path"] == ""
        assert message_body["status"] == "FAILURE"

    def test_given_no_frames_status_when_sending_notification_then_sends_no_frames_message(
        self, aws_sqs_client
    ):
        # Given: Processing completed but no frames extracted
        status = "NO_FRAMES_EXTRACTED"
        result_path = ""

        # When: Sending no frames notification
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            result_path,
            status,
        )

        # Then: Should send message with no frames status
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == aws_sqs_client["test_request_id"]
        assert message_body["result_s3_path"] == ""
        assert message_body["status"] == "NO_FRAMES_EXTRACTED"

    def test_given_nonexistent_queue_when_sending_notification_then_raises_client_error(
        self, aws_sqs_client
    ):
        # Given: Queue that doesn't exist
        nonexistent_queue_url = (
            "https://sqs.us-east-1.amazonaws.com/123456789012/nonexistent-queue"
        )

        # When: Attempting to send notification to nonexistent queue
        # Then: Should raise ClientError
        with pytest.raises(ClientError) as exc_info:
            send_completion_notification(
                nonexistent_queue_url,
                aws_sqs_client["test_request_id"],
                aws_sqs_client["test_result_s3_path"],
                aws_sqs_client["test_status"],
            )

        assert "NonExistentQueue" in exc_info.value.response["Error"]["Code"]

    def test_given_special_characters_when_sending_notification_then_handles_correctly(
        self, aws_sqs_client
    ):
        # Given: Request ID and path with special characters
        request_id = "test-request-with-special-chars-123"
        result_path = "s3://test-bucket/processed/result with spaces.zip"

        # When: Sending notification with special characters
        send_completion_notification(
            aws_sqs_client["queue_url"],
            request_id,
            result_path,
            aws_sqs_client["test_status"],
        )

        # Then: Should handle special characters correctly
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == request_id
        assert message_body["result_s3_path"] == result_path
        assert message_body["status"] == aws_sqs_client["test_status"]

    def test_given_empty_result_path_when_sending_notification_then_handles_correctly(
        self, aws_sqs_client
    ):
        # Given: Empty result path for failure case
        result_path = ""
        status = "FAILURE"

        # When: Sending notification with empty result path
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            result_path,
            status,
        )

        # Then: Should handle empty result path correctly
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == aws_sqs_client["test_request_id"]
        assert message_body["result_s3_path"] == ""
        assert message_body["status"] == "FAILURE"

    def test_given_long_request_id_when_sending_notification_then_handles_correctly(
        self, aws_sqs_client
    ):
        # Given: Very long request ID
        request_id = "a" * 100

        # When: Sending notification with long request ID
        send_completion_notification(
            aws_sqs_client["queue_url"],
            request_id,
            aws_sqs_client["test_result_s3_path"],
            aws_sqs_client["test_status"],
        )

        # Then: Should handle long request ID correctly
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["request_id"] == request_id
        assert len(message_body["request_id"]) == 100

    def test_given_large_message_when_sending_notification_then_handles_correctly(
        self, aws_sqs_client
    ):
        # Given: Large message payload within SQS limits
        long_path = "s3://test-bucket/processed/" + "a" * 200 + ".zip"

        # When: Sending notification with large message
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            long_path,
            aws_sqs_client["test_status"],
        )

        # Then: Should handle large message correctly
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["result_s3_path"] == long_path

    def test_given_message_body_when_sending_notification_then_formats_as_json(
        self, aws_sqs_client
    ):
        # Given: Notification parameters
        # When: Sending notification
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            aws_sqs_client["test_result_s3_path"],
            aws_sqs_client["test_status"],
        )

        # Then: Should format message body as valid JSON
        messages = aws_sqs_client["sqs_client"].receive_message(
            QueueUrl=aws_sqs_client["queue_url"]
        )
        assert "Messages" in messages

        message_body_str = messages["Messages"][0]["Body"]
        assert isinstance(message_body_str, str)

        message_body = json.loads(message_body_str)
        assert isinstance(message_body, dict)
        assert len(message_body) == 3
        assert "request_id" in message_body
        assert "result_s3_path" in message_body
        assert "status" in message_body

    def test_given_sqs_client_when_checking_initialization_then_has_required_methods(
        self, aws_sqs_client
    ):
        # Given: SQS client instance
        # When: Checking client attributes
        # Then: Should have required methods
        assert hasattr(sqs_client, "send_message")
        assert hasattr(sqs_client, "receive_message")
        assert hasattr(sqs_client, "delete_message")

    @patch("src.infra.sqs_handler.logger")
    def test_given_successful_notification_when_logging_then_logs_info_messages(
        self, mock_logger, aws_sqs_client
    ):
        # Given: Successful notification parameters
        # When: Sending notification with logging enabled
        send_completion_notification(
            aws_sqs_client["queue_url"],
            aws_sqs_client["test_request_id"],
            aws_sqs_client["test_result_s3_path"],
            aws_sqs_client["test_status"],
        )

        # Then: Should log appropriate messages
        mock_logger.info.assert_any_call(
            f"Sending completion notification for request ID {aws_sqs_client['test_request_id']} to queue {aws_sqs_client['queue_url']}"
        )
        mock_logger.info.assert_any_call("Completion notification sent successfully.")
