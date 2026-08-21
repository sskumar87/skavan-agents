#!/usr/bin/env bash
# Creates a local, custom-format backup of the Skavan product database.
# It is intentionally upload-free: configure encrypted off-host replication
# before treating this as a production backup policy.
set -euo pipefail

umask 077

CONTAINER_NAME="${SKAVAN_DB_CONTAINER:-skav-timescaledb}"
DATABASE_NAME="${SKAVAN_DB_NAME:-skavan}"
DATABASE_USER="${SKAVAN_BACKUP_DB_USER:-skav_user}"
BACKUP_DIR="${SKAVAN_BACKUP_DIR:-$HOME/.local/share/skavan-backups}"
LOCK_FILE="${SKAVAN_BACKUP_LOCK_FILE:-$HOME/.local/state/skavan/backup.lock}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command is unavailable: $1" >&2
    exit 1
  }
}

require_command docker
require_command flock
require_command sha256sum
require_command date

mkdir -p "$BACKUP_DIR" "$(dirname "$LOCK_FILE")"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "A Skavan backup is already running." >&2
  exit 1
fi

if ! docker inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -qx true; then
  echo "Database container is not running: $CONTAINER_NAME" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$BACKUP_DIR/skavan-$timestamp.dump"
checksum_file="$backup_file.sha256"
temporary_file="$backup_file.partial"

cleanup() {
  rm -f "$temporary_file"
}
trap cleanup EXIT

docker exec "$CONTAINER_NAME" \
  pg_dump -U "$DATABASE_USER" -d "$DATABASE_NAME" --format=custom --no-owner --no-privileges \
  > "$temporary_file"

if [[ ! -s "$temporary_file" ]]; then
  echo "Backup failed: output is empty." >&2
  exit 1
fi

mv "$temporary_file" "$backup_file"
sha256sum "$backup_file" > "$checksum_file"

cat <<EOF
Backup created: $backup_file
Checksum:      $checksum_file
Next step: encrypt and replicate both files to an approved off-host destination.
EOF
