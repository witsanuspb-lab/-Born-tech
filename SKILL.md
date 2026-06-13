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

## Adding a New Agent

### Step 1 — Create `agents/<name>.py`

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

Use `DeveloperAgent` (`agents/developer.py`) as the template — it's the only agent with its own inner tool-use loop.

### Pattern for a tool-enabled agent

```python
import anthropic
from typing import Optional

MY_TOOL = {
    "name": "tool_name",
    "description": "What this tool does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What param is"},
        },
        "required": ["param"],
    },
}


class MyAgent:
    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        self.name = "MyAgent"
        self.model = model
        self.verbose = verbose
        self.client = anthropic.Anthropic()

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [{self.name}] {msg}")

    def run(self, task: str, context: Optional[str] = None) -> str:
        content = f"Context:\n{context}\n\nTask:\n{task}" if context else task
        messages = [{"role": "user", "content": content}]

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT,
                          "cache_control": {"type": "ephemeral"}}],
                tools=[MY_TOOL],
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return "".join(b.text for b in response.content if hasattr(b, "text"))

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "tool_name":
                    result = my_tool_implementation(block.input["param"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            messages.append({"role": "user", "content": tool_results})
```

> **Important:** Always handle `stop_reason == "end_turn"` as the exit condition. Never break on a fixed number of iterations.

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
# config.py
@dataclass
class Config:
    api_key: str               # from ANTHROPIC_API_KEY env var
    orchestrator_model: str    # model for Orchestrator (default: claude-sonnet-4-6)
    agent_model: str           # model for all 9 specialized agents (default: claude-sonnet-4-6)
    max_tokens: int            # max output tokens per call (default: 4096)
    verbose: bool              # print dispatch logs to stdout (default: True)
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
  base_agent.py      BaseAgent — all simple agents inherit from this
  orchestrator.py    Orchestrator + AGENT_TOOLS list (edit both when adding agents)
  developer.py       Standalone tool-use agent (template for agents with tools)
  planner.py         }
  researcher.py      }
  writer.py          }  All extend BaseAgent — only SYSTEM_PROMPT differs
  reviewer.py        }
  analyst.py         }
  qa_tester.py       }
  critic.py          }
  summarizer.py      }
tools/
  code_executor.py   subprocess sandbox for Python execution
team.py              build_team(config) — single assembly point
config.py            Config dataclass
main.py              CLI entry point (interactive + single-task argv)
```

---

## Checklist: Adding an Agent

- [ ] `agents/<name>.py` — class extending `BaseAgent`, `SYSTEM_PROMPT` defined
- [ ] `agents/__init__.py` — import added, name in `__all__`
- [ ] `team.py` — agent instance added to `agents` dict with correct key
- [ ] `agents/orchestrator.py` — `AGENT_TOOLS` entry added (`call_<key>`)
- [ ] `agents/orchestrator.py` — team table row added to `SYSTEM_PROMPT`
