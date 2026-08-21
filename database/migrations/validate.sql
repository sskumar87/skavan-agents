-- Run after `alembic upgrade head` against a disposable database.
-- This verifies the V1 migration shape without inspecting application data.

SELECT extname
FROM pg_extension
WHERE extname = 'vector';

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'users', 'identity_accounts', 'groups', 'group_memberships', 'threads',
    'messages', 'group_memories', 'channel_identities',
    'hermes_profile_bindings', 'capability_permissions',
    'approval_requests', 'audit_events'
  )
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'group_memories'
  AND indexname = 'ix_group_memories_embedding_cosine';
