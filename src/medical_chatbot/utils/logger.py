"""Logging configuration for medical chatbot"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "1 week",
) -> None:
    """Setup logger with file and console output

    Args:
        log_file: Path to log file. If None, only console logging is enabled.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rotation: When to rotate log file
        retention: How long to keep old log files
    """
    # Remove default logger
    logger.remove()

    # Add console logger with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file logger if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )

    logger.info(f"Logger initialized with level: {log_level}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")
