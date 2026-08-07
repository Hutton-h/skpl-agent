"""Shared constants for the framework-builtin team tools.

Centralised here (rather than duplicated per-module) so contracts that
must agree across tools have exactly one source of truth. Adding a new
tool that touches the same invariant should import from here, not
redeclare the value.
"""
HANDLE_LEN: int = 8