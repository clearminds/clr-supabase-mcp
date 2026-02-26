"""Supabase auth module — GoTrue user management."""

from __future__ import annotations

from typing import Any

from clr_supabase_mcp.tools import _register_module, get_manager


async def list_auth_users(
    page: int = 1,
    per_page: int = 50,
    instance: str | None = None,
) -> dict[str, Any]:
    """List auth users.

    Args:
        page: Page number (1-indexed).
        per_page: Users per page (max 1000).
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.get(
        "/auth/v1/admin/users",
        params={"page": page, "per_page": per_page},
    )


async def get_auth_user(
    user_id: str,
    instance: str | None = None,
) -> dict[str, Any]:
    """Get details for a specific auth user.

    Args:
        user_id: User UUID.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.get(f"/auth/v1/admin/users/{user_id}")


async def create_auth_user(
    email: str,
    password: str,
    email_confirm: bool = True,
    user_metadata: dict[str, Any] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a new auth user. Privileged — requires service_key.

    Args:
        email: User email address.
        password: User password.
        email_confirm: Auto-confirm email (default: True).
        user_metadata: Optional metadata dict.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    body: dict[str, Any] = {
        "email": email,
        "password": password,
        "email_confirm": email_confirm,
    }
    if user_metadata:
        body["user_metadata"] = user_metadata
    return await client.post("/auth/v1/admin/users", json=body)


async def update_auth_user(
    user_id: str,
    email: str | None = None,
    password: str | None = None,
    user_metadata: dict[str, Any] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update an existing auth user. Privileged.

    Args:
        user_id: User UUID.
        email: New email address.
        password: New password.
        user_metadata: Metadata to merge.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    body: dict[str, Any] = {}
    if email is not None:
        body["email"] = email
    if password is not None:
        body["password"] = password
    if user_metadata is not None:
        body["user_metadata"] = user_metadata
    return await client.put(f"/auth/v1/admin/users/{user_id}", json=body)


async def delete_auth_user(
    user_id: str,
    instance: str | None = None,
) -> dict[str, str]:
    """Delete an auth user. Privileged.

    Args:
        user_id: User UUID.
        instance: Supabase instance name.
    """
    client = get_manager().get(instance)
    return await client.delete(f"/auth/v1/admin/users/{user_id}")


TOOLS = [
    list_auth_users,
    get_auth_user,
    create_auth_user,
    update_auth_user,
    delete_auth_user,
]

_register_module("auth", TOOLS)
