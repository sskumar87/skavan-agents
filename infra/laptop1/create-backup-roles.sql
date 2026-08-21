\set ON_ERROR_STOP on

DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'skavan_backup') THEN
        CREATE ROLE skavan_backup LOGIN
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION
            CONNECTION LIMIT 2;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zitadel_backup') THEN
        CREATE ROLE zitadel_backup LOGIN
            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION
            CONNECTION LIMIT 2;
    END IF;
END
$roles$;

ALTER ROLE skavan_backup SET default_transaction_read_only = on;
ALTER ROLE zitadel_backup SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE skavan TO skavan_backup;
GRANT CONNECT ON DATABASE zitadel TO zitadel_backup;

\connect skavan
GRANT USAGE ON SCHEMA public TO skavan_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO skavan_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO skavan_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE skavan_migrator IN SCHEMA public
    GRANT SELECT ON TABLES TO skavan_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE skavan_migrator IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO skavan_backup;

\connect zitadel
GRANT USAGE ON SCHEMA public TO zitadel_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO zitadel_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO zitadel_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE zitadel IN SCHEMA public
    GRANT SELECT ON TABLES TO zitadel_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE zitadel IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO zitadel_backup;
