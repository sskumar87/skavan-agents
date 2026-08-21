# Laptop 1 operations

These templates support the private data node. They are intentionally scoped to
the Skavan product (`skavan`) and identity (`zitadel`) databases and never touch
the existing `skav` database or its Redis services.

## Local backup template

`backup-skavan.sh` produces a PostgreSQL custom-format dump and SHA-256
checksum for the database selected by `SKAVAN_DB_NAME`. It defaults to
`skavan`; the separate ZITADEL service sets it to `zitadel`. The script has no
upload, retention deletion, encryption or restore-overwrite behavior. Those
safeguards avoid silently choosing a cloud provider, recovery key or deletion
policy for the operator.

The script only accepts the exact database/role pairs `skavan`/
`skavan_backup` and `zitadel`/`zitadel_backup`. Create those scoped roles with
`create-backup-roles.sql` before enabling either timer. The existing `skav`
database is deliberately absent from the allowlist.

### Install on Laptop 1

These units are user services because Laptop 1 runs Docker Desktop for Linux.
They use its user-level `docker-desktop.service` and explicit Unix socket rather
than the inactive system `docker.service`.

1. Copy the script to `/home/shyam/.local/bin/backup-skavan`, make it executable,
   and create `/home/shyam/.local/share/skavan-backups` with mode `700`.
2. Run it once manually as `shyam`. Check that it writes a `.dump` and matching
   `.sha256` file with mode `600`.
3. Install the product and ZITADEL service/timer templates under
   `/home/shyam/.config/systemd/user/`, reload the user manager, then enable both
   timers with `systemctl --user enable --now`.
4. Verify both timers with `systemctl --user list-timers` and inspect each
   service's last result before relying on the schedule.
5. User services do not run while `shyam` is logged out unless lingering is
   enabled. An administrator must run `sudo loginctl enable-linger shyam`, then
   verify `loginctl show-user shyam -p Linger` reports `yes`.

Do not call this a complete production backup until the dump and checksum are
encrypted and copied to an approved, access-controlled location outside Laptop
1. Keep recovery keys separately from the destination. A monthly isolated
restore test remains required.

## Before enabling off-host replication

Record the destination, encryption recovery-key holder, backup owner,
retention policy, alerting path and RPO/RTO. The current recommended baseline
is nightly backup, 14 daily / 8 weekly / 12 monthly retained copies, and a
monthly restore rehearsal. Tighter than 24-hour RPO requires a separately
designed WAL/PITR setup.
