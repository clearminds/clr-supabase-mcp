# clr-supabase-mcp

MCP server for self-hosted Supabase instances with multi-instance support.

## Features

- Schema introspection, SQL execution, migrations
- Auth user management (GoTrue)
- Storage bucket/object management
- Edge function management
- Multi-instance support via credentials.json
- Module-based tool loading (--modules flag)

## Installation

```bash
pip install clr-supabase-mcp
```

## Configuration

Create `~/.config/supabase/credentials.json`:

```json
{
  "instances": {
    "prod": {
      "url": "https://supabase.prod.example.com",
      "service_key": "eyJ...",
      "db_url": "postgresql://postgres:pass@db:5432/postgres"
    }
  },
  "default": "prod"
}
```
