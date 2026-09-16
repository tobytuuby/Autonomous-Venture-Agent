CREATE TABLE IF NOT EXISTS agent_jobs (
    job_id uuid PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    payload jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('queued','claimed','completed','failed')),
    claimed_by text,
    claimed_at timestamptz,
    completed_at timestamptz,
    attempts integer NOT NULL DEFAULT 0
);
