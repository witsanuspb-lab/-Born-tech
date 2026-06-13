import os
from datetime import datetime


class SessionLogger:
    """Saves each task + result to a timestamped markdown file in output/."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = os.path.join(output_dir, f"session_{ts}.md")
        self._entry_count = 0
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(f"# AI Team Session\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    def log(self, task: str, result: str) -> str:
        self._entry_count += 1
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"---\n\n")
            f.write(f"## Task {self._entry_count}\n\n")
            f.write(f"{task}\n\n")
            f.write(f"## Result\n\n")
            f.write(f"{result}\n\n")
        return self.path

    def finalize(self, cost_summary: str = "") -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"---\n\n")
            f.write(f"*Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            if cost_summary:
                f.write(f"\n`{cost_summary}`\n")
