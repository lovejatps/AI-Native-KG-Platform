import logging


def get_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Set logger level based on configuration (default INFO)
    from .config import get_settings

    level_name = get_settings().LOG_LEVEL
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    return logger
