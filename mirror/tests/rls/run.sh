#!/usr/bin/env bash
# Adversarial RLS verification for supabase/migrations/0001_init.sql.
#
# Stands up a throwaway local Postgres, reconstructs the Supabase-provided
# auth/storage scaffolding that the migration depends on (00_scaffold.sql —
# real auth.uid()/storage.foldername() bodies), applies the migration UNCHANGED,
# then runs 10_adversarial.sql as the non-owner `authenticated` role (superusers
# bypass RLS) with the JWT `sub` claim set exactly like PostgREST does.
#
# Requires: postgresql-16 server binaries. Postgres refuses to run as root, so
# if invoked as root this uses `sudo -u postgres`.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MIG="$HERE/../../supabase/migrations/0001_init.sql"
PGBIN="${PGBIN:-/usr/lib/postgresql/16/bin}"
WORK="$(mktemp -d)"
PORT="${PORT:-5433}"
SOCK="$WORK/sock"; mkdir -p "$SOCK"

RUN=""
if [ "$(id -u)" = "0" ]; then RUN="sudo -u postgres"; chown -R postgres:postgres "$WORK"; fi
PSQL="$RUN psql -h $SOCK -p $PORT -U postgres -v ON_ERROR_STOP=1"

cleanup() { $RUN "$PGBIN/pg_ctl" -D "$WORK/data" stop >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

$RUN "$PGBIN/initdb" -U postgres -A trust "$WORK/data" >/dev/null
$RUN "$PGBIN/pg_ctl" -D "$WORK/data" \
  -o "-p $PORT -k $SOCK -c listen_addresses=''" -l "$WORK/pg.log" start >/dev/null
sleep 2

$PSQL -q -f "$HERE/00_scaffold.sql"
$PSQL -q -f "$MIG"
echo "== migration applied unchanged; running adversarial suite =="
$RUN psql -h "$SOCK" -p "$PORT" -U postgres -f "$HERE/10_adversarial.sql"
