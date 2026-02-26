"""Configuration for Supabase MCP Server.

Credential loading follows the Clearminds standard pattern:
1. Load from ~/.config/supabase/credentials.json FIRST
2. Override with environment variables

Supports single-instance and multi-instance configurations.
"""

import json
import logging
import logging.config
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

CREDS_PATH = Path.home() / ".config" / "supabase" / "credentials.json"


class SupabaseInstance:
    """A single Supabase instance connection."""

    def __init__(
        self,
        name: str,
        url: str,
        anon_key: str = "",
        service_key: str = "",
        db_url: str = "",
    ) -> None:
        self.name = name
        self.url = url.rstrip("/")
        self.anon_key = anon_key
        self.service_key = service_key
        self.db_url = db_url


class Settings(BaseSettings):
    """Settings for the Supabase MCP server."""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_db_url: str = ""
    supabase_read_only: bool = False

    @field_validator("supabase_read_only", mode="before")
    @classmethod
    def _empty_str_to_false(cls, v: Any) -> Any:
        if v == "":
            return False
        return v

    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def load_instances(self) -> dict[str, SupabaseInstance]:
        """Load Supabase instances from env vars or credentials.json.

        Supports two formats in credentials.json:

        Single instance:
            {"url": "...", "service_key": "...", "db_url": "..."}

        Multi-instance:
            {
                "instances": {
                    "prod": {"url": "...", "service_key": "...", "db_url": "..."},
                    "dev": {"url": "...", "service_key": "...", "db_url": "..."}
                },
                "default": "prod"
            }
        """
        instances: dict[str, SupabaseInstance] = {}

        # 1. FIRST: Load from environment variables (base/fallback)
        if self.supabase_url:
            instances["default"] = SupabaseInstance(
                name="default",
                url=self.supabase_url,
                anon_key=self.supabase_anon_key,
                service_key=self.supabase_service_key,
                db_url=self.supabase_db_url,
            )

        # 2. THEN: Override with credentials.json file (takes priority)
        if CREDS_PATH.exists():
            try:
                data: dict[str, Any] = json.loads(CREDS_PATH.read_text())

                if "instances" in data:
                    instances.clear()
                    for name, cfg in data["instances"].items():
                        instances[name] = SupabaseInstance(
                            name=name,
                            url=cfg["url"],
                            anon_key=cfg.get("anon_key", ""),
                            service_key=cfg.get("service_key", ""),
                            db_url=cfg.get("db_url", ""),
                        )
                    logger.info(
                        "Loaded %d Supabase instance(s) from %s",
                        len(instances), CREDS_PATH,
                    )
                elif data.get("url"):
                    instances["default"] = SupabaseInstance(
                        name="default",
                        url=data["url"],
                        anon_key=data.get("anon_key", ""),
                        service_key=data.get("service_key", ""),
                        db_url=data.get("db_url", ""),
                    )
                    logger.info("Loaded Supabase credentials from %s", CREDS_PATH)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load %s: %s", CREDS_PATH, e)

        if not instances:
            logger.warning(
                "No Supabase instances configured. Set SUPABASE_URL env var "
                "or create %s", CREDS_PATH,
            )

        return instances

    def get_default_name(self) -> str:
        """Get the default instance name from credentials.json."""
        if CREDS_PATH.exists():
            try:
                data: dict[str, Any] = json.loads(CREDS_PATH.read_text())
                if "default" in data:
                    return data["default"]
                if "instances" in data:
                    return next(iter(data["instances"]))
            except (json.JSONDecodeError, KeyError):
                pass
        return "default"


def configure_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
) -> None:
    """Configure application-wide logging."""
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "httpx": {"level": "WARNING"},
            "asyncpg": {"level": "WARNING"},
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }
    logging.config.dictConfig(config)
