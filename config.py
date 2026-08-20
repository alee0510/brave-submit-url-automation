import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(BASE_DIR, "profile")   # fresh profile lives inside the project
DATA_DIR = os.path.join(BASE_DIR, "data")
ERRORS_DIR = os.path.join(BASE_DIR, "errors")

URLS_CSV = os.path.join(DATA_DIR, "urls.csv")
LOGS_CSV = os.path.join(DATA_DIR, "logs.csv")
LOG_FILE = os.path.join(DATA_DIR, "run.log")   # full verbose trace lives here now

# Target
BASE_URL = "https://search.brave.com/submit-url"

# Retry / backoff
MAX_RETRIES = 3

# Widened to reduce PoW trigger rate on a fresh profile / datacenter IP
COOLDOWN_MIN = 8
COOLDOWN_MAX = 20

# Extra pause every BATCH_SIZE URLs, on top of the per-URL cooldown
BATCH_SIZE = 15
BATCH_PAUSE_MIN = 60
BATCH_PAUSE_MAX = 120

# Captcha / PoW handling
# How long to wait for the PoW challenge to auto-resolve before giving up
# on this attempt. No human fallback — fully unattended.
CAPTCHA_AUTO_TIMEOUT_MS = 180_000  # 3 minutes

# Misc timeouts
SELECTOR_TIMEOUT_MS = 10_000

# Headless toggle
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"