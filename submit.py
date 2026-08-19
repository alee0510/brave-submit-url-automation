import argparse
import asyncio
from datetime import datetime, timezone

from logger import setup_logger, log_to_file
from queue_manager import QueueManager
from async_worker import AsyncWorker
from config import MAX_RETRIES, LOGS_CSV

logger = setup_logger()

def _now():
    return datetime.now(timezone.utc).isoformat()

async def run(mode):
    queue = QueueManager()
    worker = AsyncWorker(logger)

    if mode == "run":
        urls = queue.get_pending()
    elif mode == "resume":
        urls = queue.get_pending()
    elif mode == "retry-failed":
        urls = queue.get_failed()
    else:
        return

    logger.info(f"Processing {len(urls)} URLs...")

    async for url, success in worker.run(urls):
        attempts = queue.get_attempts(url) + 1
        timestamp = _now()

        if success:
            queue.mark_success(url, timestamp)
            log_to_file(LOGS_CSV, url, "success", attempts)
        else:
            if attempts >= MAX_RETRIES:
                queue.mark_failed(url, attempts, timestamp)
                log_to_file(LOGS_CSV, url, "failed", attempts)
            else:
                queue.mark_retry(url, attempts, timestamp)
                log_to_file(LOGS_CSV, url, "retry", attempts)

def status():
    queue = QueueManager()
    total = len(queue.rows)
    success = sum(1 for r in queue.rows.values() if r["status"] == "success")
    failed = sum(1 for r in queue.rows.values() if r["status"] == "failed")
    retry = sum(1 for r in queue.rows.values() if r["status"] == "retry")
    pending = total - success - failed - retry

    print(f"""Total: {total} | Pending: {pending} | Success: {success} | Retrying: {retry} | Failed: {failed}""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "resume", "status", "retry-failed"])

    args = parser.parse_args()

    if args.command == "status":
        status()
    else:
        asyncio.run(run(args.command))