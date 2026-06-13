# SKILL.md — AI Team Knowledge Base

Reference document for Claude Code working in this repository.
Read this before making any changes to the agent system.

---

## Mental Model

The system has **two layers**:

1. **Orchestrator loop** — Claude (with 9 tools) decides which agents to call, in what order, and how to chain their results. Loop exits when `stop_reason == "end_turn"`.
2. **Agent execution** — each agent is a single `messages.create` call (or its own inner tool-use loop for `DeveloperAgent`).

The Orchestrator never hardcodes a workflow. Claude reasons about the task and constructs the pipeline dynamically each time.

---

## Two Agent Base Classes

| Base class | When to use | Inner loop? |
|-----------|-------------|-------------|
| `BaseAgent` | Agent needs no tools — single Claude call per task | No |
| `ToolAgent` | Agent needs tools (web search, file I/O, code execution, etc.) | Yes — loops until `end_turn` |

`ToolAgent` extends `BaseAgent`. Override `_dispatch_tool(name, input) -> str` to handle each tool call. See `agents/researcher.py`, `agents/writer.py`, `agents/developer.py` for examples.

---

## Adding a New Agent

### Step 1 — Create `agents/<name>.py`

**Simple agent (no tools):**

```python
from .base_agent import BaseAgent

SYSTEM_PROMPT = """You are the <Name> — a <specialty> specialist on a 10-agent AI team.

Your job is to <primary responsibility>. When given a task:
1. <First thing to do>
2. <Second thing to do>
3. <Output format or quality bar>

<One sentence on what NOT to do or a key constraint>."""


class <Name>Agent(BaseAgent):
    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        super().__init__(
            name="<Name>",
            role="<One-line role description>",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            verbose=verbose,
        )
```

**Agent with tools** — extend `ToolAgent` instead:

```python
from .tool_agent import ToolAgent
from tools.my_tool import my_function

class MyAgent(ToolAgent):
    def __init__(self, model="claude-sonnet-4-6", verbose=True):
        super().__init__(
            name="MyAgent", role="...", system_prompt=SYSTEM_PROMPT,
            tools=[MY_TOOL_DEFINITION], model=model, verbose=verbose,
        )

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "my_tool":
            return my_function(tool_input["param"])
        return f"Unknown tool: {tool_name}"
```

### Step 2 — Register in `agents/__init__.py`

```python
from .<name> import <Name>Agent
# add to __all__ list
```

### Step 3 — Add to `team.py`

```python
agents = {
    ...
    "<key>": <Name>Agent(model=m, verbose=v),   # key is what Orchestrator uses
}
```

### Step 4 — Add tool to `agents/orchestrator.py`

In `AGENT_TOOLS` list:

```python
{
    "name": "call_<key>",
    "description": "<One sentence — what does calling this agent accomplish?>",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The specific task for this agent"},
            "context": {"type": "string", "description": "Relevant prior results or background"},
        },
        "required": ["task"],
    },
},
```

### Step 5 — Update Orchestrator system prompt table

Add a row to the team table in `SYSTEM_PROMPT` inside `agents/orchestrator.py`:

```
| <key>       | <Short specialty description>                          |
```

---

## Adding Tools to an Agent

Extend `ToolAgent` — it handles the inner loop automatically. You only implement `_dispatch_tool`.

```python
# 1. Define the tool schema
MY_TOOL = {
    "name": "my_tool",
    "description": "One-sentence description for Claude",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What param is"},
        },
        "required": ["param"],
    },
}

# 2. Extend ToolAgent
class MyAgent(ToolAgent):
    def __init__(self, model="claude-sonnet-4-6", verbose=True):
        super().__init__(
            name="...", role="...", system_prompt=SYSTEM_PROMPT,
            tools=[MY_TOOL], model=model, verbose=verbose,
        )

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "my_tool":
            return str(my_function(tool_input["param"]))
        return f"Unknown tool: {tool_name}"
```

> The `ToolAgent.run()` loop exits on `stop_reason == "end_turn"`. Cost tracking is automatic.

---

## System Prompt Guidelines

All agent system prompts follow this structure — keep this consistent:

```
You are the <Name> — a <specialty> specialist on a 10-agent AI team.

Your job is to <primary responsibility>. When given a task:
1. <numbered steps — what to do in order>
...

<Final constraint sentence — what to avoid or a quality bar.>
```

**Rules:**
- Open with identity: `You are the <Name> — a <specialty> specialist on a 10-agent AI team.`
- Use numbered steps for the core workflow — Claude follows lists reliably.
- End with a single hard constraint or quality bar.
- Do NOT add meta-instructions like "be helpful" or "be professional" — redundant.
- Keep prompts under ~200 words. Long prompts dilute focus.

---

## Prompt Caching

Every `system` parameter uses `cache_control: ephemeral` to cache the system prompt:

```python
system=[
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},   # always include this
    }
]
```

This is applied in both `BaseAgent.run()` and every standalone agent. Do not remove it — it significantly reduces cost and latency on repeated calls to the same agent.

---

## Config Reference

```python
@dataclass
class Config:
    api_key: str               # from ANTHROPIC_API_KEY env var
    orchestrator_model: str    # model for Orchestrator (default: claude-sonnet-4-6)
    agent_model: str           # model for all 9 specialized agents (default: claude-sonnet-4-6)
    max_tokens: int            # max output tokens per call (default: 4096)
    verbose: bool              # print dispatch logs (default: True)
    maintain_history: bool     # chat mode — remember turns (default: False)
    save_output: bool          # auto-save results to output/ (default: False)
    show_cost: bool            # print token + cost summary (default: True)
    max_retries: int           # API retry attempts on rate limit / error (default: 3)
```

**Model selection guide:**

| Scenario | Orchestrator | Agents |
|----------|-------------|--------|
| Default (balanced) | `claude-sonnet-4-6` | `claude-sonnet-4-6` |
| Best quality | `claude-opus-4-8` | `claude-sonnet-4-6` |
| Low cost / high speed | `claude-sonnet-4-6` | `claude-haiku-4-5` |
| Fast prototyping | `claude-haiku-4-5` | `claude-haiku-4-5` |

---

## Context Chaining Pattern

The Orchestrator passes results between agents via the `context` parameter. This is how multi-step pipelines work:

```
researcher result → passed as context to writer → writer result → passed as context to reviewer
```

In the Orchestrator tool call, `context` is always a string (previous agent output). Agents prepend it before the task in `BaseAgent.run()`:

```python
content = f"Context:\n{context}\n\nTask:\n{task}" if context else task
```

When building context strings in the Orchestrator tool calls, be explicit:
```
"context": "Research findings:\n" + research_result
```

---

## Code Executor

`tools/code_executor.py` → `execute_python_code(code: str, timeout: int = 30) -> dict`

Returns:
```python
{
    "stdout": str,
    "stderr": str,
    "returncode": int,
    "success": bool,
}
```

Currently used only by `DeveloperAgent`. To give another agent Python execution, import and use the same pattern as `developer.py`.

---

## File Map

```
agents/
  base_agent.py      BaseAgent — simple single-call agents; retry + cost tracking built in
  tool_agent.py      ToolAgent(BaseAgent) — inner tool-use loop; override _dispatch_tool()
  orchestrator.py    Orchestrator + AGENT_TOOLS (edit both when adding agents)
  developer.py       ToolAgent — execute_python, file tools, run_shell
  researcher.py      ToolAgent — web_search, fetch_webpage
  writer.py          ToolAgent — write_file
  planner.py  reviewer.py  analyst.py  qa_tester.py  critic.py  summarizer.py
               └── All extend BaseAgent (no tools)
tools/
  code_executor.py   subprocess Python sandbox
  file_tools.py      read_file, write_file, append_file, list_directory
  web_tools.py       web_search (DuckDuckGo), fetch_webpage
  shell_tools.py     run_shell (blocked: rm, kill, sudo, etc.)
utils/
  cost.py            CostTracker singleton — get_tracker(), reset_tracker()
  logger.py          SessionLogger — saves to output/session_<timestamp>.md
output/              Auto-created; holds session markdown files
team.py              build_team(config) — single assembly point
config.py            Config dataclass
main.py              CLI — flags: --chat, --save, --quiet, --model, --no-cost
```

---

## Parallel Execution

When the Orchestrator's Claude response contains multiple `tool_use` blocks in a single turn, they are dispatched concurrently via `ThreadPoolExecutor`. No code changes needed — this is automatic. Design agent tasks to be independent when possible so Claude can parallelize them.

---

## Cost Tracking

All `BaseAgent.run()` and `ToolAgent.run()` calls automatically register with the singleton `CostTracker`:

```python
from utils.cost import get_tracker, reset_tracker

reset_tracker()          # clear counts before a task
result = team.run(task)
print(get_tracker().summary())   # "Calls: 5 | In: 12,400 | Out: 3,200 | ..."
```

Pricing table is in `utils/cost.py` (`_PRICING`). Update it if models or prices change.

---

## Session Logging

```python
from utils.logger import SessionLogger

logger = SessionLogger("output")   # creates output/session_YYYY-MM-DD_HH-MM-SS.md
logger.log(task, result)           # appends task + result
logger.finalize(cost_summary)      # writes footer with timestamp + cost
```

---

## Checklist: Adding an Agent

- [ ] `agents/<name>.py` — class extending `BaseAgent` or `ToolAgent`, `SYSTEM_PROMPT` defined
- [ ] `agents/__init__.py` — import added, name in `__all__`
- [ ] `team.py` — agent instance in `agents` dict with correct string key
- [ ] `agents/orchestrator.py` — `AGENT_TOOLS` entry added (`call_<key>`)
- [ ] `agents/orchestrator.py` — team table row added to `SYSTEM_PROMPT`
