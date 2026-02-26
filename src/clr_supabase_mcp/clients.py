"""HTTP and Postgres client management for Supabase instances."""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
import httpx

from clr_supabase_mcp.config import SupabaseInstance

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for a single Supabase instance.

    Provides httpx for REST APIs and asyncpg for direct Postgres.
    """

    def __init__(self, instance: SupabaseInstance) -> None:
        self.instance = instance
        self._http: httpx.AsyncClient | None = None
        self._pool: asyncpg.Pool | None = None

    def _get_http(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http is None or self._http.is_closed:
            headers = {}
            key = self.instance.service_key or self.instance.anon_key
            if key:
                headers["apikey"] = key
                headers["Authorization"] = f"Bearer {key}"
            self._http = httpx.AsyncClient(
                base_url=self.instance.url,
                headers=headers,
                timeout=30.0,
            )
        return self._http

    async def get(self, path: str, **kwargs: Any) -> Any:
        """HTTP GET request to the Supabase REST API."""
        resp = await self._get_http().get(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, **kwargs: Any) -> Any:
        """HTTP POST request."""
        resp = await self._get_http().post(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, **kwargs: Any) -> Any:
        """HTTP PUT request."""
        resp = await self._get_http().put(path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str, **kwargs: Any) -> Any:
        """HTTP DELETE request."""
        resp = await self._get_http().delete(path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return {"status": "deleted"}
        return resp.json()

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create the Postgres connection pool."""
        if self._pool is None:
            if not self.instance.db_url:
                raise RuntimeError(
                    f"No db_url configured for instance '{self.instance.name}'. "
                    "Set db_url in credentials.json or SUPABASE_DB_URL env var."
                )
            self._pool = await asyncpg.create_pool(
                self.instance.db_url,
                min_size=1,
                max_size=5,
            )
            logger.info("Postgres pool created for instance '%s'", self.instance.name)
        return self._pool

    async def query(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        """Execute a SQL query and return rows as dicts."""
        pool = await self._get_pool()
        rows = await pool.fetch(sql, *args)
        return [dict(row) for row in rows]

    async def execute(self, sql: str, *args: Any) -> str:
        """Execute a SQL statement and return status."""
        pool = await self._get_pool()
        return await pool.execute(sql, *args)

    async def close(self) -> None:
        """Close HTTP client and Postgres pool."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
        if self._pool:
            await self._pool.close()


class ClientManager:
    """Manages SupabaseClient instances for multi-instance support."""

    def __init__(self) -> None:
        self._clients: dict[str, SupabaseClient] = {}
        self._default: str = "default"

    def add(self, instance: SupabaseInstance) -> None:
        """Register a Supabase instance."""
        self._clients[instance.name] = SupabaseClient(instance)

    def set_default(self, name: str) -> None:
        """Set the default instance name."""
        self._default = name

    def get(self, instance: str | None = None) -> SupabaseClient:
        """Get a client by instance name, or the default."""
        name = instance or self._default
        if name not in self._clients:
            available = ", ".join(sorted(self._clients.keys()))
            raise ValueError(
                f"Unknown instance '{name}'. Available: {available}"
            )
        return self._clients[name]

    def list_instances(self) -> list[dict[str, Any]]:
        """List all configured instances."""
        return [
            {
                "name": name,
                "url": client.instance.url,
                "has_db": bool(client.instance.db_url),
                "has_service_key": bool(client.instance.service_key),
                "is_default": name == self._default,
            }
            for name, client in self._clients.items()
        ]

    async def close_all(self) -> None:
        """Close all clients."""
        for client in self._clients.values():
            await client.close()
