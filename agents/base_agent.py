import anthropic
from typing import Optional


class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        verbose: bool = True,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.verbose = verbose
        self.client = anthropic.Anthropic()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"  [{self.name}] {message}")

    def run(self, task: str, context: Optional[str] = None) -> str:
        """Run a task and return the agent's response."""
        self._log(f"Working on: {task[:80]}...")

        content = f"Context:\n{context}\n\nTask:\n{task}" if context else task

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": content}],
        )

        result = response.content[0].text
        self._log("Done.")
        return result
