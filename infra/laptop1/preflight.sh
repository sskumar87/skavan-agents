#!/usr/bin/env bash
set -euo pipefail

container="${SKAVAN_DB_CONTAINER:-skav-timescaledb}"
expected_bind="${SKAVAN_DB_BIND:-192.168.1.49:5432}"
failures=0
warnings=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1" >&2; failures=$((failures + 1)); }
warn() { printf 'WARN  %s\n' "$1" >&2; warnings=$((warnings + 1)); }

for command_name in docker systemctl sha256sum; do
  command -v "$command_name" >/dev/null 2>&1 && pass "$command_name is installed" || fail "$command_name is missing"
done

if ! docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null | grep -qx true; then
  fail "database container $container is not running"
else
  pass "database container $container is running"
fi

if docker port "$container" 5432/tcp 2>/dev/null | grep -Fxq "$expected_bind"; then
  pass "PostgreSQL is bound to $expected_bind"
else
  fail "PostgreSQL is not bound exactly to $expected_bind"
fi

database_list="$(docker exec "$container" psql -U skav_user -d postgres -X -Atc \
  "SELECT datname FROM pg_database WHERE datname IN ('skav','skavan','zitadel') ORDER BY datname;")"
for database_name in skav skavan zitadel; do
  grep -Fxq "$database_name" <<<"$database_list" && pass "database $database_name exists" || fail "database $database_name is missing"
done

unsafe_roles="$(docker exec "$container" psql -U skav_user -d postgres -X -Atc \
  "SELECT rolname FROM pg_roles WHERE rolname IN ('skavan_app','skavan_migrator','skavan_backup','zitadel','zitadel_backup') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication);")"
[[ -z "$unsafe_roles" ]] && pass "product, identity and backup roles are non-privileged" || fail "privileged application roles detected"

vector_version="$(docker exec "$container" psql -U skav_user -d skavan -X -Atc \
  "SELECT extversion FROM pg_extension WHERE extname='vector';")"
[[ -n "$vector_version" ]] && pass "pgvector is installed in skavan ($vector_version)" || fail "pgvector is missing from skavan"

alembic_revision="$(docker exec "$container" psql -U skav_user -d skavan -X -Atc \
  "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || true)"
[[ "$alembic_revision" == "20260821_0001" ]] && pass "Alembic revision is $alembic_revision" || fail "unexpected Alembic revision"

for unit_name in skavan-backup.timer zitadel-backup.timer; do
  systemctl --user is-enabled --quiet "$unit_name" && pass "$unit_name is enabled" || fail "$unit_name is disabled"
  systemctl --user is-active --quiet "$unit_name" && pass "$unit_name is active" || fail "$unit_name is inactive"
done

backup_dir="${SKAVAN_BACKUP_DIR:-$HOME/.local/share/skavan-backups}"
for database_name in skavan zitadel; do
  latest_checksum="$(find "$backup_dir" -maxdepth 1 -type f -name "$database_name-*.dump.sha256" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)"
  if [[ -n "$latest_checksum" ]] && sha256sum -c "$latest_checksum" >/dev/null; then
    pass "latest $database_name backup checksum is valid"
  else
    fail "no valid $database_name backup checksum was found"
  fi
done

if find "$backup_dir" -maxdepth 1 -type f -name 'skav-*.dump' -print -quit | grep -q .; then
  fail "a forbidden backup of the existing skav database exists"
else
  pass "no skav database backup was created"
fi

if [[ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)" == "yes" ]]; then
  pass "user lingering is enabled"
else
  warn "user lingering is disabled; timers stop after logout"
fi

ssl_state="$(docker exec "$container" psql -U skav_user -d postgres -X -Atc 'SHOW ssl;')"
[[ "$ssl_state" == "on" ]] && pass "PostgreSQL TLS is enabled" || warn "PostgreSQL TLS is not enabled"

printf '\nPreflight result: %d failure(s), %d warning(s).\n' "$failures" "$warnings"
(( failures == 0 ))
