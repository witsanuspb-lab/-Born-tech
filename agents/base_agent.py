import time
import anthropic
from typing import Optional


class BaseAgent:
    """Base class for simple (no-tool) specialized agents."""

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
        if not self.verbose:
            return
        try:
            from utils.display import console, AGENT_STYLES
            style = AGENT_STYLES.get(self.name, "dim")
            console.print(f"  [{self.name}] {message}", style=style)
        except ImportError:
            print(f"  [{self.name}] {message}")

    def run(self, task: str, context: Optional[str] = None, retries: int = 3) -> str:
        from utils.cost import get_tracker

        self._log(f"Working on: {task[:80]}...")
        content = f"Context:\n{context}\n\nTask:\n{task}" if context else task

        for attempt in range(retries):
            try:
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
                get_tracker().add(response, self.model)
                self._log("Done.")
                return response.content[0].text

            except anthropic.RateLimitError:
                wait = 2 ** attempt
                self._log(f"Rate limit — retrying in {wait}s...")
                time.sleep(wait)
            except anthropic.APIStatusError as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    self._log(f"API error ({e.status_code}) — retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    return f"Error after {retries} attempts: {e}"

        return "Error: all retry attempts exhausted."
