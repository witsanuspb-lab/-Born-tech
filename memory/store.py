import json
from datetime import datetime
from pathlib import Path


class MemoryStore:
    """JSON-backed key-value store that persists across sessions."""

    def __init__(self, path: str = "memory/memories.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def save(self, key: str, value: str) -> str:
        self._data[key] = {"value": value, "saved_at": datetime.now().isoformat()}
        self._save()
        return f"Saved memory '{key}'"

    def recall(self, key: str) -> str:
        if key not in self._data:
            return f"No memory for key '{key}'. Use list_memories to see what's stored."
        entry = self._data[key]
        return f"{entry['value']}\n(saved: {entry.get('saved_at', '?')})"

    def list_all(self) -> str:
        if not self._data:
            return "Memory is empty — nothing saved yet."
        lines = [f"Stored memories ({len(self._data)}):"]
        for key, entry in self._data.items():
            preview = entry["value"][:70].replace("\n", " ")
            if len(entry["value"]) > 70:
                preview += "…"
            lines.append(f"  • {key}: {preview}")
        return "\n".join(lines)

    def delete(self, key: str) -> str:
        if key not in self._data:
            return f"Key '{key}' not found."
        del self._data[key]
        self._save()
        return f"Deleted memory '{key}'"

    def clear_all(self) -> str:
        count = len(self._data)
        self._data = {}
        self._save()
        return f"Cleared {count} memories."

    def as_dict(self) -> dict:
        return {k: v["value"] for k, v in self._data.items()}
