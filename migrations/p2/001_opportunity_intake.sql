BEGIN;

CREATE TABLE IF NOT EXISTS p2_opportunities (
    opportunity_id text PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    portfolio_id text NOT NULL,
    record_hash text NOT NULL,
    canonical_json jsonb NOT NULL,
    lifecycle_state text NOT NULL DEFAULT 'received'
        CHECK (lifecycle_state = 'received'),
    created_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS p2_evidence_envelopes (
    evidence_id text PRIMARY KEY,
    portfolio_id text NOT NULL,
    evidence_type text NOT NULL
        CHECK (evidence_type IN ('external', 'synthetic', 'inferred', 'operator')),
    taint_status text NOT NULL
        CHECK (taint_status IN ('tainted', 'trusted', 'declassified')),
    source_ref text NOT NULL,
    source_hash text NOT NULL,
    captured_at timestamptz NOT NULL,
    canonical_json jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS p2_opportunity_evidence (
    opportunity_id text NOT NULL REFERENCES p2_opportunities(opportunity_id),
    evidence_id text NOT NULL REFERENCES p2_evidence_envelopes(evidence_id),
    PRIMARY KEY (opportunity_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS p2_intake_events (
    sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    opportunity_id text NOT NULL REFERENCES p2_opportunities(opportunity_id),
    event_type text NOT NULL CHECK (event_type IN ('intake_received', 'duplicate_delivery')),
    event_json jsonb NOT NULL,
    previous_hash text NOT NULL,
    event_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS p2_opportunities_portfolio_idx
    ON p2_opportunities (portfolio_id);
CREATE INDEX IF NOT EXISTS p2_evidence_portfolio_idx
    ON p2_evidence_envelopes (portfolio_id);
CREATE INDEX IF NOT EXISTS p2_intake_events_opportunity_idx
    ON p2_intake_events (opportunity_id, sequence);

COMMIT;
