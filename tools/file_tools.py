import os


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    try:
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content):,} characters to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def append_file(path: str, content: str) -> str:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to {path}"
    except Exception as e:
        return f"Error appending to {path}: {e}"


def list_directory(path: str = ".") -> str:
    try:
        items = os.listdir(path)
        dirs, files = [], []
        for item in sorted(items):
            full = os.path.join(path, item)
            if os.path.isdir(full):
                dirs.append(f"[DIR]  {item}/")
            else:
                size = os.path.getsize(full)
                files.append(f"[FILE] {item}  ({size:,} bytes)")
        lines = dirs + files
        return "\n".join(lines) if lines else "(empty)"
    except Exception as e:
        return f"Error listing {path}: {e}"
