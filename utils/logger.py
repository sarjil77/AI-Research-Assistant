import logging
import os
from datetime import datetime
from pytz import timezone


def create_logger(path, api_cls):
    if path is None:
        path = "logs"

    path = str(path)
    os.makedirs(path, exist_ok=True)

    time_str = datetime.now(
        timezone("Asia/Kolkata")
    ).strftime('%Y-%m-%d-%H-%M')

    log_file = f"{time_str}_{api_cls}.log"
    final_log_file = os.path.join(path, log_file)

    # 🔥 Create named logger (NOT root logger)
    logger = logging.getLogger(api_cls)
    logger.setLevel(logging.INFO)

    # 🚀 Clear existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # ---- File Handler ----
    file_handler = logging.FileHandler(final_log_file)
    file_handler.setLevel(logging.INFO)

    # ---- Console Handler ----
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # ---- Formatter ----
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger