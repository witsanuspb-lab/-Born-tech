import anthropic
from typing import Any

SYSTEM_PROMPT = """You are the Orchestrator — the master coordinator of a 10-agent AI team. You receive tasks from users and direct the right agents to accomplish them.

## Your Team

| Agent       | Specialty                                              |
|-------------|--------------------------------------------------------|
| planner     | Breaks goals into structured, step-by-step plans       |
| researcher  | Gathers and synthesizes accurate information           |
| writer      | Crafts polished written content of any kind            |
| developer   | Writes code and executes Python to verify it works     |
| reviewer    | Reviews code/content for bugs and quality issues       |
| analyst     | Analyzes data and produces insights                    |
| qa_tester   | Designs test cases and validates outputs               |
| critic      | Scores work holistically and recommends improvements   |
| summarizer  | Distills long content into clear, concise summaries    |

## How to Operate

1. **Analyze** the user's task — understand scope, type, and expected output.
2. **Plan** your agent sequence. For simple tasks, call 1–2 agents. For complex tasks, chain agents (e.g., researcher → writer → reviewer).
3. **Pass context** between agents — always include relevant prior results when calling the next agent.
4. **Synthesize** all agent outputs into a single, coherent final answer for the user.
5. **Never fabricate** agent outputs — only use what agents actually return.

Start with the planner for any task that has more than 2 distinct steps."""

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
        "description": "Research and gather information on any topic or question.",
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
        "description": "Write, create, or edit any written content.",
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
        "description": "Write code or solve programming problems. Can execute Python to verify results.",
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
        "description": "Evaluate quality holistically and provide a score with improvement recommendations.",
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
    """Hierarchical orchestrator that coordinates a 10-agent team using tool use."""

    def __init__(self, agents: dict[str, Any], model: str = "claude-sonnet-4-6", verbose: bool = True):
        self.agents = agents
        self.model = model
        self.verbose = verbose
        self.client = anthropic.Anthropic()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"\n[Orchestrator] {message}")

    def run(self, user_task: str) -> str:
        """Process a user task by coordinating the agent team."""
        self._log(f"Task received: {user_task[:120]}...")

        messages = [{"role": "user", "content": user_task}]

        while True:
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

            if response.stop_reason == "end_turn":
                final = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                self._log("Task complete.")
                return final

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                agent_key = block.name.replace("call_", "")
                task = block.input.get("task", "")
                context = block.input.get("context", "")

                self._log(f"Dispatching to → {agent_key.upper()} agent")

                if agent_key in self.agents:
                    result = self.agents[agent_key].run(
                        task, context if context else None
                    )
                else:
                    result = f"Agent '{agent_key}' is not available."

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
