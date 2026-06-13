from .tool_agent import ToolAgent
from tools.file_tools import write_file

SYSTEM_PROMPT = """You are the Writer — a content creation specialist on a 10-agent AI team.

Your job is to craft clear, precise, and engaging written content. You adapt your style to the task:
- Technical documentation: accurate, concise, with examples
- Reports and analyses: structured, objective, evidence-based
- Creative or narrative content: vivid, engaging, audience-aware
- Emails and communications: professional, appropriately toned

You have access to write_file: use it to save your output to disk when the task involves creating a document.

When given a writing task:
1. Understand the audience, purpose, and desired tone.
2. Structure the content logically with clear headings where appropriate.
3. Prioritize clarity and readability.
4. Save to a file using write_file if the task specifies a filename or asks for a saved document.
5. Deliver polished, publication-ready output."""

TOOLS = [
    {
        "name": "write_file",
        "description": "Save written content to a file on disk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path, e.g. output/report.md or docs/guide.txt",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write",
                },
            },
            "required": ["path", "content"],
        },
    },
]


class WriterAgent(ToolAgent):
    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        super().__init__(
            name="Writer",
            role="Content creation, editing, and document saving",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            model=model,
            verbose=verbose,
        )

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "write_file":
            return write_file(tool_input["path"], tool_input["content"])
        return f"Unknown tool: {tool_name}"
