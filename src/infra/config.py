import logging
import os

logger = logging.getLogger(__name__)


def get_config_parameter(name: str, default: str = None) -> str:
    """
    Retrieves a configuration parameter from environment variables.

    Args:
        name (str): The name of the environment variable.
        default (str): Default value to return if the environment variable is not set.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set and no default is provided.
    """
    value = os.environ.get(name, default)

    if value is None:
        logger.error(
            f"Environment variable '{name}' is not set and no default provided"
        )
        raise ValueError(f"Environment variable '{name}' is required but not set")

    logger.info(f"Retrieved environment variable: {name}, value: {value}")
    return value
