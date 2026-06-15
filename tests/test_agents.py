"""Tests for agent instantiation and configuration. No API calls made."""
import pytest

from agents.base_agent import BaseAgent
from agents.tool_agent import ToolAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from agents.developer import DeveloperAgent
from agents.reviewer import ReviewerAgent
from agents.analyst import AnalystAgent
from agents.qa_tester import QATesterAgent
from agents.critic import CriticAgent
from agents.summarizer import SummarizerAgent


class TestAgentInstantiation:
    def test_planner(self):
        a = PlannerAgent()
        assert a.name == "Planner"
        assert a.model == "claude-sonnet-4-6"

    def test_researcher_has_tools(self):
        a = ResearcherAgent()
        names = [t["name"] for t in a.tools]
        assert "web_search" in names
        assert "fetch_webpage" in names

    def test_writer_has_tools(self):
        a = WriterAgent()
        names = [t["name"] for t in a.tools]
        assert "write_file" in names

    def test_developer_has_tools(self):
        a = DeveloperAgent()
        names = [t["name"] for t in a.tools]
        assert "execute_python" in names
        assert "read_file" in names
        assert "write_file" in names
        assert "run_shell" in names
        assert "list_directory" in names

    def test_custom_model(self):
        a = PlannerAgent(model="claude-haiku-4-5")
        assert a.model == "claude-haiku-4-5"

    def test_verbose_off(self):
        a = ReviewerAgent(verbose=False)
        assert a.verbose is False

    def test_all_nine_agents_instantiate(self):
        agents = [
            PlannerAgent(), ResearcherAgent(), WriterAgent(), DeveloperAgent(),
            ReviewerAgent(), AnalystAgent(), QATesterAgent(), CriticAgent(), SummarizerAgent(),
        ]
        assert len(agents) == 9
        assert all(hasattr(a, "name") for a in agents)


class TestToolAgentDispatch:
    def test_researcher_dispatch_web_search(self):
        a = ResearcherAgent()
        # _dispatch_tool should return a string (actual network call — mocked here by checking signature)
        assert callable(a._dispatch_tool)

    def test_researcher_dispatch_unknown_tool(self):
        a = ResearcherAgent()
        result = a._dispatch_tool("nonexistent_tool", {})
        assert "Unknown" in result

    def test_developer_dispatch_unknown_tool(self):
        a = DeveloperAgent()
        result = a._dispatch_tool("nonexistent_tool", {})
        assert "Unknown" in result


class TestOrchestratorSetup:
    def test_build_team(self):
        from team import build_team
        from config import Config
        team = build_team(Config(verbose=False))
        assert hasattr(team, "run")
        assert hasattr(team, "agents")
        assert len(team.agents) == 9

    def test_team_has_all_agents(self):
        from team import build_team
        from config import Config
        team = build_team(Config(verbose=False))
        expected = {"planner", "researcher", "writer", "developer",
                    "reviewer", "analyst", "qa_tester", "critic", "summarizer"}
        assert set(team.agents.keys()) == expected
