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

## How to Operate

1. **Analyze** the task — understand scope, type, and expected output.
2. **Sequence** agents appropriately. Simple tasks: 1–2 agents. Complex tasks: chain them (e.g., researcher → writer → reviewer).
3. **Pass context** — always include relevant prior results when calling the next agent.
4. **Parallelize** when multiple independent sub-tasks can run simultaneously (e.g., two independent research tasks).
5. **Synthesize** all agent outputs into a single coherent final answer for the user.
6. **Never fabricate** agent outputs — only use what agents actually return.

Start with the planner for any task requiring more than 2 distinct steps."""

AGENT_TOOLS = [
    {
        "name": "call_planner",
        "description": "Create a detailed step-by-step plan or strategy for a goal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The planning task"},
                "context": {"type": "string", "description": "Relevant background context"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_researcher",
        "description": "Research and gather information via web search. Returns cited findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The research question or topic"},
                "context": {"type": "string", "description": "Relevant background context"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_writer",
        "description": "Write, create, or edit any written content. Can save to files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The writing task"},
                "context": {"type": "string", "description": "Relevant research or prior content"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_developer",
        "description": "Write code, run Python, read/write files, and execute shell commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The development task"},
                "context": {"type": "string", "description": "Relevant context or requirements"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_reviewer",
        "description": "Review code or content for bugs, quality issues, and improvements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to review and focus areas"},
                "context": {"type": "string", "description": "The code or content to review"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_analyst",
        "description": "Analyze data or a situation and produce insights and recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The analysis question"},
                "context": {"type": "string", "description": "Data or information to analyze"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_qa_tester",
        "description": "Create test cases, validate outputs, and identify gaps or issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to test or validate"},
                "context": {"type": "string", "description": "Code, plan, or content being tested"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_critic",
        "description": "Evaluate quality holistically; provide a score and improvement recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Evaluation criteria and goal"},
                "context": {"type": "string", "description": "The work to evaluate"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_summarizer",
        "description": "Condense lengthy content into a clear, concise summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Summary type and desired length"},
                "context": {"type": "string", "description": "The content to summarize"},
            },
            "required": ["task"],
        },
    },
]


class Orchestrator:
    """Hierarchical orchestrator that coordinates a 10-agent team via Claude tool use."""

    def __init__(
        self,
        agents: dict[str, Any],
        model: str = "claude-sonnet-4-6",
        verbose: bool = True,
        maintain_history: bool = False,
        max_retries: int = 3,
    ):
        self.agents = agents
        self.model = model
        self.verbose = verbose
        self.maintain_history = maintain_history
        self.max_retries = max_retries
        self.client = anthropic.Anthropic()
        self._history: list[dict] = []

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"\n[Orchestrator] {message}")

    def _call_agent(self, agent_key: str, task: str, context: str) -> tuple[str, str]:
        """Call a single agent; returns (agent_key, result)."""
        if agent_key not in self.agents:
            return agent_key, f"Agent '{agent_key}' is not available."
        result = self.agents[agent_key].run(task, context if context else None)
        return agent_key, result

    def _process_tool_blocks(self, blocks: list) -> list[dict]:
        """Process all tool_use blocks, running independent calls in parallel."""
        from utils.cost import get_tracker

        calls = []
        for block in blocks:
            if block.type != "tool_use":
                continue
            agent_key = block.name.replace("call_", "")
            task = block.input.get("task", "")
            context = block.input.get("context", "")
            calls.append((block.id, agent_key, task, context))

        if not calls:
            return []

        results: dict[str, str] = {}

        if len(calls) == 1:
            bid, key, task, ctx = calls[0]
            self._log(f"Dispatching → {key.upper()}")
            _, res = self._call_agent(key, task, ctx)
            results[bid] = res
        else:
            self._log(f"Dispatching {len(calls)} agents in parallel: {[c[1].upper() for c in calls]}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_map = {
                    executor.submit(self._call_agent, key, task, ctx): bid
                    for bid, key, task, ctx in calls
                }
                for future in concurrent.futures.as_completed(future_map):
                    bid = future_map[future]
                    _, res = future.result()
                    results[bid] = res

        return [
            {"type": "tool_result", "tool_use_id": bid, "content": results[bid]}
            for bid, *_ in calls
        ]

    def run(self, user_task: str) -> str:
        from utils.cost import get_tracker

        self._log(f"Task: {user_task[:120]}...")

        if self.maintain_history:
            messages = self._history + [{"role": "user", "content": user_task}]
        else:
            messages = [{"role": "user", "content": user_task}]

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
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
                    return "Error: rate limit exhausted."
            except Exception as e:
                return f"Error: {e}"

        while True:
            if response.stop_reason == "end_turn":
                final = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
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
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=AGENT_TOOLS,
                messages=messages,
            )
            get_tracker().add(response, self.model)

    def clear_history(self) -> None:
        """Reset conversation history (chat mode only)."""
        self._history = []
        self._log("History cleared.")
