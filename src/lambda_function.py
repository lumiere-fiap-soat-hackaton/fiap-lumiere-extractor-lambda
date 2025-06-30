import json
import logging
import os

# Import the configuration module
# import infra.config as config

# Import the core application logic
from .services.processing_service import VideoProcessingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#  Initialize the configuration module
# config.init()
NOTIFICATION_QUEUE_URL = os.environ.get("NOTIFICATION_QUEUE_URL")
OUTPUT_BUCKET_NAME = os.environ.get("OUTPUT_BUCKET_NAME")

# Instantiate the service once, allowing it to be reused across warm invocations
processing_svc = VideoProcessingService(OUTPUT_BUCKET_NAME)


def lambda_handler(event: dict, context: object):
    """
    AWS Lambda handler triggered by SQS.
    This function acts as an adapter, translating the SQS event into a
    call to the core application service.
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} messages.")

    for record in event.get("Records", []):
        try:
            # 1. Parse the incoming event to extract the necessary input
            message_body = json.loads(record["body"])
            s3_path = message_body["s3_path"]
            request_id = message_body["request_id"]

            # 2. Invoke the core application logic
            processing_svc.process_video(
                s3_path=s3_path,
                request_id=request_id,
                notification_queue_url=NOTIFICATION_QUEUE_URL,
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
