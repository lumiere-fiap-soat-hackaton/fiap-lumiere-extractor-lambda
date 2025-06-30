import logging
import boto3
import os
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize clients outside the handler for reuse on warm starts
ssm_client = boto3.client("ssm")

# Cache for storing parameters to avoid repeated API calls
_parameter_cache = {}


def init():
    """
    Initializes the module by setting up the SSM client.
    This function is called once when the Lambda container is initialized.
    """
    logger.info("SSM client initialized successfully.")
    os.environ["NOTIFICATION_QUEUE_URL"] = get_config_parameter(
        "NOTIFICATION_QUEUE_URL", with_decryption=False
    )
    os.environ["BUCKET_NAME"] = get_config_parameter(
        "BUCKET_NAME", with_decryption=False
    )


def get_config_parameter(name: str, with_decryption: bool = False) -> str:
    """
    Retrieves a configuration parameter from AWS SSM Parameter Store.
    Caches the parameter value to reduce latency on subsequent calls.

    Args:
        name (str): The name of the parameter.
        with_decryption (bool): Set to True for SecureString parameters.

    Returns:
        str: The value of the parameter.

    Raises:
        ClientError: If the parameter cannot be retrieved.
    """
    if name in _parameter_cache:
        logger.info(f"Returning cached value for parameter: {name}")
        return _parameter_cache[name]

    try:
        logger.info(f"Fetching parameter '{name}' from SSM Parameter Store...")
        response = ssm_client.get_parameter(Name=name, WithDecryption=with_decryption)
        value = response["Parameter"]["Value"]

        # Cache the value for future invocations
        _parameter_cache[name] = value
        logger.info(f"Successfully fetched and cached parameter: {name}")

        return value
    except ClientError as e:
        logger.error(f"Failed to retrieve parameter '{name}': {e}")
        raise
