from rich.console import Console
from rich.table import Table

from core.queue_manager import QueueManager

STATUS_STYLES = {
    "success": "green",
    "pending": "cyan",
    "retry": "yellow",
    "failed": "red",
}

def render_status_table():
    queue = QueueManager()
    console = Console()

    table = Table(title="Brave URL Submission Status", show_lines=False)
    table.add_column("URL", overflow="fold")
    table.add_column("Status", justify="center")
    table.add_column("Attempts", justify="right")
    table.add_column("Last Attempt", justify="center")
    table.add_column("Last Error", overflow="fold")

    for row in queue.rows.values():
        status = row.get("status", "")
        style = STATUS_STYLES.get(status, "white")
        table.add_row(
            row.get("url", ""),
            f"[{style}]{status}[/{style}]",
            row.get("attempts", "0"),
            row.get("last_attempt_at", "") or "-",
            row.get("last_error", "") or "-",
        )

    console.print(table)

    counts = {}
    for row in queue.rows.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    summary = " | ".join(f"{k}: {v}" for k, v in counts.items())
    console.print(f"\n[bold]Total: {len(queue.rows)}[/bold]  ({summary})")