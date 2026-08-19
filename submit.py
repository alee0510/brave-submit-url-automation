import argparse
import asyncio
from datetime import datetime, timezone

from core.logger import setup_logger, log_to_file
from core.queue_manager import QueueManager
from core.async_worker import AsyncWorker
from core.importer import import_urls
from cli.report import render_status_table
from config import MAX_RETRIES, LOGS_CSV

logger = setup_logger()

def _now():
    return datetime.now(timezone.utc).isoformat()

async def run(mode):
    queue = QueueManager()
    worker = AsyncWorker(logger)

    if mode in ("run", "resume"):
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


def do_import(file_path):
    queue = QueueManager()
    added, invalid, duplicate = import_urls(queue, file_path)
    logger.info(f"[IMPORT] added={added} invalid={invalid} duplicate={duplicate} from {file_path}")
    print(f"Imported {added} new URL(s). Skipped {duplicate} duplicate(s), {invalid} invalid.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run")
    subparsers.add_parser("resume")
    subparsers.add_parser("retry-failed")
    subparsers.add_parser("status")

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--file", required=True, help="Path to a .csv or .xlsx file of URLs")

    args = parser.parse_args()

    if args.command == "status":
        render_status_table()
    elif args.command == "import":
        do_import(args.file)
    else:
        asyncio.run(run(args.command))