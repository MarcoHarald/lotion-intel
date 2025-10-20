"""
Logging configuration using Loguru.
Provides structured logging with daily rotation and retention.
"""
import os
import sys
from loguru import logger
from pathlib import Path
from config.settings import settings


def setup_logging():
    """Configure Loguru logging with structured format and rotation."""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler with daily rotation
    logger.add(
        logs_dir / "monitoring_app_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
        rotation="00:00",  # Daily rotation at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True,
        serialize=False  # Set to True for JSON format if needed
    )
    
    # Error file handler (separate file for errors)
    logger.add(
        logs_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
        rotation="00:00",
        retention="90 days",  # Keep error logs longer
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Collection-specific log file
    logger.add(
        logs_dir / "collection_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message} | {extra}",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        filter=lambda record: "collection" in record["name"].lower()
    )
    
    logger.info("Logging system initialized", extra={"component": "logging", "level": settings.log_level})


def get_logger(name: str = None):
    """Get a logger instance with optional name binding."""
    if name:
        return logger.bind(component=name)
    return logger


# Initialize logging when module is imported
setup_logging()
