"""Tests for Cerebrum: agent learning memory and knowledge persistence."""

import pytest
import time
from skpl_agent.context.cerebrum import Cerebrum, Memory


class TestMemoryCRUD:
    """Basic memory operations: remember, recall, forget, update."""

    @pytest.fixture
    def brain(self):
        return Cerebrum(agent_id="test-agent")

    def test_remember(self, brain):
        mem = brain.remember("key1", "value1", category="test")
        assert mem.key == "key1"
        assert mem.value == "value1"
        assert mem.category == "test"
        assert mem.agent_id == "test-agent"

    def test_remember_overwrite(self, brain):
        brain.remember("key1", "value1")
        mem = brain.remember("key1", "value2")
        assert mem.value == "value2"
        assert len(brain.get_all()) == 1

    def test_recall(self, brain):
        brain.remember("key1", "value1")
        mem = brain.recall("key1")
        assert mem is not None
        assert mem.value == "value1"
        assert mem.access_count == 1

    def test_recall_nonexistent(self, brain):
        assert brain.recall("nonexistent") is None

    def test_recall_increments_access(self, brain):
        brain.remember("key1", "value1")
        brain.recall("key1")
        brain.recall("key1")
        mem = brain.recall("key1")
        assert mem.access_count == 3

    def test_forget(self, brain):
        brain.remember("key1", "value1")
        assert brain.forget("key1") is True
        assert brain.recall("key1") is None

    def test_forget_nonexistent(self, brain):
        assert brain.forget("nonexistent") is False

    def test_update(self, brain):
        brain.remember("key1", "value1", confidence=0.5)
        mem = brain.update("key1", value="new_value", confidence=0.9)
        assert mem is not None
        assert mem.value == "new_value"
        assert mem.confidence == 0.9

    def test_update_nonexistent(self, brain):
        assert brain.update("nonexistent", value="x") is None


class TestMemoryQueries:
    """Query operations on memories."""

    @pytest.fixture
    def brain(self):
        b = Cerebrum(agent_id="test-agent")
        b.remember("pref_theme", "dark", category="preferences", confidence=0.9)
        b.remember("pref_lang", "python", category="preferences", confidence=0.8)
        b.remember("fact_earth", "round", category="facts", confidence=1.0)
        b.remember("temp_session", "xyz", category="session", confidence=0.3)
        return b

    def test_get_by_category(self, brain):
        prefs = brain.get_by_category("preferences")
        assert len(prefs) == 2

    def test_get_all(self, brain):
        all_mems = brain.get_all()
        assert len(all_mems) == 4

    def test_search(self, brain):
        results = brain.search("theme")
        assert len(results) >= 1
        assert any("theme" in r.key for r in results)

    def test_search_value(self, brain):
        results = brain.search("python")
        assert len(results) >= 1

    def test_search_no_match(self, brain):
        results = brain.search("nonexistent_xyz")
        assert len(results) == 0

    def test_get_high_confidence(self, brain):
        high = brain.get_high_confidence(threshold=0.8)
        assert len(high) >= 2

    def test_get_frequently_accessed(self, brain):
        # Access some memories multiple times
        brain.recall("pref_theme")
        brain.recall("pref_theme")
        brain.recall("pref_theme")
        brain.recall("pref_theme")
        brain.recall("pref_theme")
        brain.recall("pref_lang")
        brain.recall("pref_lang")
        brain.recall("pref_lang")
        brain.recall("pref_lang")
        brain.recall("pref_lang")
        frequent = brain.get_frequently_accessed(min_access=5)
        assert len(frequent) >= 2


class TestMemoryTTL:
    """TTL-based memory expiration."""

    def test_ttl_not_expired(self):
        brain = Cerebrum()
        brain.remember("key1", "value1", ttl_seconds=3600)
        mem = brain.recall("key1")
        assert mem is not None

    def test_ttl_expired(self):
        brain = Cerebrum()
        brain.remember("key1", "value1", ttl_seconds=0)  # expires immediately
        time.sleep(0.01)
        assert brain.recall("key1") is None

    def test_ttl_cleanup_on_get_all(self):
        brain = Cerebrum()
        brain.remember("expired", "value", ttl_seconds=0)
        brain.remember("valid", "value", ttl_seconds=3600)
        time.sleep(0.01)
        all_mems = brain.get_all()
        assert len(all_mems) == 1
        assert all_mems[0].key == "valid"

    def test_memory_is_expired_property(self):
        mem = Memory(key="test", value="val", ttl_seconds=0)
        time.sleep(0.01)
        assert mem.is_expired is True

    def test_memory_no_ttl_not_expired(self):
        mem = Memory(key="test", value="val")
        assert mem.is_expired is False


class TestMemoryExport:
    """Export and import operations."""

    def test_export_context(self, brain=None):
        if brain is None:
            brain = Cerebrum()
            brain.remember("key1", "value1", category="test")
            brain.remember("key2", "value2", category="test")
        context = brain.export_context(max_entries=10)
        assert "## Agent Memory (Cerebrum)" in context
        assert "key1" in context
        assert "value1" in context

    def test_export_empty(self, brain=None):
        if brain is None:
            brain = Cerebrum()
        context = brain.export_context()
        assert context == ""

    def test_to_dict(self, brain=None):
        if brain is None:
            brain = Cerebrum()
            brain.remember("key1", "value1", category="test", confidence=0.9)
        data = brain.to_dict()
        assert "key1" in data
        assert data["key1"]["value"] == "value1"
        assert data["key1"]["category"] == "test"
        assert data["key1"]["confidence"] == 0.9

    def test_import_from_dict(self, brain=None):
        if brain is None:
            brain = Cerebrum()
        data = {
            "key_a": {"value": "val_a", "category": "cat1", "confidence": 0.8},
            "key_b": {"value": "val_b", "category": "cat2", "confidence": 0.9},
        }
        count = brain.import_from_dict(data)
        assert count == 2
        assert brain.recall("key_a").value == "val_a"
        assert brain.recall("key_b").value == "val_b"


class TestMemoryStats:
    """Memory statistics."""

    def test_empty_stats(self):
        brain = Cerebrum()
        stats = brain.get_stats()
        assert stats["total_memories"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_stats_with_data(self):
        brain = Cerebrum()
        brain.remember("a", "1", category="cat1", confidence=0.8)
        brain.remember("b", "2", category="cat1", confidence=0.9)
        brain.remember("c", "3", category="cat2", confidence=1.0)
        stats = brain.get_stats()
        assert stats["total_memories"] == 3
        assert stats["by_category"]["cat1"] == 2
        assert stats["by_category"]["cat2"] == 1
        assert stats["avg_confidence"] == pytest.approx(0.9, abs=0.01)


class TestMemoryDataclass:
    """Memory dataclass."""

    def test_default_values(self):
        mem = Memory(key="test", value="val")
        assert mem.id is not None
        assert mem.agent_id == ""
        assert mem.category == "general"
        assert mem.confidence == 1.0
        assert mem.access_count == 0
        assert mem.created_at is not None

    def test_last_accessed_updated(self):
        brain = Cerebrum()
        brain.remember("key1", "value1")
        mem = brain.recall("key1")
        assert mem.last_accessed_at is not None


class TestMaxEntries:
    """Max entries and trimming."""

    def test_max_entries_trimming(self):
        brain = Cerebrum(max_entries=5)
        for i in range(10):
            brain.remember(f"key{i}", f"value{i}", confidence=float(i) / 10)
        # After trimming, should have at most 5 entries
        assert len(brain.get_all()) <= 5

    def test_clear(self):
        brain = Cerebrum()
        brain.remember("key1", "value1")
        brain.clear()
        assert len(brain.get_all()) == 0
        assert brain.recall("key1") is None