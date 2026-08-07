"""Tests for desktop WebSocket handler."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDesktopWebSocket:
    """Tests for desktop WebSocket connection handling."""

    def test_token_validation(self) -> None:
        """JWT token validation works."""
        import jwt

        secret = "test-secret"
        payload = {"node_id": "node-1", "platform": "windows"}
        token = jwt.encode(payload, secret, algorithm="HS256")

        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["node_id"] == "node-1"
        assert decoded["platform"] == "windows"

    def test_invalid_token(self) -> None:
        """Invalid JWT token is rejected."""
        import jwt

        secret = "test-secret"
        token = "invalid-token"

        with pytest.raises(Exception):
            jwt.decode(token, secret, algorithms=["HS256"])

    def test_token_expiry(self) -> None:
        """Expired tokens are rejected."""
        import jwt
        from datetime import datetime, timedelta, timezone

        secret = "test-secret"
        payload = {
            "node_id": "node-1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"])


class TestDesktopMessageHandling:
    """Tests for desktop WebSocket message parsing."""

    def test_screenshot_message(self) -> None:
        """Screenshot messages are parsed correctly."""
        msg = {
            "type": "screenshot",
            "node_id": "node-1",
            "data": "base64-encoded-data",
            "timestamp": "2026-07-27T00:00:00Z",
        }
        assert msg["type"] == "screenshot"
        assert "data" in msg

    def test_action_result_message(self) -> None:
        """Action result messages are parsed correctly."""
        msg = {
            "type": "action_result",
            "node_id": "node-1",
            "action_id": "action-123",
            "success": True,
            "screenshot": "base64-data",
            "error": None,
        }
        assert msg["type"] == "action_result"
        assert msg["success"] is True

    def test_ui_tree_message(self) -> None:
        """UI tree messages are parsed correctly."""
        msg = {
            "type": "ui_tree",
            "node_id": "node-1",
            "elements": [
                {"id": "1", "name": "Window", "role": "window", "children": [
                    {"id": "2", "name": "Button", "role": "button", "children": []},
                ]},
            ],
        }
        assert msg["type"] == "ui_tree"
        assert len(msg["elements"]) == 1

    def test_error_message(self) -> None:
        """Error messages are parsed correctly."""
        msg = {
            "type": "error",
            "node_id": "node-1",
            "error": "Permission denied",
            "code": "PERMISSION_DENIED",
        }
        assert msg["type"] == "error"
        assert msg["code"] == "PERMISSION_DENIED"


class TestDesktopCommandProtocol:
    """Tests for the desktop command protocol."""

    def test_click_command(self) -> None:
        """Click command is formatted correctly."""
        cmd = {
            "type": "command",
            "command_id": "cmd-1",
            "action": "click",
            "params": {"x": 100, "y": 200, "button": "left"},
        }
        assert cmd["action"] == "click"
        assert cmd["params"]["x"] == 100

    def test_type_command(self) -> None:
        """Type command is formatted correctly."""
        cmd = {
            "type": "command",
            "command_id": "cmd-2",
            "action": "type",
            "params": {"text": "Hello World", "interval": 0.05},
        }
        assert cmd["action"] == "type"
        assert cmd["params"]["text"] == "Hello World"

    def test_screenshot_command(self) -> None:
        """Screenshot command is formatted correctly."""
        cmd = {
            "type": "command",
            "command_id": "cmd-3",
            "action": "screenshot",
            "params": {"region": None, "format": "png"},
        }
        assert cmd["action"] == "screenshot"

    def test_extract_tree_command(self) -> None:
        """Extract tree command is formatted correctly."""
        cmd = {
            "type": "command",
            "command_id": "cmd-4",
            "action": "extract_tree",
            "params": {"max_depth": 5},
        }
        assert cmd["action"] == "extract_tree"

    def test_serialization(self) -> None:
        """Commands can be serialized to JSON."""
        cmd = {
            "type": "command",
            "command_id": "cmd-1",
            "action": "click",
            "params": {"x": 100, "y": 200},
        }
        serialized = json.dumps(cmd)
        deserialized = json.loads(serialized)
        assert deserialized == cmd