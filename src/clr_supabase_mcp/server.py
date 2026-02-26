"""Supabase MCP Server — FastMCP tools for self-hosted Supabase."""

import argparse
import logging
import sys
from typing import Any

from fastmcp import FastMCP

from clr_supabase_mcp.config import Settings, configure_logging
from clr_supabase_mcp.clients import ClientManager
from clr_supabase_mcp.middleware import ToolValidationMiddleware
from clr_supabase_mcp.tools import ALL_MODULE_NAMES, MODULES, set_manager

WRITE_TOOLS = [
    "execute_sql",
    "apply_migration",
    "create_auth_user",
    "update_auth_user",
    "delete_auth_user",
    "update_storage_config",
    "invoke_edge_function",
    "rebuild_hooks",
]

_MODULE_LABELS = {
    "core": "Schema",
    "sql": "SQL",
    "auth": "Auth",
    "storage": "Storage",
    "edge": "Edge Functions",
}


def parse_cli_args() -> dict[str, Any]:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Supabase MCP Server")
    parser.add_argument("--supabase-url", type=str, help="Supabase URL")
    parser.add_argument("--supabase-service-key", type=str, help="Service role key")
    parser.add_argument("--supabase-db-url", type=str, help="PostgreSQL connection URL")
    parser.add_argument(
        "--transport", type=str, choices=["stdio", "http"], help="MCP transport"
    )
    parser.add_argument("--host", type=str, help="HTTP host")
    parser.add_argument("--port", type=int, help="HTTP port")
    parser.add_argument(
        "--log-level", type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    parser.add_argument(
        "--modules", type=str, default=None,
        help=f"Comma-separated modules to load. Available: {', '.join(ALL_MODULE_NAMES)}",
    )

    args = parser.parse_args()

    overlay: dict[str, Any] = {}
    if args.supabase_url is not None:
        overlay["supabase_url"] = args.supabase_url
    if args.supabase_service_key is not None:
        overlay["supabase_service_key"] = args.supabase_service_key
    if args.supabase_db_url is not None:
        overlay["supabase_db_url"] = args.supabase_db_url
    if args.transport is not None:
        overlay["transport"] = args.transport
    if args.host is not None:
        overlay["host"] = args.host
    if args.port is not None:
        overlay["port"] = args.port
    if args.log_level is not None:
        overlay["log_level"] = args.log_level

    overlay["_modules"] = args.modules
    return overlay


def _resolve_modules(raw: str | None) -> list[str]:
    """Parse --modules value into a validated list."""
    if raw is None:
        return list(ALL_MODULE_NAMES)
    names = [n.strip() for n in raw.split(",") if n.strip()]
    unknown = set(names) - set(ALL_MODULE_NAMES)
    if unknown:
        print(
            f"Unknown module(s): {', '.join(sorted(unknown))}. "
            f"Available: {', '.join(ALL_MODULE_NAMES)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return names


def _server_name(modules: list[str]) -> str:
    """Build a descriptive FastMCP server name."""
    if set(modules) == set(ALL_MODULE_NAMES):
        return "Supabase"
    labels = [_MODULE_LABELS.get(m, m.title()) for m in modules]
    return f"Supabase ({', '.join(labels)})"


def main() -> None:
    """Main entry point for the Supabase MCP server."""
    cli_overlay = parse_cli_args()
    modules_raw = cli_overlay.pop("_modules", None)
    modules = _resolve_modules(modules_raw)

    try:
        settings = Settings(**cli_overlay)
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    instances = settings.load_instances()
    if not instances:
        logger.error(
            "No Supabase instances configured. Set SUPABASE_URL env var "
            "or create ~/.config/supabase/credentials.json"
        )
        sys.exit(1)

    manager = ClientManager()
    for inst in instances.values():
        manager.add(inst)
    manager.set_default(settings.get_default_name())
    set_manager(manager)

    logger.info(
        "Supabase MCP: %d instance(s), modules=%s",
        len(instances), ",".join(modules),
    )

    name = _server_name(modules)
    mcp = FastMCP(name)
    mcp.add_middleware(ToolValidationMiddleware())

    tool_count = 0
    for mod_name in modules:
        tools = MODULES.get(mod_name, [])
        for func in tools:
            mcp.tool()(func)
            tool_count += 1
        logger.info("Loaded module '%s' (%d tools)", mod_name, len(tools))

    logger.info("Total tools registered: %d", tool_count)

    if settings.supabase_read_only and WRITE_TOOLS:
        removed = 0
        for tool_name in WRITE_TOOLS:
            try:
                mcp.remove_tool(tool_name)
                removed += 1
            except Exception:
                pass
        logger.info("Read-only mode: %d write tools removed", removed)

    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    elif settings.transport == "http":
        mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
