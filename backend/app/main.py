from backend.app.core.logging import get_logger, setup_logging


setup_logging()
logger = get_logger(__name__)
logger.info("TEST")