from typing import Optional
from .base_agent import BaseAgent


class ToolAgent(BaseAgent):
    """Base class for agents that need their own inner tool-use loop."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        tools: list,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        verbose: bool = True,
    ):
        super().__init__(
            name=name,
            role=role,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            verbose=verbose,
        )
        self.tools = tools

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        """Override in subclasses to handle tool calls."""
        return f"Unknown tool: {tool_name}"

    def run(self, task: str, context: Optional[str] = None) -> str:
        from utils.cost import get_tracker

        self._log(f"Working on: {task[:80]}...")
        content = f"Context:\n{context}\n\nTask:\n{task}" if context else task
        messages = [{"role": "user", "content": content}]

        while True:
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
                tools=self.tools,
                messages=messages,
            )
            get_tracker().add(response, self.model)

            if response.stop_reason == "end_turn":
                result = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                self._log("Done.")
                return result

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                self._log(f"Using tool: {block.name}")
                output = self._dispatch_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output}
                )

            messages.append({"role": "user", "content": tool_results})
