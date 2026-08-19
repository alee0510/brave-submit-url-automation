import argparse
import asyncio

from logger import setup_logger, log_to_file
from queue_manager import QueueManager
from async_worker import AsyncWorker
from config import MAX_RETRIES, SUCCESS_LOG, FAILED_LOG

logger = setup_logger()

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

        if success:
            queue.mark_success(url)
            log_to_file(SUCCESS_LOG, url, "success", attempts)
        else:
            if attempts >= MAX_RETRIES:
                queue.mark_failed(url, attempts)
                log_to_file(FAILED_LOG, url, "failed", attempts)
            else:
                queue.mark_retry(url, attempts)
                log_to_file(FAILED_LOG, url, "retry", attempts)

def status():
    queue = QueueManager()
    total = len(queue.urls)
    success = sum(1 for v in queue.progress.values() if v["status"] == "success")
    failed = sum(1 for v in queue.progress.values() if v["status"] == "failed")
    retry = sum(1 for v in queue.progress.values() if v["status"] == "retry")

    print(f"""Total: {total} | Success: {success} | Retrying: {retry} | Failed: {failed}""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "resume", "status", "retry-failed"])

    args = parser.parse_args()

    if args.command == "status":
        status()
    else:
        asyncio.run(run(args.command))