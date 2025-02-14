import logging
import logging.config
import traceback
from functools import wraps
from typing import Callable, Any
from .config import Config

# Configure logging based on settings from Config
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)

def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the specified name"""
    return logging.getLogger(name)

def log_exception(logger: logging.Logger) -> Callable:
    """Decorator to log exceptions with stack trace"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {str(e)}\n"
                    f"Stack trace: {traceback.format_exc()}"
                )
                raise
        return wrapper
    return decorator

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Sets up a logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    # Create formatters and handlers
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger