import os

BASE_URL = "https://search.brave.com/submit-url"
PROFILE_DIR = "/Users/user/Library/Application Support/Automation Profile"

MAX_RETRIES = 3
TIMEOUT = 30000

COOLDOWN_MIN = 3
COOLDOWN_MAX = 8

URLS_CSV = "data/urls.csv"
LOGS_CSV = "data/logs.csv"

# NEW: test toggles, both default to current behavior (off)
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"