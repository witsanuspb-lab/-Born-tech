import shlex
import subprocess

# Commands that could cause irreversible damage
_BLOCKED = {
    "rm", "rmdir", "dd", "mkfs", "format", "fdisk",
    "shutdown", "reboot", "halt", "poweroff",
    "kill", "pkill", "killall",
    "chmod", "chown", "sudo", "su",
}


def run_shell(command: str, timeout: int = 30) -> str:
    """Run a shell command and return combined stdout + stderr."""
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return f"Invalid command syntax: {e}"

    if not parts:
        return "Empty command."

    if parts[0] in _BLOCKED:
        return f"Error: '{parts[0]}' is blocked for safety. Use execute_python for file operations."

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            return f"(exited with code {result.returncode})"
        return output
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except FileNotFoundError:
        return f"Command not found: {parts[0]}"
    except Exception as e:
        return f"Error: {e}"
