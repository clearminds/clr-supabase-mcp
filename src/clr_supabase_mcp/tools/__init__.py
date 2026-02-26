"""Supabase MCP tools — modular registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from clr_supabase_mcp.clients import ClientManager

_manager: ClientManager | None = None


def set_manager(m: ClientManager) -> None:
    """Set the shared ClientManager instance."""
    global _manager
    _manager = m


def get_manager() -> ClientManager:
    """Return the shared ClientManager, raising if not initialized."""
    assert _manager is not None, "ClientManager not initialized — call set_manager() first"
    return _manager


# Module registry — each value is a list of tool functions.
MODULES: dict[str, list[Callable[..., Any]]] = {}

ALL_MODULE_NAMES = ("core", "sql", "auth", "storage", "edge")


def _register_module(name: str, tools: list[Callable[..., Any]]) -> None:
    """Register a list of tool functions under a module name."""
    MODULES[name] = tools
