"""Supabase SQL module — execution, stats, migrations, cron, pgvector, realtime."""

from __future__ import annotations

import logging
from typing import Any

from clr_supabase_mcp.tools import _register_module, get_manager

logger = logging.getLogger(__name__)


async def execute_sql(
    sql: str,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, str]:
    """Execute an arbitrary SQL query.

    For SELECT/WITH queries, returns result rows. For DDL/DML, returns status.
    Privileged — requires service_key.

    Args:
        sql: SQL statement to execute.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    trimmed = sql.strip().upper()
    if trimmed.startswith(("SELECT", "WITH", "EXPLAIN")):
        return await client.query(sql)
    else:
        status = await client.execute(sql)
        return {"status": status}


async def explain_query(
    sql: str,
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Run EXPLAIN ANALYZE on a query.

    Args:
        sql: SQL query to analyze.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
    )


async def get_database_connections(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Show active database connections from pg_stat_activity.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT pid, usename, application_name, client_addr,
               state, query_start, state_change,
               LEFT(query, 200) AS query_preview
        FROM pg_stat_activity
        WHERE datname = current_database()
        ORDER BY state_change DESC
        LIMIT 50
        """
    )


async def get_database_stats(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve database statistics from pg_stat_database.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT datname, numbackends, xact_commit, xact_rollback,
               blks_read, blks_hit,
               CASE WHEN blks_read + blks_hit > 0
                    THEN ROUND(blks_hit::numeric / (blks_read + blks_hit) * 100, 2)
                    ELSE 0 END AS cache_hit_ratio,
               tup_returned, tup_fetched, tup_inserted,
               tup_updated, tup_deleted,
               pg_size_pretty(pg_database_size(datname)) AS db_size
        FROM pg_stat_database
        WHERE datname = current_database()
        """
    )


async def get_index_stats(
    schema: str = "public",
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Show index usage statistics.

    Args:
        schema: Schema name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT schemaname, relname AS table_name,
               indexrelname AS index_name,
               idx_scan AS times_used,
               idx_tup_read, idx_tup_fetch,
               pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = $1
        ORDER BY idx_scan DESC
        """,
        schema,
    )


async def list_migrations(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List applied Supabase migrations.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        return await client.query(
            """
            SELECT version, name, statements
            FROM supabase_migrations.schema_migrations
            ORDER BY version DESC
            """
        )
    except Exception:
        return [{"info": "supabase_migrations.schema_migrations table not found"}]


async def apply_migration(
    name: str,
    sql: str,
    instance: str | None = None,
) -> dict[str, str]:
    """Apply a SQL migration and record it. Privileged.

    Args:
        name: Migration name/label.
        sql: SQL statements to execute.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    await client.execute(sql)
    try:
        await client.execute(
            """
            INSERT INTO supabase_migrations.schema_migrations (version, name, statements)
            VALUES (to_char(now(), 'YYYYMMDDHH24MISS'), $1, $2)
            """,
            name, sql,
        )
    except Exception as e:
        logger.warning("Migration applied but could not record: %s", e)
    return {"status": "applied", "name": name}


async def list_cron_jobs(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List scheduled pg_cron jobs (requires pg_cron extension).

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        return await client.query(
            """
            SELECT jobid, schedule, command, nodename, nodeport,
                   database, username, active
            FROM cron.job
            ORDER BY jobid
            """
        )
    except Exception:
        return [{"info": "pg_cron extension not installed or accessible"}]


async def get_cron_job_history(
    job_id: int,
    limit: int = 20,
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Show recent execution history for a cron job.

    Args:
        job_id: The cron job ID.
        limit: Max rows to return.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        return await client.query(
            """
            SELECT runid, job_pid, status, return_message,
                   start_time, end_time
            FROM cron.job_run_details
            WHERE jobid = $1
            ORDER BY start_time DESC
            LIMIT $2
            """,
            job_id, limit,
        )
    except Exception:
        return [{"info": "pg_cron extension not installed or cron.job_run_details not available"}]


async def list_vector_indexes(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List pgvector indexes (requires pgvector extension).

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT schemaname, tablename, indexname, indexdef,
               pg_size_pretty(pg_relation_size(schemaname || '.' || indexname)) AS index_size
        FROM pg_indexes
        WHERE indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%hnsw%'
        ORDER BY schemaname, tablename, indexname
        """
    )


async def get_vector_index_stats(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """Show pgvector index usage statistics.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT s.schemaname, s.relname AS table_name,
               s.indexrelname AS index_name,
               s.idx_scan AS times_used,
               pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size
        FROM pg_stat_user_indexes s
        JOIN pg_indexes i ON s.indexrelname = i.indexname
            AND s.schemaname = i.schemaname
        WHERE i.indexdef ILIKE '%ivfflat%' OR i.indexdef ILIKE '%hnsw%'
        ORDER BY s.idx_scan DESC
        """
    )


async def list_realtime_publications(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List PostgreSQL publications used for Supabase Realtime.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.query(
        """
        SELECT p.pubname AS publication_name,
               p.puballtables AS all_tables,
               pt.schemaname, pt.tablename
        FROM pg_publication p
        LEFT JOIN pg_publication_tables pt ON p.pubname = pt.pubname
        ORDER BY p.pubname, pt.tablename
        """
    )


async def rebuild_hooks(
    instance: str | None = None,
) -> dict[str, str]:
    """Restart pg_net worker and notify PostgREST to reload schema. Privileged.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    try:
        await client.execute("SELECT pg_notify('pgrst', 'reload schema')")
        return {"status": "schema reload notification sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


TOOLS = [
    execute_sql,
    explain_query,
    get_database_connections,
    get_database_stats,
    get_index_stats,
    list_migrations,
    apply_migration,
    list_cron_jobs,
    get_cron_job_history,
    list_vector_indexes,
    get_vector_index_stats,
    list_realtime_publications,
    rebuild_hooks,
]

_register_module("sql", TOOLS)
