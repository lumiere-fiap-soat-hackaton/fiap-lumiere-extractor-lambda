import json
import logging
import boto3
from botocore.exceptions import ClientError
from ..common.utils import format_sqs_message

logger = logging.getLogger(__name__)
sqs_client = boto3.client("sqs")


def send_completion_notification(
    queue_url: str, request_id: str, result_s3_path: str, status: str
) -> None:
    """
    Sends a job completion notification to a specified SQS queue.

    Args:
        queue_url (str): The URL of the notification SQS queue.
        request_id (str): The unique ID of the original request.
        result_s3_path (str): The S3 path of the processed output file.

    Raises:
        ClientError: If the message fails to be sent.
    """
    message_body = format_sqs_message(request_id, result_s3_path, status)

    try:
        logger.info(
            f"Sending completion notification for request ID {request_id} to queue {queue_url}"
        )
        sqs_client.send_message(
            QueueUrl=queue_url, MessageBody=json.dumps(message_body)
        )
        logger.info("Completion notification sent successfully.")
    except ClientError as e:
        logger.error(
            f"Failed to send SQS notification for request ID {request_id}. Error: {e}"
        )
        raise
