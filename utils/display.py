from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console(highlight=False)

AGENT_STYLES: dict[str, str] = {
    "Orchestrator": "bold cyan",
    "Planner":      "bold blue",
    "Researcher":   "bold green",
    "Writer":       "bold yellow",
    "Developer":    "bold magenta",
    "Reviewer":     "bold red",
    "Analyst":      "bright_cyan",
    "QA Tester":    "bright_yellow",
    "Critic":       "bright_red",
    "Summarizer":   "bright_green",
}


def print_result(result: str) -> None:
    console.print()
    console.print(Panel(result, title="[bold green]Result[/]", border_style="green", padding=(1, 2)))


def print_cost(tracker) -> None:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column(style="dim", width=14)
    table.add_column()
    table.add_row("Calls",      str(tracker.calls))
    table.add_row("Tokens in",  f"{tracker.input_tokens:,}")
    table.add_row("Tokens out", f"{tracker.output_tokens:,}")
    cache_pct = round(tracker.cache_read_tokens / max(tracker.input_tokens, 1) * 100)
    table.add_row("Cache hits", f"{tracker.cache_read_tokens:,}  [dim]({cache_pct}%)[/]")
    table.add_row("Est. cost",  f"[green]${tracker.estimated_cost():.4f}[/]")
    console.print(table)


BANNER = Panel(
    "[bold cyan]AI TEAM[/] — 10-Agent System\n\n"
    "Orchestrator [dim](head)[/]\n"
    "├─ [green]Researcher✦[/]   ├─ [yellow]Writer✦[/]   ├─ [magenta]Developer✦[/]\n"
    "├─ [blue]Planner[/]       ├─ [red]Reviewer[/]   ├─ [bright_cyan]Analyst[/]\n"
    "├─ [bright_yellow]QA Tester[/]     ├─ [bright_red]Critic[/]     └─ [bright_green]Summarizer[/]\n\n"
    "[dim]✦ = has tools (web search · file I/O · code execution)[/]",
    border_style="cyan",
    title="[bold]AI Team[/]",
    subtitle="[dim]powered by Anthropic Claude[/]",
)
