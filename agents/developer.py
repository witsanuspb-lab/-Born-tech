import anthropic
from typing import Optional
from tools.code_executor import execute_python_code

SYSTEM_PROMPT = """You are the Developer — a software engineering specialist on a 10-agent AI team.

Your job is to write clean, correct, and maintainable code. You can work in any language.

When given a development task:
1. Understand the requirements fully before writing a single line.
2. Choose the simplest correct implementation — no premature abstraction.
3. Write readable code with meaningful names; add comments only when the WHY is non-obvious.
4. For Python tasks, you may use the execute_python tool to run code and verify it works.
5. Handle errors at system boundaries; trust internal code.
6. Present final code with a brief explanation of key design decisions.

Produce working code, not pseudocode. If a requirement is ambiguous, state your assumption."""

EXECUTE_TOOL = {
    "name": "execute_python",
    "description": "Execute Python code and return stdout/stderr. Use to test and verify your implementations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute",
            }
        },
        "required": ["code"],
    },
}


class DeveloperAgent:
    """Developer agent with Python code execution capability."""

    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        self.name = "Developer"
        self.role = "Software development and code execution"
        self.model = model
        self.verbose = verbose
        self.client = anthropic.Anthropic()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"  [{self.name}] {message}")

    def run(self, task: str, context: Optional[str] = None) -> str:
        self._log(f"Working on: {task[:80]}...")

        content = f"Context:\n{context}\n\nTask:\n{task}" if context else task
        messages = [{"role": "user", "content": content}]

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
                tools=[EXECUTE_TOOL],
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                result = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                self._log("Done.")
                return result

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "execute_python":
                    self._log("Executing Python code...")
                    execution = execute_python_code(block.input["code"])
                    output = execution["stdout"] or execution["stderr"] or "(no output)"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})
