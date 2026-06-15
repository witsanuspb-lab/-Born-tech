import concurrent.futures
import time
import anthropic
from typing import Any, Optional

SYSTEM_PROMPT = """You are the Orchestrator — the master coordinator of a 10-agent AI team. You receive tasks from users and direct the right agents to accomplish them.

## Your Team

| Agent       | Specialty                                                       |
|-------------|-----------------------------------------------------------------|
| planner     | Breaks goals into structured, step-by-step plans               |
| researcher  | Gathers information via web search and URL fetching            |
| writer      | Crafts polished content and saves documents to disk            |
| developer   | Writes/runs code; reads, writes, and lists files; runs shell   |
| reviewer    | Reviews code/content for bugs and quality issues               |
| analyst     | Analyzes data and produces insights                            |
| qa_tester   | Designs test cases and validates outputs                       |
| critic      | Scores work holistically and recommends improvements           |
| summarizer  | Distills long content into clear, concise summaries            |

## Persistent Memory

You also have access to memory tools that persist across sessions:
- **save_memory(key, value)** — Store important information for future sessions (user name, project goals, preferences)
- **recall_memory(key)** — Retrieve a previously saved value by key
- **list_memories()** — See all keys currently in memory

Use memory proactively: save decisions, user preferences, and project context so future sessions start with full context.

## How to Operate

1. **Check memory first** — if the task references past context, use recall_memory or list_memories.
2. **Analyze** the task — understand scope, type, and expected output.
3. **Sequence** agents appropriately. Simple tasks: 1–2 agents. Complex tasks: chain them.
4. **Pass context** — always include relevant prior results when calling the next agent.
5. **Parallelize** — when multiple independent sub-tasks exist, call those agents simultaneously.
6. **Synthesize** all outputs into a single coherent final answer.
7. **Save to memory** if the task produces something worth remembering long-term.

Never fabricate agent outputs — only use what agents actually return."""

AGENT_TOOLS = [
    {
        "name": "call_planner",
        "description": "Create a detailed step-by-step plan or strategy for a goal.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_researcher",
        "description": "Research and gather information via web search. Returns cited findings.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_writer",
        "description": "Write, create, or edit any written content. Can save to files.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_developer",
        "description": "Write code, run Python, read/write files, and execute shell commands.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_reviewer",
        "description": "Review code or content for bugs, quality issues, and improvements.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_analyst",
        "description": "Analyze data or a situation and produce insights and recommendations.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_qa_tester",
        "description": "Create test cases, validate outputs, and identify gaps or issues.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_critic",
        "description": "Evaluate quality holistically; provide a score and improvement recommendations.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "call_summarizer",
        "description": "Condense lengthy content into a clear, concise summary.",
        "input_schema": {"type": "object", "properties": {
            "task": {"type": "string"}, "context": {"type": "string"},
        }, "required": ["task"]},
    },
    {
        "name": "save_memory",
        "description": "Save a value to persistent memory under a key. Survives across sessions.",
        "input_schema": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Short unique identifier, e.g. 'user_name'"},
            "value": {"type": "string", "description": "The information to remember"},
        }, "required": ["key", "value"]},
    },
    {
        "name": "recall_memory",
        "description": "Retrieve a previously saved value from persistent memory by key.",
        "input_schema": {"type": "object", "properties": {
            "key": {"type": "string"},
        }, "required": ["key"]},
    },
    {
        "name": "list_memories",
        "description": "List all keys and value previews currently in persistent memory.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

_MEMORY_TOOL_NAMES = {"save_memory", "recall_memory", "list_memories"}


class Orchestrator:
    """Hierarchical orchestrator that coordinates a 10-agent team via Claude tool use."""

    def __init__(
        self,
        agents: dict[str, Any],
        model: str = "claude-sonnet-4-6",
        verbose: bool = True,
        maintain_history: bool = False,
        max_retries: int = 3,
        memory=None,
    ):
        self.agents = agents
        self.model = model
        self.verbose = verbose
        self.maintain_history = maintain_history
        self.max_retries = max_retries
        self.memory = memory
        self.client = anthropic.Anthropic()
        self._history: list[dict] = []
        self._trace: list[dict] = []

    def _log(self, message: str) -> None:
        if not self.verbose:
            return
        try:
            from utils.display import console
            console.print(f"\n[Orchestrator] {message}", style="bold cyan")
        except ImportError:
            print(f"\n[Orchestrator] {message}")

    def _handle_memory(self, name: str, inp: dict) -> str:
        if not self.memory:
            return "Memory is not enabled."
        if name == "save_memory":
            return self.memory.save(inp["key"], inp["value"])
        if name == "recall_memory":
            return self.memory.recall(inp["key"])
        if name == "list_memories":
            return self.memory.list_all()
        return "Unknown memory operation."

    def _call_agent(self, agent_key: str, task: str, context: str) -> tuple[str, str]:
        if agent_key not in self.agents:
            return agent_key, f"Agent '{agent_key}' is not available."
        result = self.agents[agent_key].run(task, context if context else None)
        return agent_key, result

    def _process_tool_blocks(self, blocks: list) -> list[dict]:
        from utils.cost import get_tracker

        results: dict[str, str] = {}
        agent_calls: list[tuple] = []  # (block_id, agent_key, task, context)

        for block in blocks:
            if block.type != "tool_use":
                continue

            # Memory tools — handled synchronously (fast)
            if block.name in _MEMORY_TOOL_NAMES:
                result = self._handle_memory(block.name, block.input)
                results[block.id] = result
                self._log(f"Memory [{block.name}] → {result[:60]}")
                self._trace.append({"agent": f"memory:{block.name}", "task": str(block.input)[:80]})
                continue

            # Agent dispatch
            agent_key = block.name.replace("call_", "")
            task = block.input.get("task", "")
            context = block.input.get("context", "")
            agent_calls.append((block.id, agent_key, task, context))

        # Dispatch agents — parallel if multiple
        if len(agent_calls) == 1:
            bid, key, task, ctx = agent_calls[0]
            self._log(f"Dispatching → {key.upper()}")
            self._trace.append({"agent": key, "task": task[:80]})
            _, res = self._call_agent(key, task, ctx)
            results[bid] = res
        elif len(agent_calls) > 1:
            keys = [c[1].upper() for c in agent_calls]
            self._log(f"Parallel dispatch → {keys}")
            for _, key, task, _ in agent_calls:
                self._trace.append({"agent": key, "task": task[:80]})
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self._call_agent, key, task, ctx): bid
                    for bid, key, task, ctx in agent_calls
                }
                for future in concurrent.futures.as_completed(futures):
                    bid = futures[future]
                    _, res = future.result()
                    results[bid] = res

        # Return tool results preserving original block order
        ordered_ids = [b.id for b in blocks if b.type == "tool_use"]
        return [
            {"type": "tool_result", "tool_use_id": bid, "content": results[bid]}
            for bid in ordered_ids
            if bid in results
        ]

    def run(self, user_task: str) -> str:
        from utils.cost import get_tracker

        self._trace = []
        self._log(f"Task: {user_task[:120]}...")

        messages = (
            self._history + [{"role": "user", "content": user_task}]
            if self.maintain_history
            else [{"role": "user", "content": user_task}]
        )

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=[{
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    tools=AGENT_TOOLS,
                    messages=messages,
                )
                get_tracker().add(response, self.model)
                break
            except anthropic.RateLimitError:
                wait = 2 ** attempt
                self._log(f"Rate limit — retrying in {wait}s...")
                time.sleep(wait)
                if attempt == self.max_retries - 1:
                    return "Error: rate limit exhausted after retries."
            except Exception as e:
                return f"Error: {e}"

        while True:
            if response.stop_reason == "end_turn":
                final = "".join(b.text for b in response.content if hasattr(b, "text"))
                self._log("Complete.")
                if self.maintain_history:
                    self._history.append({"role": "user", "content": user_task})
                    self._history.append({"role": "assistant", "content": final})
                return final

            messages.append({"role": "assistant", "content": response.content})
            tool_results = self._process_tool_blocks(response.content)
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=AGENT_TOOLS,
                messages=messages,
            )
            get_tracker().add(response, self.model)

    @property
    def last_trace(self) -> list[dict]:
        return list(self._trace)

    def clear_history(self) -> None:
        self._history = []
        self._log("History cleared.")
