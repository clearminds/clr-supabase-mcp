# clr-supabase-mcp

MCP server for self-hosted Supabase instances with multi-instance support.

## Features

- Schema introspection, SQL execution, migrations
- Auth user management (GoTrue)
- Storage bucket/object management
- Edge function management
- Multi-instance support via credentials.json
- Module-based tool loading (`--modules` flag)
- Read-only mode

## Installation

```bash
pip install clr-supabase-mcp
```

## Configuration

### Step 1: Create the credentials directory

```bash
mkdir -p ~/.config/supabase
```

### Step 2: Find your Supabase credentials

You need three values from your self-hosted Supabase deployment:

**1. Supabase URL** — The public Kong gateway URL for your instance. This is the URL you use to access the Supabase API (e.g. `https://supabase.example.com`). If you're running Supabase locally via Docker, this is typically `http://localhost:8000`.

**2. Service Role Key** — The `service_role` JWT key that grants admin access. Find it in your Supabase `.env` file:
```bash
# In your Supabase deployment directory:
grep SERVICE_ROLE_KEY .env
# or look for the value of SUPABASE_SERVICE_ROLE_KEY
```
This key looks like `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (a long JWT token).

**3. Database URL** — Direct PostgreSQL connection string. Build it from values in your Supabase `.env` file:
```
postgresql://postgres:YOUR_POSTGRES_PASSWORD@YOUR_DB_HOST:5432/postgres
```

Find the password:
```bash
grep POSTGRES_PASSWORD .env
```

The DB host depends on your setup:
- **Docker on same machine:** `localhost` (or the mapped port, check `docker compose ps`)
- **Remote server:** The hostname/IP of your database server
- **Docker network name:** `db` (if connecting from within the same Docker network)

### Step 3: Create credentials.json

**Single instance:**

```bash
cat > ~/.config/supabase/credentials.json << 'EOF'
{
  "url": "https://supabase.example.com",
  "service_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "db_url": "postgresql://postgres:your-db-password@db-host:5432/postgres"
}
EOF
chmod 600 ~/.config/supabase/credentials.json
```

**Multiple instances:**

```bash
cat > ~/.config/supabase/credentials.json << 'EOF'
{
  "instances": {
    "prod": {
      "url": "https://supabase-prod.example.com",
      "service_key": "eyJ...-prod-key",
      "db_url": "postgresql://postgres:prodpass@prod-db:5432/postgres"
    },
    "dev": {
      "url": "https://supabase-dev.example.com",
      "service_key": "eyJ...-dev-key",
      "db_url": "postgresql://postgres:devpass@dev-db:5432/postgres"
    }
  },
  "default": "prod"
}
EOF
chmod 600 ~/.config/supabase/credentials.json
```

### Credential fields

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Supabase Kong gateway URL |
| `service_key` | Yes | Service role JWT (admin access for auth/storage/edge tools) |
| `db_url` | For SQL/schema tools | Direct PostgreSQL connection URL |
| `anon_key` | No | Anon key (not needed when service_key is set) |

**Note:** `db_url` is only required for schema introspection and SQL tools (core and sql modules). Auth, storage, and edge modules only need `url` and `service_key`.

### Environment variable fallback

If no credentials file exists, the server falls back to environment variables:

```bash
export SUPABASE_URL="https://supabase.example.com"
export SUPABASE_SERVICE_KEY="eyJ..."
export SUPABASE_DB_URL="postgresql://postgres:pass@db-host:5432/postgres"
```

## Usage

### All modules (default)

```bash
clr-supabase-mcp
```

### Specific modules

```bash
# Schema introspection only
clr-supabase-mcp --modules core

# SQL + auth
clr-supabase-mcp --modules sql,auth
```

Available modules: `core`, `sql`, `auth`, `storage`, `edge`

### Read-only mode

Disable write operations (SQL execution, migrations, user creation, etc.):

```bash
export SUPABASE_READ_ONLY=true
clr-supabase-mcp
```

## Modules

| Module | Tools | API | Requires |
|--------|-------|-----|----------|
| core | 19 | Direct Postgres | `db_url` |
| sql | 13 | Direct Postgres | `db_url` |
| auth | 5 | GoTrue REST `/auth/v1/` | `url` + `service_key` |
| storage | 4 | Storage REST `/storage/v1/` | `url` + `service_key` |
| edge | 5 | Functions REST `/functions/v1/` | `url` + `service_key` |
