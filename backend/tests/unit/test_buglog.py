"""Tests for BugLog: bug recording, deduplication, and queries."""

import pytest
from skpl_agent.context.buglog import BugLog, BugRecord, BugStatus


class TestBugLogging:
    """Basic bug recording."""

    @pytest.fixture
    def buglog(self):
        return BugLog(session_id="test-session")

    def test_log_bug(self, buglog):
        bug = buglog.log(
            error_type="SyntaxError",
            error_message="invalid syntax at line 42",
            file_path="src/main.py",
            line_number=42,
        )
        assert bug.error_type == "SyntaxError"
        assert bug.error_message == "invalid syntax at line 42"
        assert bug.file_path == "src/main.py"
        assert bug.line_number == 42
        assert bug.session_id == "test-session"
        assert bug.status == BugStatus.OPEN.value

    def test_log_bug_with_traceback(self, buglog):
        bug = buglog.log(
            error_type="ValueError",
            error_message="invalid value",
            error_traceback="Traceback...\n  File \"test.py\", line 10\n    raise ValueError",
        )
        assert bug.error_traceback is not None
        assert "Traceback" in bug.error_traceback

    def test_log_bug_with_context(self, buglog):
        bug = buglog.log(
            error_type="TypeError",
            error_message="unsupported operand",
            context_snippet="a + b  # a is None",
            agent_id="agent-001",
        )
        assert bug.context_snippet is not None
        assert bug.agent_id == "agent-001"

    def test_log_exception(self, buglog):
        try:
            raise ValueError("test error message")
        except ValueError as exc:
            bug = buglog.log_exception(exc, file_path="src/test.py", line_number=10)
        assert bug.error_type == "ValueError"
        assert "test error message" in bug.error_message
        assert bug.error_traceback is not None

    def test_log_bug_generates_id(self, buglog):
        bug = buglog.log(error_type="Error", error_message="test")
        assert bug.id is not None
        assert len(bug.id) > 0

    def test_log_bug_generates_fingerprint(self, buglog):
        bug = buglog.log(error_type="Error", error_message="test")
        assert bug.fingerprint is not None
        assert len(bug.fingerprint) > 0


class TestBugDeduplication:
    """Bug deduplication via fingerprinting."""

    @pytest.fixture
    def buglog(self):
        return BugLog(session_id="test-session")

    def test_duplicate_exact(self, buglog):
        bug1 = buglog.log(
            error_type="SyntaxError",
            error_message="unexpected EOF while parsing",
            file_path="src/main.py",
            line_number=10,
        )
        bug2 = buglog.log(
            error_type="SyntaxError",
            error_message="unexpected EOF while parsing",
            file_path="src/main.py",
            line_number=10,
        )
        assert bug2.duplicate_of == bug1.id
        assert bug2.status == BugStatus.DUPLICATE.value

    def test_not_duplicate_different_types(self, buglog):
        bug1 = buglog.log(error_type="SyntaxError", error_message="syntax error in parsing")
        bug2 = buglog.log(error_type="ValueError", error_message="value is out of range")
        # Different types AND different messages should not be duplicates
        assert bug2.duplicate_of is None

    def test_metadata_json(self, buglog):
        bug = buglog.log(
            error_type="Error",
            error_message="test",
            metadata={"key": "value", "count": 42},
        )
        assert bug.metadata_json is not None
        import json
        data = json.loads(bug.metadata_json)
        assert data["key"] == "value"
        assert data["count"] == 42


class TestBugQueries:
    """Querying bugs from the log."""

    @pytest.fixture
    def buglog(self):
        bl = BugLog(session_id="sess-1")
        bl.log(error_type="SyntaxError", error_message="err1", file_path="a.py")
        bl.log(error_type="ValueError", error_message="err2", file_path="b.py")
        bl.log(error_type="SyntaxError", error_message="err3", file_path="a.py")
        return bl

    def test_get_recent(self, buglog):
        recent = buglog.get_recent(limit=2)
        assert len(recent) == 2

    def test_get_by_type(self, buglog):
        syntax = buglog.get_by_type("SyntaxError")
        assert len(syntax) == 2

    def test_get_by_file(self, buglog):
        a_bugs = buglog.get_by_file("a.py")
        assert len(a_bugs) == 2

    def test_get_by_session(self, buglog):
        sess_bugs = buglog.get_by_session("sess-1")
        assert len(sess_bugs) == 3

    def test_get_open(self, buglog):
        open_bugs = buglog.get_open()
        assert len(open_bugs) == 3

    def test_get_nonexistent(self, buglog):
        assert buglog.get("nonexistent-id") is None


class TestBugUpdates:
    """Bug status updates."""

    @pytest.fixture
    def buglog(self):
        bl = BugLog()
        bl.log(error_type="Error", error_message="test")
        return bl

    def test_update_status(self, buglog):
        bug = buglog.get_recent(1)[0]
        updated = buglog.update_status(
            bug.id, BugStatus.RESOLVED, resolution="Fixed in commit abc123"
        )
        assert updated is not None
        assert updated.status == BugStatus.RESOLVED.value
        assert updated.resolution == "Fixed in commit abc123"
        assert updated.resolved_at is not None

    def test_update_nonexistent(self, buglog):
        result = buglog.update_status("nonexistent", BugStatus.RESOLVED)
        assert result is None

    def test_mark_duplicate(self, buglog):
        bugs = buglog.get_recent(2)
        if len(bugs) < 2:
            buglog.log(error_type="Error", error_message="test2")
            bugs = buglog.get_recent(2)
        result = buglog.mark_duplicate(bugs[1].id, bugs[0].id)
        assert result is not None
        assert result.duplicate_of == bugs[0].id
        assert result.status == BugStatus.DUPLICATE.value


class TestBugStats:
    """Bug statistics."""

    def test_empty_stats(self):
        buglog = BugLog()
        stats = buglog.get_stats()
        assert stats["total"] == 0
        assert stats["open"] == 0

    def test_stats_with_bugs(self):
        buglog = BugLog()
        buglog.log(error_type="SyntaxError", error_message="e1")
        buglog.log(error_type="ValueError", error_message="e2")
        buglog.log(error_type="SyntaxError", error_message="e3")
        stats = buglog.get_stats()
        assert stats["total"] == 3
        assert stats["open"] == 3
        assert stats["by_type"]["SyntaxError"] == 2
        assert stats["by_type"]["ValueError"] == 1


class TestBugLogMaxEntries:
    """Bug log trimming when max entries exceeded."""

    def test_max_entries_trimming(self):
        buglog = BugLog(max_entries=5)
        for i in range(10):
            buglog.log(error_type="Error", error_message=f"error {i}")
        assert len(buglog.get_all()) <= 5

    def test_clear(self):
        buglog = BugLog()
        buglog.log(error_type="Error", error_message="test")
        buglog.clear()
        assert len(buglog.get_all()) == 0


class TestBugRecordDataclass:
    """BugRecord dataclass behavior."""

    def test_default_values(self):
        bug = BugRecord(
            error_type="Error",
            error_message="test",
        )
        assert bug.id is not None
        assert bug.session_id == ""
        assert bug.status == BugStatus.OPEN.value
        assert bug.created_at is not None
        assert bug.updated_at is not None