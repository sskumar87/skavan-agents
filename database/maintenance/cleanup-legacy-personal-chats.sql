-- Remove only the superseded per-user Personal chat workspaces.
-- Run after ADR-013 profile workspaces are deployed and verified.
-- Deleting a group cascades to its threads and messages by schema design.

BEGIN;

WITH targets AS (
    SELECT id
    FROM groups
    WHERE settings->>'kind' = 'personal'
), deleted AS (
    DELETE FROM groups
    WHERE id IN (SELECT id FROM targets)
    RETURNING id
)
SELECT count(*) AS deleted_legacy_personal_workspaces FROM deleted;

COMMIT;
