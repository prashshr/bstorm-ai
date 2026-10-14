#!/usr/bin/env bash
#
# Apply database migrations to an existing AI-Ensemble deployment.
#
# WHY THIS IS A MANUAL STEP
# ------------------------
# The application creates its schema at startup via init_db()
# (Base.metadata.create_all plus best-effort SQLite ALTER TABLE calls).
# That path is currently the *complete* schema authority: five of the twelve
# model tables (agent_personas, messages, search_history, session_store,
# user_settings) have no Alembic revision that creates them, so
# `alembic upgrade head` on its own would leave a database unable to serve
# ordinary traffic.
#
# Therefore this script does NOT replace startup initialisation, and no
# migration is run automatically by the application. Run it deliberately, with
# a backup, as described in docs/architecture.md ("Database migrations").
#
# USAGE
#   backend/scripts/migrate.sh            # migrate + verify
#   backend/scripts/migrate.sh --dry-run  # show what would happen, change nothing
#
# ENVIRONMENT
#   DATABASE_URL (or a repo-root .env) must point at the target database.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

cd "$BACKEND_DIR"

# Resolve DATABASE_URL from the environment, falling back to the repo .env.
if [ -z "${DATABASE_URL:-}" ] && [ -f "$PROJECT_ROOT/.env" ]; then
  # Only read the assignment; never source the file as shell code.
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$PROJECT_ROOT/.env" | tail -1 | cut -d= -f2- || true)"
  export DATABASE_URL
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set and no repo-root .env provides it." >&2
  exit 1
fi

echo "Target database: ${DATABASE_URL%%\?*}"   # strip any query string

case "$DATABASE_URL" in
  sqlite*)
    DB_PATH="$(printf '%s' "$DATABASE_URL" | sed -E 's#^sqlite:///##; s#^sqlite://##')"
    [ -f "$DB_PATH" ] || { echo "ERROR: SQLite file not found: $DB_PATH" >&2; exit 1; }
    SIZE_MB="$(( ($(stat -c%s "$DB_PATH") + 1048575) / 1048576 ))"
    echo "SQLite database: $DB_PATH (${SIZE_MB} MB)"
    ;;
  *)
    echo "Non-SQLite target: rely on your platform's managed backup before continuing."
    ;;
esac

if [ "$DRY_RUN" = "1" ]; then
  echo "[dry-run] would back up, then run: alembic upgrade head"
  alembic current 2>/dev/null || echo "[dry-run] (no current revision recorded)"
  exit 0
fi

echo ""
echo "This will apply Alembic migrations to the database above."
read -r -p "Type 'migrate' to proceed: " CONFIRM
[ "$CONFIRM" = "migrate" ] || { echo "Aborted."; exit 1; }

BACKUP=""
case "$DATABASE_URL" in
  sqlite*)
    BACKUP="${DB_PATH}.pre-migrate-$(date -u +%Y%m%dT%H%M%SZ)"
    echo "==> Backing up to $BACKUP"
    # Online backup API, not a raw copy: safe while the app is running.
    python3 - "$DB_PATH" "$BACKUP" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
d = sqlite3.connect(dst)
with d:
    s.backup(d)
d.close(); s.close()
PY
    echo "    backup integrity: $(python3 -c "
import sqlite3,sys
print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])
" "$BACKUP")"
    ;;
esac

echo "==> Applying migrations"
if ! alembic upgrade head; then
  echo "ERROR: alembic upgrade head failed." >&2
  if [ -n "$BACKUP" ]; then
    echo "Restore with: cp '$BACKUP' '$DB_PATH'" >&2
  fi
  exit 1
fi

echo "==> Verifying expected tables exist after migration"
python3 - "$DATABASE_URL" <<'PY'
import sys, re
url = sys.argv[1]
if not url.startswith("sqlite"):
    print("    (skipped: only SQLite verification is implemented here)"); sys.exit(0)
path = re.sub(r"^sqlite:///", "", url)
import sqlite3
c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
tables = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}
required = {"users", "discussions", "messages", "provider_credentials", "search_history",
            "refresh_tokens", "session_store", "agent_personas", "user_settings"}
missing = sorted(required - tables)
if missing:
    print("    MISSING TABLES:", ", ".join(missing))
    print("    -> init_db() must run (start the app) to create these; Alembic")
    print("       does not yet have revisions that create them.")
    sys.exit(1)
print("    all expected tables present")
PY

echo ""
echo "Migration finished."
[ -n "$BACKUP" ] && echo "Rollback: cp '$BACKUP' '$DB_PATH'"
