# drupal2directus-migrator

[![CI](https://github.com/nagyonmarci/drupal2directus-migrator/actions/workflows/ci.yml/badge.svg)](https://github.com/nagyonmarci/drupal2directus-migrator/actions/workflows/ci.yml)
[![CD](https://github.com/nagyonmarci/drupal2directus-migrator/actions/workflows/cd.yml/badge.svg)](https://github.com/nagyonmarci/drupal2directus-migrator/actions/workflows/cd.yml)

A complete, phased Python migration toolkit to move a Drupal 10 CMS to Directus 11. Ships with a web UI and runs entirely in Docker. Scripts are idempotent, state-tracked, and fully logged — safe to re-run after any failure.

## Features

- **Web UI** — browser-based interface to configure source/target site pairs, select migration phases, and monitor live log output
- **Incremental / resumable** — every migrated entity is recorded in `migration_state.json`; re-running a phase skips already-completed records
- **Dual Drupal source** — schema, users, and file metadata are read directly from MySQL; node content is fetched via the Drupal JSON:API REST API
- **Full entity coverage** — content types, taxonomy, users, roles, files, blocks, and views
- **Directus Views → Presets** — Drupal Views are translated into Directus Data Studio Presets (via API) and Markdown/GraphQL query template files
- **Secure user migration** — Drupal password hashes are never copied; each user receives a cryptographically random placeholder password and can reset via the standard "Forgot Password" flow

---

## Requirements

- Docker + Docker Compose
- Access to the Drupal 10 MySQL database
- Drupal site reachable via HTTP (for JSON:API and file downloads)
- A running Directus 11 instance with a static admin token

---

## Quick start (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/nagyonmarci/drupal2directus-migrator.git
cd drupal2directus-migrator

# 2. Copy env template (only needed if running migrate.py directly)
cp .env.example .env

# 3. Build and start
docker compose up --build -d
```

Open **http://localhost:3000** in your browser.

- The web UI lets you add source/target connection pairs, select which phases to run, and stream live logs.
- The FastAPI Swagger UI is available at **http://localhost:8000/docs**.

### Production deployment

```bash
# Pull pre-built images from GHCR and start
docker compose -f docker-compose.prod.yml up -d
```

### `.env` variables

| Variable | Description |
|---|---|
| `DRUPAL_DB_HOST` | MySQL host |
| `DRUPAL_DB_PORT` | MySQL port (default `3306`) |
| `DRUPAL_DB_NAME` | Drupal database name |
| `DRUPAL_DB_USER` | Database user |
| `DRUPAL_DB_PASSWORD` | Database password |
| `DRUPAL_BASE_URL` | Drupal site URL, e.g. `https://mysite.com` |
| `DRUPAL_API_USER` | Drupal username for REST API auth |
| `DRUPAL_API_PASSWORD` | Drupal password for REST API auth |
| `DIRECTUS_URL` | Directus instance URL, e.g. `https://directus.mysite.com` |
| `DIRECTUS_ADMIN_TOKEN` | Static admin token from Directus settings |

---

## Usage

### Run all phases in sequence

```bash
python migrate.py --phase all
```

### Run a specific phase

```bash
python migrate.py --phase 2
```

### Run multiple phases

```bash
python migrate.py --phase 3,4
```

### Dry-run (validate without writing)

```bash
python migrate.py --phase 2 --dry-run
```

### Run a phase script directly

```bash
python scripts/phase1_verify.py
```

---

## Migration Phases

### Phase 1 — Preflight Verification
Checks connectivity to the Drupal MySQL database, Drupal REST API, and Directus API. Prints a summary table of record counts.

```bash
python scripts/phase1_verify.py
```

### Phase 2 — Schema Extraction & Creation
Reads Drupal content types, fields, and taxonomy vocabularies from the database. Creates equivalent Directus collections and fields, including M2M junction collections for taxonomy relations.

**Drupal → Directus field type mapping:**

| Drupal | Directus |
|---|---|
| `string`, `string_long` | `string` |
| `text_long`, `text_with_summary` | `text` |
| `integer` | `integer` |
| `boolean` | `boolean` |
| `datetime` | `dateTime` |
| `image`, `file` | `uuid` → `directus_files` |
| `entity_reference` (taxonomy) | M2M junction collection |
| `entity_reference` (node) | `integer` (M2O) |
| `link`, `geofield`, `address` | `json` |

### Phase 3 — Identity & Access Migration
Migrates Drupal roles to Directus roles, then migrates all active users. Drupal's `administrator` role maps to the existing Directus `Administrator` role. Each user is created with `status: active` and a 32-byte random placeholder password. Drupal password hashes are never used.

### Phase 4 — Media & File Migration
Reads the `file_managed` table, downloads each file from `sites/default/files/`, and uploads it to Directus via the Files API. File ID mappings (`drupal_fid → directus_file_uuid`) are stored in the state file for use in Phase 5.

### Phase 5 — Content & Relational Data Migration
Fetches node content via the Drupal JSON:API (paginated) and supplementary field values from the database. Resolves file, user, and taxonomy references using the Phase 3/4 ID maps. Creates items in the corresponding Directus collections and writes M2M junction records for taxonomy relations.

Drupal-specific tokens (`[node:...]`, `[site:...]`) and embed tags are stripped from body HTML.

### Phase 6 — Blocks & Views
**Blocks:** Reads custom block content and migrates it into a `global_blocks` Directus collection.

**Views:** For each Drupal View:
1. Creates a Directus Data Studio **Preset** via the API (with filters, sort, and limit)
2. Generates a `views_output/<view_name>.md` file with equivalent Directus REST and GraphQL query templates
3. Writes a master `views_output/views_documentation.md` index

---

## Project Structure

```
drupal2directus-migrator/
├── migrate.py                  # CLI orchestrator
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py               # Env var loading & validation
│   ├── logger.py               # Rotating file + console logging
│   ├── state.py                # StateTracker — idempotency via migration_state.json
│   ├── drupal/
│   │   ├── db.py               # MySQL connection pool
│   │   ├── api_client.py       # Drupal JSON:API REST client
│   │   ├── schema_reader.py    # Content types, fields, taxonomies
│   │   ├── user_reader.py      # Users and roles
│   │   ├── file_reader.py      # file_managed table
│   │   ├── content_reader.py   # Nodes + body cleanup
│   │   └── views_reader.py     # Views config + custom blocks
│   └── directus/
│       ├── client.py           # Directus REST client (auth, retry, upload)
│       ├── schema_writer.py    # Collection + field creation
│       ├── user_writer.py      # Role + user creation
│       ├── file_writer.py      # File download + upload
│       ├── content_writer.py   # Item + M2M junction creation
│       └── views_writer.py     # Presets + query template generation
└── scripts/
    ├── phase1_verify.py
    ├── phase2_schema.py
    ├── phase3_users.py
    ├── phase4_files.py
    ├── phase5_content.py
    └── phase6_blocks_views.py
```

---

## State File

`migration_state.json` is created automatically on first run and tracks all migrated entity IDs:

```json
{
  "files":  { "<drupal_fid>": "<directus_file_uuid>", ... },
  "users":  { "<drupal_uid>": "<directus_user_uuid>", ... },
  "roles":  { "<drupal_rid>": "<directus_role_uuid>", ... },
  "nodes":  { "<drupal_nid>": "<directus_item_id>",   ... },
  "terms":  { "<drupal_tid>": "<directus_item_id>",   ... },
  "blocks": { "<drupal_bid>": "<directus_item_id>",   ... },
  "views":  { "<view_name>":  "<directus_preset_id>", ... }
}
```

This file is gitignored. Back it up between runs on large datasets.

---

## Logs

All runs write to `logs/migration.log` (rotating, max 10 MB × 5 files). The console shows INFO-level output; the log file includes DEBUG detail.

---

## Post-Migration: User Password Reset

Users are migrated with placeholder passwords. To let them set their own:

1. Ensure Directus has SMTP configured under **Settings → Email**
2. Direct users to the Directus login page and have them use **Forgot Password**
3. Directus will send a reset link to their migrated email address

No additional scripting is required.
