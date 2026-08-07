"""SKPL Agent Web Intelligence (Agent-S KnowledgeBase Integration).

Provides web search, knowledge retrieval, and research capabilities
adapted from Agent-S. Supports multiple search backends and
knowledge fusion for agent-augmented research.

Architecture:
    SearchEngine (abstract)
        ├── PerplexicaEngine   — self-hosted Perplexica
        ├── LLMSearchEngine    — LLM internal knowledge
        ├── DuckDuckGoEngine   — DuckDuckGo (free)
        └── GoogleEngine       — Google Custom Search API

    KnowledgeBase
        ├── formulate_query()    — LLM-based query generation
        ├── retrieve_knowledge() — search + cache
        └── knowledge_fusion()   — merge web + experience results

    ResearchAgent
        └── research() — multi-step research with citations
"""

from skpl_agent.web_intelligence._search_engine import (
    SearchEngine,
    SearchResult,
    PerplexicaEngine,
    LLMSearchEngine,
    DuckDuckGoEngine,
)
from skpl_agent.web_intelligence._knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseConfig,
)
from skpl_agent.web_intelligence._research_agent import (
    ResearchAgent,
    ResearchConfig,
    ResearchTask,
    ResearchResult,
)

__all__ = [
    # Search engines
    "SearchEngine",
    "SearchResult",
    "PerplexicaEngine",
    "LLMSearchEngine",
    "DuckDuckGoEngine",
    # Knowledge base
    "KnowledgeBase",
    "KnowledgeBaseConfig",
    # Research agent
    "ResearchAgent",
    "ResearchConfig",
    "ResearchTask",
    "ResearchResult",
]