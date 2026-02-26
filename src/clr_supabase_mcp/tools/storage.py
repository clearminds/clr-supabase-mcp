"""Supabase storage module — bucket and object management."""

from __future__ import annotations

from typing import Any

from clr_supabase_mcp.tools import _register_module, get_manager


async def list_storage_buckets(
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List all storage buckets.

    Args:
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.get("/storage/v1/bucket")


async def list_storage_objects(
    bucket_id: str,
    prefix: str = "",
    limit: int = 100,
    offset: int = 0,
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List objects in a storage bucket.

    Args:
        bucket_id: Bucket ID/name.
        prefix: Filter by path prefix.
        limit: Max objects to return.
        offset: Pagination offset.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    body: dict[str, Any] = {
        "prefix": prefix,
        "limit": limit,
        "offset": offset,
    }
    return await client.post(f"/storage/v1/object/list/{bucket_id}", json=body)


async def get_storage_config(
    bucket_id: str,
    instance: str | None = None,
) -> dict[str, Any]:
    """Get configuration for a storage bucket.

    Args:
        bucket_id: Bucket ID/name.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.get(f"/storage/v1/bucket/{bucket_id}")


async def update_storage_config(
    bucket_id: str,
    public: bool | None = None,
    file_size_limit: int | None = None,
    allowed_mime_types: list[str] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update storage bucket configuration. Privileged.

    Args:
        bucket_id: Bucket ID/name.
        public: Make bucket public/private.
        file_size_limit: Max file size in bytes.
        allowed_mime_types: List of allowed MIME types.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    body: dict[str, Any] = {}
    if public is not None:
        body["public"] = public
    if file_size_limit is not None:
        body["file_size_limit"] = file_size_limit
    if allowed_mime_types is not None:
        body["allowed_mime_types"] = allowed_mime_types
    return await client.put(f"/storage/v1/bucket/{bucket_id}", json=body)


TOOLS = [
    list_storage_buckets,
    list_storage_objects,
    get_storage_config,
    update_storage_config,
]

_register_module("storage", TOOLS)
