#!/usr/bin/env python3
import argparse
import sys
from dotenv import load_dotenv
load_dotenv()

from rich import box
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from config import Config
from team import build_team
from utils.cost import get_tracker, reset_tracker
from utils.display import BANNER, console, print_cost, print_result
from utils.logger import SessionLogger

MODELS = [
    ("claude-opus-4-8",   "$15.00", "$75.00", "Most capable"),
    ("claude-sonnet-4-6", "$3.00",  "$15.00", "Best balance  ← default"),
    ("claude-haiku-4-5",  "$0.25",  "$1.25",  "Fastest / cheapest"),
]

COMMANDS = """
[bold]Commands (interactive mode)[/]
  [cyan]/clear[/]    Clear conversation history
  [cyan]/cost[/]     Show token usage and estimated cost
  [cyan]/memory[/]   List all saved memories
  [cyan]/models[/]   Show available models and pricing
  [cyan]/export[/]   Save current session to output/
  [cyan]/help[/]     Show this message
  [cyan]exit[/]      Quit
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python main.py",
        description="AI Team — 10-agent hierarchical system",
    )
    p.add_argument("task", nargs="*", help="Task to run (omit for interactive mode)")
    p.add_argument("--model",  "-m",  metavar="MODEL", help="Override model for all agents")
    p.add_argument("--orchestrator-model", dest="omodel", metavar="MODEL")
    p.add_argument("--agent-model",        dest="amodel", metavar="MODEL")
    p.add_argument("--chat",   "-c",  action="store_true", help="Chat mode: remember history")
    p.add_argument("--quiet",  "-q",  action="store_true", help="Suppress agent dispatch logs")
    p.add_argument("--save",   "-s",  action="store_true", help="Save results to output/")
    p.add_argument("--no-cost",       action="store_true", help="Hide cost summary")
    p.add_argument("--file",   "-f",  metavar="FILE",  help="Run tasks from a text file (one per line)")
    return p


def run_one(team, task: str, config: Config, logger: SessionLogger | None) -> str:
    reset_tracker()
    console.print(f"\n[dim yellow]⟳  Team working on:[/] {task[:100]}")
    result = team.run(task)
    print_result(result)
    if config.show_cost:
        print_cost(get_tracker())
    if logger:
        path = logger.log(task, result)
        console.print(f"  [dim]Saved → {path}[/]")
    return result


def interactive(team, config: Config, logger: SessionLogger | None) -> None:
    console.print(COMMANDS)
    session_tasks: list[tuple[str, str]] = []

    while True:
        try:
            task = console.input("[cyan]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        if not task:
            continue

        if task.lower() in {"exit", "quit", "q"}:
            console.print("[dim]Goodbye.[/]")
            break

        if task == "/help":
            console.print(COMMANDS)
            continue

        if task == "/cost":
            print_cost(get_tracker())
            continue

        if task == "/clear":
            team.clear_history()
            session_tasks.clear()
            reset_tracker()
            console.print("[dim]History cleared.[/]")
            continue

        if task == "/memory":
            result = team.memory.list_all() if team.memory else "Memory not enabled."
            console.print(Panel(result, title="Memory", border_style="cyan", padding=(0, 2)))
            continue

        if task == "/models":
            t = Table(title="Available Models", box=box.ROUNDED)
            t.add_column("Model ID",     style="bold")
            t.add_column("In $/MTok",    justify="right")
            t.add_column("Out $/MTok",   justify="right")
            t.add_column("Notes",        style="dim")
            for row in MODELS:
                t.add_row(*row)
            console.print(t)
            continue

        if task == "/export":
            if not logger:
                exp = SessionLogger()
                for t_, r_ in session_tasks:
                    exp.log(t_, r_)
                exp.finalize(get_tracker().summary())
                console.print(f"  [cyan]Exported → {exp.path}[/]")
            else:
                console.print(f"  [cyan]Session file: {logger.path}[/]")
            continue

        result = run_one(team, task, config, logger)
        session_tasks.append((task, result))

    if logger:
        logger.finalize(get_tracker().summary())


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = Config()

    if args.model:
        config.orchestrator_model = args.model
        config.agent_model = args.model
    if args.omodel:
        config.orchestrator_model = args.omodel
    if args.amodel:
        config.agent_model = args.amodel
    if args.quiet:
        config.verbose = False
    if args.chat:
        config.maintain_history = True
    if args.save:
        config.save_output = True
    if args.no_cost:
        config.show_cost = False

    if not config.api_key:
        console.print("[bold red]Error:[/] ANTHROPIC_API_KEY is not set.")
        console.print("Copy [cyan].env.example[/] to [cyan].env[/] and add your key.")
        sys.exit(1)

    console.print(BANNER)

    if config.maintain_history:
        console.print("[dim cyan]Chat mode ON — history retained between turns.[/]\n")

    team   = build_team(config)
    logger = SessionLogger() if config.save_output else None

    # ── Batch mode: tasks from file ──────────────────────────────────────────
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                tasks = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        except FileNotFoundError:
            console.print(f"[red]File not found: {args.file}[/]")
            sys.exit(1)

        console.print(f"[dim]Running {len(tasks)} tasks from [cyan]{args.file}[/][/]\n")
        for i, task in enumerate(tasks, 1):
            console.rule(f"[bold]Task {i} / {len(tasks)}")
            run_one(team, task, config, logger)

        if logger:
            logger.finalize(get_tracker().summary())
        return

    # ── Single task from argv ────────────────────────────────────────────────
    if args.task:
        task = " ".join(args.task)
        run_one(team, task, config, logger)
        if logger:
            logger.finalize(get_tracker().summary())
        return

    # ── Interactive mode ─────────────────────────────────────────────────────
    interactive(team, config, logger)


if __name__ == "__main__":
    main()
