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

### Install on Laptop 1

1. Copy the script to `/usr/local/sbin/backup-skavan`, make it executable, and
   create `/home/shyam/.local/share/skavan-backups` with mode `700`.
2. Run it once manually as `shyam`. Check that it writes a `.dump` and matching
   `.sha256` file with mode `600`.
3. Install the product service/timer templates as
   `/etc/systemd/system/skavan-backup.service` and
   `/etc/systemd/system/skavan-backup.timer`. Install the ZITADEL pair as
   `zitadel-backup.service` and `zitadel-backup.timer`; then enable both timers.
4. Verify both timers with `systemctl list-timers` and inspect each service's
   last result before relying on the schedule.

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
