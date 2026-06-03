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
```

## Architecture

This is a **10-agent hierarchical AI system** built with the Anthropic SDK (Python). The Orchestrator is the single entry point — users never call specialized agents directly.

```
User
 └── Orchestrator  (tool-use agentic loop)
      ├── Planner
      ├── Researcher
      ├── Writer
      ├── Developer   ← has execute_python tool (subprocess sandbox)
      ├── Reviewer
      ├── Analyst
      ├── QA Tester
      ├── Critic
      └── Summarizer
```

### How the Orchestrator works

`agents/orchestrator.py` runs an **agentic loop**: it calls Claude with 9 tool definitions (one per agent). Claude decides which agents to call and in what order, passing results as `tool_result` blocks. The loop exits when `stop_reason == "end_turn"` and Claude synthesizes a final answer. This is the standard Anthropic tool-use pattern.

### Agent design pattern

All agents except `DeveloperAgent` extend `BaseAgent` (`agents/base_agent.py`), which:
- Uses **prompt caching** (`cache_control: ephemeral`) on every system prompt to reduce latency and cost on repeated calls.
- Accepts an optional `context` string (prior agent output) concatenated before the task.

`DeveloperAgent` is standalone — it has its own tool-use loop with an `execute_python` tool that runs code in a subprocess via `tools/code_executor.py`.

### Entry points

| File | Purpose |
|------|---------|
| `main.py` | CLI — interactive loop or single-task via argv |
| `team.py` | `build_team(config)` — assembles all agents into an Orchestrator |
| `config.py` | Dataclass for model names, token limits, verbosity |

### Key conventions

- `Config.agent_model` controls the model for all 9 specialized agents; `Config.orchestrator_model` controls the Orchestrator separately.
- Verbose mode (`Config.verbose = True`) prints each agent dispatch step to stdout so you can trace execution.
- To add a new agent: subclass `BaseAgent`, add an instance to `team.py`'s `agents` dict, and add a `call_<name>` tool definition in `agents/orchestrator.py`'s `AGENT_TOOLS` list and update the Orchestrator's system prompt table.
