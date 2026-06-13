#!/usr/bin/env python3
import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from config import Config
from team import build_team
from utils.cost import get_tracker, reset_tracker
from utils.logger import SessionLogger

BANNER = """
╔══════════════════════════════════════════════════════════╗
║              AI TEAM  —  10-Agent System                 ║
╠══════════════════════════════════════════════════════════╣
║  Orchestrator (head)                                     ║
║  ├─ Planner      ├─ Researcher*  ├─ Writer*             ║
║  ├─ Developer*   ├─ Reviewer     ├─ Analyst             ║
║  ├─ QA Tester    ├─ Critic       └─ Summarizer          ║
║                                                          ║
║  * = has tools (web search / file I/O / code execution) ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands (interactive mode):
  /clear    Clear conversation history (chat mode)
  /cost     Show current token usage and cost
  /history  Show tasks completed this session
  /save     Toggle auto-saving results
  /help     Show this message
  exit      Quit
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python main.py",
        description="AI Team — 10-agent hierarchical system powered by Claude",
    )
    p.add_argument("task", nargs="*", help="Task to run (omit for interactive mode)")
    p.add_argument(
        "--model", "-m",
        default=None,
        metavar="MODEL",
        help="Override model for all agents (e.g. claude-opus-4-8)",
    )
    p.add_argument(
        "--orchestrator-model", "-om",
        default=None,
        dest="orchestrator_model",
        metavar="MODEL",
        help="Override Orchestrator model only",
    )
    p.add_argument(
        "--agent-model", "-am",
        default=None,
        dest="agent_model",
        metavar="MODEL",
        help="Override agent model only",
    )
    p.add_argument(
        "--chat", "-c",
        action="store_true",
        help="Enable chat mode: remember conversation history across turns",
    )
    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress per-agent dispatch logs",
    )
    p.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save all results to output/ as a markdown file",
    )
    p.add_argument(
        "--no-cost",
        action="store_true",
        help="Hide token usage and cost summary",
    )
    return p


def run_task(team, task: str, config: Config, logger: SessionLogger | None) -> str:
    reset_tracker()
    result = team.run(task)

    if logger:
        path = logger.log(task, result)
        if config.verbose:
            print(f"\n[Saved → {path}]")

    if config.show_cost:
        print(f"\n  {get_tracker().summary()}")

    return result


def interactive(team, config: Config, logger: SessionLogger | None) -> None:
    session_tasks: list[tuple[str, str]] = []

    print(HELP_TEXT)
    print("Type your task and press Enter.\n")

    while True:
        try:
            task = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not task:
            continue

        # Built-in commands
        if task.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        if task == "/help":
            print(HELP_TEXT)
            continue

        if task == "/cost":
            print(f"  {get_tracker().summary()}")
            continue

        if task == "/clear":
            team.clear_history()
            session_tasks.clear()
            reset_tracker()
            print("  History cleared.")
            continue

        if task == "/history":
            if not session_tasks:
                print("  No tasks yet.")
            else:
                for i, (t, _) in enumerate(session_tasks, 1):
                    print(f"  {i}. {t[:80]}")
            continue

        if task == "/save":
            config.save_output = not config.save_output
            state = "ON" if config.save_output else "OFF"
            if config.save_output and logger is None:
                logger = SessionLogger()
            print(f"  Auto-save: {state}")
            continue

        result = run_task(team, task, config, logger)
        session_tasks.append((task, result))

        print("\n" + "─" * 60)
        print(result)
        print("─" * 60 + "\n")

    if logger:
        logger.finalize(get_tracker().summary())


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = Config()

    # Apply CLI overrides
    if args.model:
        config.orchestrator_model = args.model
        config.agent_model = args.model
    if args.orchestrator_model:
        config.orchestrator_model = args.orchestrator_model
    if args.agent_model:
        config.agent_model = args.agent_model
    if args.quiet:
        config.verbose = False
    if args.chat:
        config.maintain_history = True
    if args.save:
        config.save_output = True
    if args.no_cost:
        config.show_cost = False

    if not config.api_key:
        print("Error: ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and fill in your key.")
        sys.exit(1)

    print(BANNER)

    if config.maintain_history:
        print("  [Chat mode ON — conversation history is retained between turns]\n")

    team = build_team(config)
    logger = SessionLogger() if config.save_output else None

    if args.task:
        # Single-task mode
        task = " ".join(args.task)
        result = run_task(team, task, config, logger)
        print("\n" + "=" * 60)
        print("RESULT")
        print("=" * 60)
        print(result)
        if logger:
            logger.finalize(get_tracker().summary())
    else:
        # Interactive mode
        interactive(team, config, logger)


if __name__ == "__main__":
    main()
