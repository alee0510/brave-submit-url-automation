import argparse
import asyncio
from datetime import datetime, timezone

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn

from core.logger import setup_logger, log_to_file
from core.queue_manager import QueueManager
from core.async_worker import AsyncWorker
from core.importer import import_urls
from cli.report import render_status_table
from config import MAX_RETRIES, LOGS_CSV, LOG_FILE

console = Console()
logger = setup_logger(console)


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

    if not urls:
        console.print("[bold cyan]Nothing to process.[/bold cyan]")
        return

    console.print(f"[bold]Processing {len(urls)} URL(s)...[/bold]  (full trace: {LOG_FILE})\n")

    success_count = 0
    fail_count = 0

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,          # same instance as the logger
    ) as progress:
        task = progress.add_task("Submitting", total=len(urls))

        async for url, success, detail in worker.run(urls):
            attempts = queue.get_attempts(url) + 1
            timestamp = _now()

            if success:
                queue.mark_success(url, timestamp)
                log_to_file(LOGS_CSV, url, "success", attempts)
                success_count += 1
                progress.console.print(f"[green]✓[/green] {url}")
            else:
                if attempts >= MAX_RETRIES:
                    queue.mark_failed(url, attempts, timestamp, error=detail or "")
                    log_to_file(LOGS_CSV, url, "failed", attempts)
                    progress.console.print(f"[red]✗[/red] {url}  [dim]— {detail or 'failed'}[/dim]")
                else:
                    queue.mark_retry(url, attempts, timestamp, error=detail or "")
                    log_to_file(LOGS_CSV, url, "retry", attempts)
                    progress.console.print(f"[yellow]↻[/yellow] {url}  [dim]— retrying ({attempts}/{MAX_RETRIES})[/dim]")
                fail_count += 1

            progress.update(task, advance=1)

    console.print(
        f"\n[bold]Done.[/bold]  "
        f"[green]{success_count} succeeded[/green], "
        f"[red]{fail_count} failed/retrying[/red]"
    )


def do_import(file_path):
    queue = QueueManager()
    added, invalid, duplicate = import_urls(queue, file_path)
    logger.info(f"[IMPORT] added={added} invalid={invalid} duplicate={duplicate} from {file_path}")
    console.print(f"Imported [green]{added}[/green] new URL(s). Skipped {duplicate} duplicate(s), {invalid} invalid.")


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