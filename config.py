import os
from dataclasses import dataclass, field


@dataclass
class Config:
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    orchestrator_model: str = "claude-sonnet-4-6"
    agent_model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096
    verbose: bool = True
    maintain_history: bool = False   # enable chat mode (memory across turns)
    save_output: bool = False        # auto-save results to output/
    show_cost: bool = True           # print token usage + cost after each task
    max_retries: int = 3             # API retry attempts on error
