"""SKPL Memory System — Unified memory orchestration L1-L4.

Provides:
- MemoryManager (L1 Cerebrum + L2 Mem0 + L3 KnowledgeBase + L4 Vector)
- Cross-device session bridging
- Memory API routes (context assembly, device bridging, health)
"""

from skpl_agent.app._memory.manager import MemoryManager
from skpl_agent.app._memory.router import router as memory_router

__all__ = [
    "MemoryManager",
    "memory_router",
]