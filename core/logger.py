import logging
import csv
import os
from datetime import datetime, timezone

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    return logging.getLogger("brave_submitter")

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