from .tool_agent import ToolAgent
from tools.web_tools import fetch_webpage, web_search

SYSTEM_PROMPT = """You are the Researcher — an information synthesis specialist on a 10-agent AI team.

Your job is to gather, evaluate, and present information accurately. You have access to:
- web_search: Search the web for current information (use first)
- fetch_webpage: Read a specific URL in full when summaries aren't enough

When given a research task:
1. Run web_search on the core question first.
2. Fetch 1–2 key URLs if deeper reading would improve accuracy.
3. Synthesize findings — distinguish established facts from uncertain or evolving areas.
4. Present findings in a structured format with key takeaways at the top.
5. Never fabricate statistics or sources — flag uncertainty explicitly.

Your output must be thorough, well-organized, and immediately actionable for the team."""

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Returns summaries and links. Use this first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default 6)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_webpage",
        "description": "Fetch and extract the full text content from a specific URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
            },
            "required": ["url"],
        },
    },
]


class ResearcherAgent(ToolAgent):
    def __init__(self, model: str = "claude-sonnet-4-6", verbose: bool = True):
        super().__init__(
            name="Researcher",
            role="Information gathering and synthesis with web search",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            model=model,
            verbose=verbose,
        )

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "web_search":
            return web_search(tool_input["query"], tool_input.get("max_results", 6))
        if tool_name == "fetch_webpage":
            return fetch_webpage(tool_input["url"])
        return f"Unknown tool: {tool_name}"
