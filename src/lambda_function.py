import json
import logging

# Import the configuration module
# import infra.config as config

# Import the core application logic
from .services.processing_service import VideoProcessingService
from .infra import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Instantiate the service once, allowing it to be reused across warm invocations
processing_svc = VideoProcessingService()


def lambda_handler(event: dict, context: object):
    """
    AWS Lambda handler triggered by SQS.
    This function acts as an adapter, translating the SQS event into a
    call to the core application service.
    """
    logger.info(f"-- Received SQS message {json.dumps(event)}")

    MEDIA_RESULT_QUEUE_NAME = config.get_config_parameter("MEDIA_RESULT_QUEUE_NAME")
    S3_BUCKET_NAME = config.get_config_parameter("S3_BUCKET_NAME")

    for record in event.get("Records", []):
        try:
            logger.info(f"-- Processing Record: {json.dumps(record)}")

            # 1. Parse the incoming event to extract the necessary input
            message_body = json.loads(record["body"])
            s3_path = message_body["sourceFileKey"]
            request_id = message_body["id"]

            # 2. Invoke the core application logic
            processing_svc.process_video(
                s3_path=s3_path,
                request_id=request_id,
                s3_bucket_name=S3_BUCKET_NAME,
                notification_queue_url=MEDIA_RESULT_QUEUE_NAME,
            )

        except (KeyError, TypeError, json.JSONDecodeError) as e:
            # Handle bad message format
            logger.error(
                f"Failed to parse SQS message body: {record.get('body', 'N/A')}. Error: {e}"
            )
            # This message is malformed, re-raising will send it to the DLQ after retries
            raise
        except Exception as e:
            # Handle exceptions from the processing service
            logger.error(
                f"An unhandled exception occurred during processing. Error: {e}",
                exc_info=True,
            )
            # Re-raising the exception signals failure to SQS for retry/DLQ
            raise
