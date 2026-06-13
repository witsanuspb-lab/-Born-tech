from typing import Optional

from .tool_agent import ToolAgent
from tools.code_executor import execute_python_code
from tools.file_tools import append_file, list_directory, read_file, write_file
from tools.shell_tools import run_shell

SYSTEM_PROMPT = """You are the Developer — a software engineering specialist on a 10-agent AI team.

Your job is to write clean, correct, and maintainable code. You work in any language.

You have access to these tools:
- execute_python: Run Python code and see live output. Use to verify your implementations.
- read_file: Read an existing file from disk.
- write_file: Save code or any file to disk.
- append_file: Append content to an existing file.
- list_directory: List files in a directory.
- run_shell: Run shell commands (git, pip, npm, ls, etc.) — destructive commands are blocked.

When given a development task:
1. Understand the requirements fully before writing.
2. Choose the simplest correct implementation — no premature abstraction.
3. Use execute_python to test your code before presenting it.
4. Save final files with write_file when the task asks for files to be created.
5. Present a brief explanation of key design decisions alongside the final code.

Produce working code, not pseudocode. State assumptions if requirements are ambiguous."""

TOOLS = [
    {
        "name": "execute_python",
        "description": "Execute Python code in a subprocess and return stdout/stderr. Use to verify implementations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "append_file",
        "description": "Append content to an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to append"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories at a given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (default: current directory)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "run_shell",
        "description": "Run a shell command (git, pip, npm, ls, cat, etc.). Destructive commands like rm/kill are blocked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
]


class DeveloperAgent(ToolAgent):
    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        super().__init__(
            name="Developer",
            role="Software development with code execution and file access",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            model=model,
            verbose=verbose,
        )

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        match tool_name:
            case "execute_python":
                result = execute_python_code(tool_input["code"])
                output = result["stdout"] or result["stderr"] or "(no output)"
                return output
            case "read_file":
                return read_file(tool_input["path"])
            case "write_file":
                return write_file(tool_input["path"], tool_input["content"])
            case "append_file":
                return append_file(tool_input["path"], tool_input["content"])
            case "list_directory":
                return list_directory(tool_input.get("path", "."))
            case "run_shell":
                return run_shell(tool_input["command"])
            case _:
                return f"Unknown tool: {tool_name}"
