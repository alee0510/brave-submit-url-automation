import logging
import json
from datetime import datetime

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    return logging.getLogger("brave_submitter")


def log_to_file(path, url, status, attempt, error=None):
    entry = {
        "url": url,
        "status": status,
        "attempt": attempt,
        "timestamp": datetime.utcnow().isoformat()
    }

    if error:
        entry["error"] = str(error)

    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")
