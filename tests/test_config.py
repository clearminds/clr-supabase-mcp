"""Tests for Supabase credential loading."""

import json

import pytest

from clr_supabase_mcp.config import Settings, SupabaseInstance


def test_single_instance_from_file(tmp_path, monkeypatch):
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "url": "https://supabase.example.com",
        "service_key": "sk-test",
        "db_url": "postgresql://postgres:pass@db:5432/postgres",
    }))
    monkeypatch.setattr("clr_supabase_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    settings = Settings()
    instances = settings.load_instances()

    assert "default" in instances
    inst = instances["default"]
    assert inst.url == "https://supabase.example.com"
    assert inst.service_key == "sk-test"
    assert inst.db_url == "postgresql://postgres:pass@db:5432/postgres"


def test_multi_instance_from_file(tmp_path, monkeypatch):
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "instances": {
            "prod": {
                "url": "https://prod.example.com",
                "service_key": "sk-prod",
                "db_url": "postgresql://postgres:pass@prod:5432/postgres",
            },
            "dev": {
                "url": "https://dev.example.com",
                "service_key": "sk-dev",
                "db_url": "postgresql://postgres:pass@dev:5432/postgres",
            },
        },
        "default": "prod",
    }))
    monkeypatch.setattr("clr_supabase_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    settings = Settings()
    instances = settings.load_instances()

    assert len(instances) == 2
    assert instances["prod"].url == "https://prod.example.com"
    assert instances["dev"].url == "https://dev.example.com"
    assert settings.get_default_name() == "prod"


def test_env_vars_as_fallback(tmp_path, monkeypatch):
    creds_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("clr_supabase_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.setenv("SUPABASE_URL", "https://env.example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sk-env")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://postgres:pass@env:5432/postgres")

    settings = Settings()
    instances = settings.load_instances()

    assert "default" in instances
    assert instances["default"].url == "https://env.example.com"


def test_file_overrides_env(tmp_path, monkeypatch):
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps({
        "url": "https://file.example.com",
        "service_key": "sk-file",
        "db_url": "postgresql://postgres:pass@file:5432/postgres",
    }))
    monkeypatch.setattr("clr_supabase_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.setenv("SUPABASE_URL", "https://env.example.com")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sk-env")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://postgres:pass@env:5432/postgres")

    settings = Settings()
    instances = settings.load_instances()

    assert instances["default"].url == "https://file.example.com"
    assert instances["default"].service_key == "sk-file"


def test_no_credentials(tmp_path, monkeypatch):
    creds_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("clr_supabase_mcp.config.CREDS_PATH", creds_file)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    settings = Settings()
    instances = settings.load_instances()

    assert instances == {}


def test_empty_read_only_string(monkeypatch):
    monkeypatch.setenv("SUPABASE_READ_ONLY", "")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    settings = Settings()
    assert settings.supabase_read_only is False
