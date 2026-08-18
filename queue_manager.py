import json
import os
from config import INPUT_FILE, PROGRESS_FILE

class QueueManager:
    def __init__(self):
        self.urls = self._load_urls()
        self.progress = self._load_progress()

    def _load_urls(self):
        with open(INPUT_FILE, "r") as f:
            return [u.strip() for u in f if u.strip()]

    def _load_progress(self):
        if not os.path.exists(PROGRESS_FILE):
            return {}
        try:
            with open(PROGRESS_FILE, "r") as f:
                content = f.read().strip()
                # empty file → treat as fresh state
                if not content:
                    return {}
                return json.loads(content)
        except Exception:
            # corrupted JSON → reset safely
            return {}

    def save(self):
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        tmp_file = PROGRESS_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(self.progress, f, indent=2)
        os.replace(tmp_file, PROGRESS_FILE)

    def get_pending(self):
        return [
            u for u in self.urls
            if self.progress.get(u, {}).get("status") != "success"
        ]

    def get_failed(self):
        return [
            u for u, v in self.progress.items()
            if v.get("status") == "failed"
        ]

    def mark_success(self, url):
        self.progress[url] = {"status": "success", "attempts": 1}
        self.save()

    def mark_retry(self, url, attempts):
        self.progress[url] = {"status": "retry", "attempts": attempts}
        self.save()

    def mark_failed(self, url, attempts):
        self.progress[url] = {"status": "failed", "attempts": attempts}
        self.save()

    def get_attempts(self, url):
        return self.progress.get(url, {}).get("attempts", 0)