# Laptop 1 operations

These templates support the private data node. They are intentionally scoped to
the Skavan product database (`skavan`) and never touch the existing `skav`
database or its Redis services.

## Local backup template

`backup-skavan.sh` produces a PostgreSQL custom-format dump and SHA-256
checksum on Laptop 1. It has no upload, retention deletion, encryption or
restore-overwrite behavior. Those safeguards avoid silently choosing a cloud
provider, recovery key or deletion policy for the operator.

### Install on Laptop 1

1. Copy the script to `/usr/local/sbin/backup-skavan`, make it executable, and
   create `/home/shyam/.local/share/skavan-backups` with mode `700`.
2. Run it once manually as `shyam`. Check that it writes a `.dump` and matching
   `.sha256` file with mode `600`.
3. Install the service/timer templates as
   `/etc/systemd/system/skavan-backup.service` and
   `/etc/systemd/system/skavan-backup.timer`; then enable the timer.
4. Verify the timer with `systemctl list-timers skavan-backup.timer` and its
   last result with `systemctl status skavan-backup.service`.

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
