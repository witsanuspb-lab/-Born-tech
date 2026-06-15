from config import Config
from memory.store import MemoryStore
from agents import (
    Orchestrator,
    PlannerAgent,
    ResearcherAgent,
    WriterAgent,
    DeveloperAgent,
    ReviewerAgent,
    AnalystAgent,
    QATesterAgent,
    CriticAgent,
    SummarizerAgent,
)


def build_team(config: Config | None = None, memory: MemoryStore | None = None) -> Orchestrator:
    """Assemble and return the full 10-agent team with the Orchestrator as head."""
    if config is None:
        config = Config()

    m = config.agent_model
    v = config.verbose

    agents = {
        "planner":    PlannerAgent(model=m, verbose=v),
        "researcher": ResearcherAgent(model=m, verbose=v),
        "writer":     WriterAgent(model=m, verbose=v),
        "developer":  DeveloperAgent(model=m, verbose=v),
        "reviewer":   ReviewerAgent(model=m, verbose=v),
        "analyst":    AnalystAgent(model=m, verbose=v),
        "qa_tester":  QATesterAgent(model=m, verbose=v),
        "critic":     CriticAgent(model=m, verbose=v),
        "summarizer": SummarizerAgent(model=m, verbose=v),
    }

    store = memory if memory is not None else MemoryStore()

    return Orchestrator(
        agents=agents,
        model=config.orchestrator_model,
        verbose=config.verbose,
        maintain_history=config.maintain_history,
        max_retries=config.max_retries,
        memory=store,
    )
