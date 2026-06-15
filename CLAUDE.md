# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in API key
cp .env.example .env

# Run interactive session
python main.py

# Run with a single task
python main.py "Write a Python function to parse CSV files and summarize the data"

# Chat mode (remembers history across turns)
python main.py --chat

# Save all results to output/
python main.py --save

# Batch mode (tasks from file, one per line)
python main.py --file tasks.txt

# Quiet mode (no dispatch logs) + custom model
python main.py --quiet --model claude-opus-4-8

# Show all flags
python main.py --help

# Web UI (browser interface)
uvicorn app:app --reload --port 8000

# Run tests (no API key required)
pytest tests/ -v

# Convenience shortcuts
make run      # python main.py
make web      # uvicorn app:app --reload
make test     # pytest tests/ -v
make chat     # python main.py --chat
```

## Architecture

This is a **10-agent hierarchical AI system** built with the Anthropic SDK (Python). The Orchestrator is the single entry point — users never call specialized agents directly.

```
User
 └── Orchestrator  (tool-use agentic loop, parallel dispatch, persistent memory)
      ├── Planner
      ├── Researcher  ← web_search + fetch_webpage tools
      ├── Writer      ← write_file tool
      ├── Developer   ← execute_python + file tools + run_shell
      ├── Reviewer
      ├── Analyst
      ├── QA Tester
      ├── Critic
      └── Summarizer
```

### How the Orchestrator works

`agents/orchestrator.py` runs an **agentic loop**: it calls Claude with 12 tool definitions (9 agents + 3 memory tools). Claude decides which agents to call and in what order, passing results as `tool_result` blocks. The loop exits when `stop_reason == "end_turn"`. When Claude issues multiple tool calls in the same response, the Orchestrator runs them **in parallel** via `ThreadPoolExecutor`.

### Agent design pattern

- **`BaseAgent`** (`agents/base_agent.py`) — simple single-call agents. Extend this for agents that don't need tools. Includes retry logic and cost tracking.
- **`ToolAgent`** (`agents/tool_agent.py`) — extends `BaseAgent` with an inner tool-use loop. Used by `ResearcherAgent`, `WriterAgent`, and `DeveloperAgent`. Override `_dispatch_tool(name, input)` to handle tool calls.

All agents use **prompt caching** (`cache_control: ephemeral`) on system prompts.

### Entry points

| File | Purpose |
|------|---------|
| `main.py` | CLI — interactive, single-task, batch, and chat modes |
| `app.py` | FastAPI web server — `uvicorn app:app` |
| `team.py` | `build_team(config, memory)` — assembles all agents into an Orchestrator |
| `config.py` | Dataclass for models, verbosity, history, save, cost display |

### Tools available to agents

| Tool | File | Used by |
|------|------|---------|
| `execute_python` | `tools/code_executor.py` | Developer |
| `read_file`, `write_file`, `append_file`, `list_directory` | `tools/file_tools.py` | Developer, Writer |
| `web_search`, `fetch_webpage` | `tools/web_tools.py` | Researcher |
| `run_shell` | `tools/shell_tools.py` | Developer |

### Orchestrator memory tools

The Orchestrator also has `save_memory`, `recall_memory`, and `list_memories` tools backed by `memory/store.py` (JSON file at `memory/memories.json`). The Orchestrator can save facts, user preferences, and project context that persist across sessions.

### Utilities

| Module | Purpose |
|--------|---------|
| `utils/cost.py` | Token usage + estimated USD cost tracker (singleton via `get_tracker()`) |
| `utils/logger.py` | Saves session Q&A to `output/session_<timestamp>.md` |
| `utils/display.py` | Rich console + styled helpers (`print_result`, `print_cost`, `BANNER`) |
| `memory/store.py` | `MemoryStore` — JSON-backed key-value persistence |

### Key conventions

- `Config.agent_model` controls all 9 specialized agents; `Config.orchestrator_model` controls the Orchestrator.
- `Config.maintain_history = True` enables chat mode — the Orchestrator retains conversation across `run()` calls.
- To add a new agent: see `SKILL.md` for the complete 5-step checklist.
- Verbose mode prints each dispatch step; uses Rich styled output via `utils/display.console`.
- `team.last_trace` returns the ordered list of agent calls made during the last `run()`.
