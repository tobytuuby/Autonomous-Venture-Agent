-- P2.5 replay and adversarial result ledger
-- Synthetic/shadow-only durable shape; no external-action capabilities.
CREATE TABLE IF NOT EXISTS p2_replay_requests (
    replay_id TEXT PRIMARY KEY,
    target_decision_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    request_json JSONB NOT NULL,
    request_hash TEXT NOT NULL UNIQUE,
    external_action_authorized BOOLEAN NOT NULL DEFAULT FALSE CHECK (external_action_authorized = FALSE)
);

CREATE TABLE IF NOT EXISTS p2_replay_results (
    sequence BIGSERIAL PRIMARY KEY,
    replay_id TEXT NOT NULL REFERENCES p2_replay_requests(replay_id),
    result_json JSONB NOT NULL,
    previous_hash TEXT NOT NULL,
    result_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL
);
