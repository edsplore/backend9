import logging
import os
from datetime import datetime


class Logger:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Create logs directory if it doesn't exist
            log_dir = "/tmp/logs/everai"
            os.makedirs(log_dir, exist_ok=True)

            # Build a date-based log filename, e.g. application_2025-04-15.log
            current_date = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(log_dir, f"application_{current_date}.log")

            # Create a consistent formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '[%(filename)s:%(lineno)d] - %(message)s')

            # Basic file handler that writes to our date-based filename
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)

            # Console handler for seeing logs in stdout
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)

            # Configure the root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

            # Mark that we've initialized
            self._initialized = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        # Ensure logger is initialized before returning the named logger
        Logger()
        return logging.getLogger(name)
