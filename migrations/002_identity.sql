BEGIN;

CREATE TABLE IF NOT EXISTS ventures (
    venture_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    lifecycle_state text NOT NULL DEFAULT 'validated'
        CHECK (lifecycle_state IN ('validated', 'active', 'harvest', 'winding_down', 'wound_down')),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    venture_id      uuid NOT NULL REFERENCES ventures(venture_id),
    role            text NOT NULL,
    status          text NOT NULL DEFAULT 'provisioned'
        CHECK (status IN ('provisioned', 'active', 'degraded', 'quarantined', 'terminated')),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_grants (
    grant_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        uuid NOT NULL REFERENCES agents(agent_id),
    venture_id      uuid NOT NULL REFERENCES ventures(venture_id),
    capability      text NOT NULL,
    constraints     jsonb NOT NULL DEFAULT '{}'::jsonb,
    issued_at       timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz
);

CREATE INDEX IF NOT EXISTS agents_venture_id_idx ON agents (venture_id);
CREATE INDEX IF NOT EXISTS capability_grants_venture_id_idx ON capability_grants (venture_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'venture_app') THEN
        CREATE ROLE venture_app NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO venture_app;
GRANT SELECT, INSERT, UPDATE ON ventures, agents, capability_grants TO venture_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO venture_app;

ALTER TABLE ventures ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE capability_grants ENABLE ROW LEVEL SECURITY;

ALTER TABLE ventures FORCE ROW LEVEL SECURITY;
ALTER TABLE agents FORCE ROW LEVEL SECURITY;
ALTER TABLE capability_grants FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ventures_isolation ON ventures;
CREATE POLICY ventures_isolation ON ventures
    USING (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid)
    WITH CHECK (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid);

DROP POLICY IF EXISTS agents_isolation ON agents;
CREATE POLICY agents_isolation ON agents
    USING (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid)
    WITH CHECK (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid);

DROP POLICY IF EXISTS capability_grants_isolation ON capability_grants;
CREATE POLICY capability_grants_isolation ON capability_grants
    USING (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid)
    WITH CHECK (venture_id = nullif(current_setting('app.venture_id', true), '')::uuid);

COMMIT;
