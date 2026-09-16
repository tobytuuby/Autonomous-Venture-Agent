DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'venture-broker') THEN
        CREATE ROLE "venture-broker" LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
    ELSE
        ALTER ROLE "venture-broker" LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO "venture-broker";
GRANT SELECT, INSERT, UPDATE ON public.agent_jobs TO "venture-broker";
REVOKE DELETE, TRUNCATE ON public.agent_jobs FROM "venture-broker";
