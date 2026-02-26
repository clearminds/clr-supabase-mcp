"""Supabase edge module — edge functions and logs."""

from __future__ import annotations

import logging
from typing import Any

from clr_supabase_mcp.tools import _register_module, get_manager

logger = logging.getLogger(__name__)


async def list_edge_functions(
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, str]:
    """List deployed edge functions.

    Note: Self-hosted Supabase may not expose a function listing API.
    Falls back to a helpful message if not available.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        # Try the management API endpoint used by Supabase Dashboard
        return await client.get("/functions/v1/")
    except Exception:
        return {"info": (
            "Edge function listing not available via API. "
            "Functions are deployed in volumes/functions/ on the Supabase host. "
            "Use invoke_edge_function to call a known function by name."
        )}


async def get_edge_function_details(
    function_name: str,
    instance: str | None = None,
) -> dict[str, Any]:
    """Get metadata for an edge function.

    Args:
        function_name: Name of the edge function.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        return await client.get(f"/functions/v1/{function_name}", params={"__meta": "true"})
    except Exception:
        return {
            "function_name": function_name,
            "info": "Function metadata not available. Try invoke_edge_function to test it.",
        }


async def list_edge_function_logs(
    function_name: str,
    limit: int = 50,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, str]:
    """Retrieve recent logs for an edge function.

    Note: Log access depends on the self-hosted Supabase logging configuration.

    Args:
        function_name: Name of the edge function.
        limit: Max log entries to return.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        return await client.get(
            "/functions/v1/logs",
            params={"function_name": function_name, "limit": limit},
        )
    except Exception:
        return {"info": (
            f"Logs for '{function_name}' not available via API. "
            "Check Docker logs: docker logs supabase-edge-functions"
        )}


async def invoke_edge_function(
    function_name: str,
    body: dict[str, Any] | None = None,
    instance: str | None = None,
) -> Any:
    """Invoke an edge function. Privileged.

    Args:
        function_name: Name of the edge function.
        body: JSON body to send to the function.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    kwargs: dict[str, Any] = {}
    if body is not None:
        kwargs["json"] = body
    return await client.post(f"/functions/v1/{function_name}", **kwargs)


async def get_logs(
    service: str = "all",
    limit: int = 100,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, str]:
    """Retrieve general Supabase logs.

    Note: Log access depends on the self-hosted logging/analytics configuration.

    Args:
        service: Service to filter logs (e.g., 'auth', 'rest', 'storage', 'all').
        limit: Max log entries.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        # Try the analytics endpoint if available
        return await client.get(
            "/analytics/v1/logs",
            params={"source": service, "limit": limit},
        )
    except Exception:
        return {"info": (
            "Log API not available on this self-hosted instance. "
            "Check Docker logs directly: docker logs supabase-<service>"
        )}


TOOLS = [
    list_edge_functions,
    get_edge_function_details,
    list_edge_function_logs,
    invoke_edge_function,
    get_logs,
]

_register_module("edge", TOOLS)
