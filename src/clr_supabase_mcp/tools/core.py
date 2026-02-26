"""Supabase core module — schema introspection, RLS, extensions, system."""

from __future__ import annotations

from typing import Any

from clr_supabase_mcp.tools import _register_module, get_manager


async def list_tables(
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List tables in a database schema.

    Args:
        schema: Database schema name (default: public).
        instance: Supabase instance name (default: configured default).
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = $1
        ORDER BY table_name
        """,
        schema,
    )


async def list_table_columns(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List columns for a specific table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT column_name, data_type, is_nullable, column_default,
               character_maximum_length, numeric_precision
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
        """,
        schema, table,
    )


async def list_indexes(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List indexes for a specific table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = $1 AND tablename = $2
        ORDER BY indexname
        """,
        schema, table,
    )


async def list_constraints(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List constraints for a specific table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY constraint_name
        """,
        schema, table,
    )


async def list_foreign_keys(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List foreign keys for a specific table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT
            kcu.constraint_name,
            kcu.column_name,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.referential_constraints rc
            ON kcu.constraint_name = rc.constraint_name
            AND kcu.constraint_schema = rc.constraint_schema
        JOIN information_schema.constraint_column_usage ccu
            ON rc.unique_constraint_name = ccu.constraint_name
            AND rc.unique_constraint_schema = ccu.constraint_schema
        WHERE kcu.table_schema = $1 AND kcu.table_name = $2
        ORDER BY kcu.constraint_name, kcu.ordinal_position
        """,
        schema, table,
    )


async def list_triggers(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List triggers for a specific table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT trigger_name, event_manipulation, action_timing,
               action_statement
        FROM information_schema.triggers
        WHERE event_object_schema = $1 AND event_object_table = $2
        ORDER BY trigger_name
        """,
        schema, table,
    )


async def list_database_functions(
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List user-defined database functions.

    Args:
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT p.proname AS function_name,
               pg_get_function_identity_arguments(p.oid) AS arguments,
               t.typname AS return_type,
               l.lanname AS language
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        JOIN pg_type t ON p.prorettype = t.oid
        JOIN pg_language l ON p.prolang = l.oid
        WHERE n.nspname = $1
        ORDER BY p.proname
        """,
        schema,
    )


async def get_function_definition(
    function_name: str,
    schema: str = "public",
    instance: str | None = None,
) -> dict[str, Any]:
    """Get the source definition of a database function.

    Args:
        function_name: Function name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    rows = await client.query(
        """
        SELECT p.proname AS function_name,
               pg_get_functiondef(p.oid) AS definition
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = $1 AND p.proname = $2
        LIMIT 1
        """,
        schema, function_name,
    )
    return rows[0] if rows else {"error": f"Function '{function_name}' not found in schema '{schema}'"}


async def get_trigger_definition(
    trigger_name: str,
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> dict[str, Any]:
    """Get the source definition of a trigger.

    Args:
        trigger_name: Trigger name.
        table: Table the trigger is on.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    rows = await client.query(
        """
        SELECT tg.tgname AS trigger_name,
               pg_get_triggerdef(tg.oid) AS definition
        FROM pg_trigger tg
        JOIN pg_class c ON tg.tgrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = $1 AND c.relname = $2 AND tg.tgname = $3
          AND NOT tg.tgisinternal
        LIMIT 1
        """,
        schema, table, trigger_name,
    )
    return rows[0] if rows else {"error": f"Trigger '{trigger_name}' not found"}


async def list_extensions(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List installed PostgreSQL extensions.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT e.extname AS name, e.extversion AS version,
               n.nspname AS schema, c.description
        FROM pg_extension e
        JOIN pg_namespace n ON e.extnamespace = n.oid
        LEFT JOIN pg_description c ON c.objoid = e.oid
        ORDER BY e.extname
        """
    )


async def list_available_extensions(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List all available (installable) PostgreSQL extensions.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT name, default_version, installed_version, comment
        FROM pg_available_extensions
        ORDER BY name
        """
    )


async def list_rls_policies(
    table: str,
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List Row-Level Security policies for a table.

    Args:
        table: Table name.
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT policyname, permissive, roles, cmd, qual, with_check
        FROM pg_policies
        WHERE schemaname = $1 AND tablename = $2
        ORDER BY policyname
        """,
        schema, table,
    )


async def get_rls_status(
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Show RLS enabled/disabled status for all tables in a schema.

    Args:
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT c.relname AS table_name,
               c.relrowsecurity AS rls_enabled,
               c.relforcerowsecurity AS rls_forced
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = $1 AND c.relkind = 'r'
        ORDER BY c.relname
        """,
        schema,
    )


async def get_advisors(
    instance: str | None = None,
) -> dict[str, Any]:
    """Get security and performance advisory information.

    Checks for common issues: unused indexes, tables without primary keys,
    tables without RLS in public schema.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)

    unused_indexes = await client.query(
        """
        SELECT schemaname, relname AS table_name, indexrelname AS index_name,
               idx_scan AS times_used
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0 AND schemaname = 'public'
        ORDER BY relname, indexrelname
        """
    )

    no_pk = await client.query(
        """
        SELECT t.table_schema, t.table_name
        FROM information_schema.tables t
        LEFT JOIN information_schema.table_constraints tc
            ON t.table_schema = tc.table_schema
            AND t.table_name = tc.table_name
            AND tc.constraint_type = 'PRIMARY KEY'
        WHERE t.table_schema = 'public'
            AND t.table_type = 'BASE TABLE'
            AND tc.constraint_name IS NULL
        ORDER BY t.table_name
        """
    )

    no_rls = await client.query(
        """
        SELECT c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = 'public'
            AND c.relkind = 'r'
            AND NOT c.relrowsecurity
        ORDER BY c.relname
        """
    )

    return {
        "unused_indexes": unused_indexes,
        "tables_without_primary_key": no_pk,
        "tables_without_rls": no_rls,
    }


async def generate_typescript_types(
    schema: str = "public",
    instance: str | None = None,
) -> str:
    """Generate TypeScript type definitions from database schema.

    Args:
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    tables = await client.query(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = $1 AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        schema,
    )

    pg_to_ts = {
        "integer": "number", "bigint": "number", "smallint": "number",
        "numeric": "number", "real": "number", "double precision": "number",
        "text": "string", "character varying": "string", "char": "string",
        "uuid": "string", "date": "string",
        "boolean": "boolean",
        "timestamp with time zone": "string", "timestamp without time zone": "string",
        "jsonb": "Record<string, unknown>", "json": "Record<string, unknown>",
    }

    lines = []
    for tbl in tables:
        name = tbl["table_name"]
        cols = await client.query(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
            """,
            schema, name,
        )
        interface_name = "".join(w.capitalize() for w in name.split("_"))
        lines.append(f"export interface {interface_name} {{")
        for col in cols:
            ts_type = pg_to_ts.get(col["data_type"], "unknown")
            nullable = " | null" if col["is_nullable"] == "YES" else ""
            lines.append(f"  {col['column_name']}: {ts_type}{nullable};")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


async def get_project_url(
    instance: str | None = None,
) -> dict[str, str]:
    """Return the configured Supabase URL for an instance.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return {
        "instance": client.instance.name,
        "url": client.instance.url,
    }


async def verify_jwt_secret(
    instance: str | None = None,
) -> dict[str, Any]:
    """Verify connectivity and check if service key is configured.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    result: dict[str, Any] = {
        "instance": client.instance.name,
        "url": client.instance.url,
        "has_service_key": bool(client.instance.service_key),
        "has_anon_key": bool(client.instance.anon_key),
        "has_db_url": bool(client.instance.db_url),
    }

    if client.instance.db_url:
        try:
            rows = await client.query("SELECT 1 AS connected")
            result["db_connected"] = True
        except Exception as e:
            result["db_connected"] = False
            result["db_error"] = str(e)

    return result


async def supabase_instances() -> list[dict[str, Any]]:
    """List all configured Supabase instances."""
    return get_manager().list_instances()


async def supabase_status(
    instance: str | None = None,
) -> dict[str, Any]:
    """Check connectivity status of a Supabase instance.

    Tests both HTTP API and database connectivity.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    status: dict[str, Any] = {
        "instance": client.instance.name,
        "url": client.instance.url,
    }

    # Test HTTP
    try:
        await client.get("/rest/v1/", params={"limit": "0"})
        status["http"] = "connected"
    except Exception as e:
        status["http"] = f"error: {e}"

    # Test DB
    if client.instance.db_url:
        try:
            rows = await client.query("SELECT version() AS version")
            status["db"] = "connected"
            status["pg_version"] = rows[0]["version"] if rows else "unknown"
        except Exception as e:
            status["db"] = f"error: {e}"
    else:
        status["db"] = "not configured (no db_url)"

    return status


TOOLS = [
    list_tables,
    list_table_columns,
    list_indexes,
    list_constraints,
    list_foreign_keys,
    list_triggers,
    list_database_functions,
    get_function_definition,
    get_trigger_definition,
    list_extensions,
    list_available_extensions,
    list_rls_policies,
    get_rls_status,
    get_advisors,
    generate_typescript_types,
    get_project_url,
    verify_jwt_secret,
    supabase_instances,
    supabase_status,
]

_register_module("core", TOOLS)
