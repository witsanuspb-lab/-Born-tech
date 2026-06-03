#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from config import Config
from team import build_team

BANNER = """
╔══════════════════════════════════════════════════════╗
║           AI TEAM  —  10-Agent System                ║
║                                                      ║
║  Orchestrator (head)                                 ║
║  ├── Planner      ├── Researcher   ├── Writer        ║
║  ├── Developer    ├── Reviewer     ├── Analyst       ║
║  ├── QA Tester    ├── Critic       └── Summarizer    ║
╚══════════════════════════════════════════════════════╝
"""


def main() -> None:
    config = Config()

    if not config.api_key:
        print("Error: ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and add your key.")
        sys.exit(1)

    print(BANNER)
    team = build_team(config)

    # Single task from CLI argument
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        result = team.run(task)
        print("\n" + "=" * 60)
        print("RESULT")
        print("=" * 60)
        print(result)
        return

    # Interactive loop
    print("Type your task and press Enter. Type 'exit' to quit.\n")
    while True:
        try:
            task = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not task:
            continue
        if task.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        result = team.run(task)
        print("\n" + "=" * 60)
        print("RESULT")
        print("=" * 60)
        print(result)
        print()


if __name__ == "__main__":
    main()
