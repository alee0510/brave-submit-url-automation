# Brave URL Submitter Automation

An automated URL submission tool for [Brave Search](https://search.brave.com/submit-url) powered by Playwright. Designed for bulk indexing submissions, featuring automated Proof-of-Work (PoW) captcha handling, rich CLI status tracking, configurable rate-limiting/cooldown backoffs, and Docker container support with Xvfb virtual display.

---

## Key Features

- **Automated Submission & PoW Handling**: Detects input fields, enters URLs with human-like typing simulation, and waits for PoW verification to enable the submission button automatically.
- **Configurable Execution Modes**:
  - `HEADLESS`: Toggle visible browser window vs background execution.
  - `FAST_MODE`: Toggle human-like randomized typing and delay pauses.
- **Queue & Data Persistence**: CSV-backed state tracking preserving URL statuses (`pending`, `success`, `retry`, `failed`), timestamps, attempt counters, and error traces.
- **Data Import**: Supports bulk URL loading from `.csv` and `.xlsx` files with deduplication and URL validation.
- **Rich Status Report**: Terminal-rendered status table powered by `rich`.
- **Docker Ready**: Pre-built Docker container setup equipped with Xvfb for seamless non-headless execution inside headless environments.

---

## Requirements

### Non-Docker Environment
- **Python**: 3.14+ (or Python 3.10+ with standard venv/uv)
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- **Browser Dependencies**: Playwright Chromium browser

### Docker Environment
- **Docker Engine**: 20.10+
- **Docker Compose**: v2+

---

## Project Structure

```
brave-submit/
├── config.py           # Configuration parameters (cooldowns, paths, flags)
├── submit.py           # Main CLI entrypoint (run, resume, retry-failed, status, import)
├── cli/                # Terminal output & status reporting modules
├── core/               # Async Playwright worker, queue manager, and URL importer
├── data/               # Persistent data store (urls.csv, logs.csv, run.log)
├── docker/             # Dockerfile & docker-compose.yaml configurations
├── errors/             # Error DOM debug snapshots
├── imports/            # Directory for input URL files (.csv / .xlsx)
└── profile/            # Persistent browser context profile
```

---

## Installation & Setup

### Option A: Non-Docker Setup (Local Python)

1. **Clone or Navigate to the Workspace**:
   ```bash
   cd /path/to/brave-submit
   ```

2. **Install Dependencies**:
   Using `uv`:
   ```bash
   uv sync
   ```
   Or using standard `venv` + `pip`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   playwright install chromium
   ```

---

### Option B: Docker Setup

1. **Build the Docker Image**:
   ```bash
   docker compose -f docker/docker-compose.yaml build
   ```

---

## Usage Guide

### 1. Importing URL Data

Place your `.csv` or `.xlsx` file inside the `imports/` directory (or specify any valid file path). The importer extracts valid URLs from the first column, ignores headers if present, and skips duplicates.

**Non-Docker**:
```bash
uv run submit.py import --file imports/urls.csv
# or
python submit.py import --file imports/urls.csv
```

**Docker**:
```bash
docker compose -f docker/docker-compose.yaml run --rm brave-submitter import --file imports/urls.csv
```

---

### 2. Environment Variables & Toggles

Configure execution using environment flags:

| Variable | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `HEADLESS` | `true` \| `false` | `false` | When `false`, launches a visible browser (or Xvfb display in Docker). |
| `FAST_MODE` | `true` \| `false` | `false` | When `true`, disables human-like delays for faster execution. |

---

### 3. Running Submission Automation

#### Command Modes

- **`run`**: Process pending/unsubmitted URLs.
- **`resume`**: Resume processing from the last state in `data/urls.csv`.
- **`retry-failed`**: Re-attempt only URLs marked as `failed` (exceeded `MAX_RETRIES`).

#### Non-Docker Examples

```bash
# Default run (Headful with human typing delays)
uv run submit.py run

# Headless & Fast Mode
HEADLESS=true FAST_MODE=true uv run submit.py run

# Resume pending queue
uv run submit.py resume

# Retry failed URLs
uv run submit.py retry-failed
```

#### Docker Examples

```bash
# Default run (HEADLESS=false using container Xvfb virtual framebuffer)
docker compose -f docker/docker-compose.yaml run --rm brave-submitter run

# Headless mode run inside Docker
HEADLESS=true docker compose -f docker/docker-compose.yaml run --rm brave-submitter run

# Resume pending URLs in Docker
docker compose -f docker/docker-compose.yaml run --rm brave-submitter resume

# Retry failed URLs in Docker
docker compose -f docker/docker-compose.yaml run --rm brave-submitter retry-failed
```

---

### 4. Viewing Status Report

Generate a formatted table summarizing the status of all imported URLs along with total execution statistics.

**Non-Docker**:
```bash
uv run submit.py status
# or
python submit.py status
```

**Docker**:
```bash
docker compose -f docker/docker-compose.yaml run --rm brave-submitter status
```

**Sample Output**:
```
                      Brave URL Submission Status                       
┌───────────────────────────────────────┬─────────┬──────────┬──────────────────────┬────────────┐
│ URL                                   │ Status  │ Attempts │ Last Attempt         │ Last Error │
├───────────────────────────────────────┼─────────┼──────────┼──────────────────────┼────────────┤
│ https://example.com                   │ success │        1 │ 2026-08-20T10:15:00Z │ -          │
│ https://developer.mozilla.org         │ success │        1 │ 2026-08-20T10:15:20Z │ -          │
│ http://invalid-host.com               │ failed  │        3 │ 2026-08-20T10:16:00Z │ Invalid URL│
└───────────────────────────────────────┴─────────┴──────────┴──────────────────────┴────────────┘

Total: 3  (success: 2 | failed: 1)
```

---

## Logs & Debugging

- **State File**: `data/urls.csv` holds queue state and history.
- **Trace Logs**: `data/run.log` records detailed execution logs and backoff timers.
- **Attempt History**: `data/logs.csv` records raw log events per URL.
- **DOM Snapshots**: On timeout or UI errors, HTML debug snapshots are dumped to `errors/debug_*.html`.
