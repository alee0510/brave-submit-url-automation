import logging
import csv
import os
from datetime import datetime, timezone
from rich.logging import RichHandler
from config import LOG_FILE


def setup_logger(console=None):
    logger = logging.getLogger("brave_submitter")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    console_handler = RichHandler(
        console=console, # shares the same Console as Progress
        level=logging.WARNING,
        show_time=False,
        show_path=False,
        markup=True,
        rich_tracebacks=False,
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def log_to_file(path, url, status, attempt, error=None):
    file_exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "url", "status", "attempt", "error"])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(), url, status, attempt, error or ""
        ])