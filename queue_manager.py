import csv
import os
from config import URLS_CSV

FIELDNAMES = ["url", "status", "attempts", "last_attempt_at", "submitted_at", "last_error"]

class QueueManager:
    def __init__(self):
        self.rows = self._load()

    def _load(self):
        if not os.path.exists(URLS_CSV):
            return {}
        with open(URLS_CSV, "r", newline="", encoding="utf-8") as f:
            return {r["url"]: r for r in csv.DictReader(f)}

    def save(self):
        os.makedirs(os.path.dirname(URLS_CSV), exist_ok=True)
        tmp_file = URLS_CSV + ".tmp"
        with open(tmp_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(self.rows.values())
        os.replace(tmp_file, URLS_CSV)  # atomic, same safety as before

    def add_url(self, url):
        """New: lets you append a fresh URL as a pending row instead of editing a .txt file."""
        if url not in self.rows:
            self.rows[url] = {
                "url": url, "status": "pending", "attempts": "0",
                "last_attempt_at": "", "submitted_at": "", "last_error": ""
            }
            self.save()

    def get_pending(self):
        return [u for u, r in self.rows.items() if r["status"] not in ("success",)]

    def get_failed(self):
        return [u for u, r in self.rows.items() if r["status"] == "failed"]

    def get_attempts(self, url):
        return int(self.rows.get(url, {}).get("attempts", 0))

    def _update(self, url, status, attempts, timestamp, error="", submitted=False):
        self.rows.setdefault(url, {"url": url})
        self.rows[url].update({
            "status": status,
            "attempts": str(attempts),
            "last_attempt_at": timestamp,
            "last_error": error,
        })
        if submitted:
            self.rows[url]["submitted_at"] = timestamp
        self.save()

    def mark_success(self, url, timestamp):
        self._update(url, "success", 1, timestamp, submitted=True)

    def mark_retry(self, url, attempts, timestamp, error=""):
        self._update(url, "retry", attempts, timestamp, error=error)

    def mark_failed(self, url, attempts, timestamp, error=""):
        self._update(url, "failed", attempts, timestamp, error=error)