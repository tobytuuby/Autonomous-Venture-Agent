-- P2.4 scoring, human review, lifecycle transitions, and replay events.
CREATE TABLE IF NOT EXISTS p2_thesis_scores (
  score_id TEXT PRIMARY KEY,
  thesis_id TEXT NOT NULL,
  portfolio_id TEXT NOT NULL,
  input_fingerprint CHAR(64) NOT NULL,
  score_json JSONB NOT NULL,
  computation_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (thesis_id, input_fingerprint)
);
CREATE TABLE IF NOT EXISTS p2_lifecycle_transitions (
  transition_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL,
  portfolio_id TEXT NOT NULL,
  from_state TEXT NOT NULL,
  to_state TEXT NOT NULL,
  transition_json JSONB NOT NULL,
  sequence BIGSERIAL UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS p2_review_decisions (
  review_id TEXT PRIMARY KEY,
  thesis_id TEXT NOT NULL,
  portfolio_id TEXT NOT NULL,
  review_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS p2_lifecycle_events (
  sequence BIGSERIAL PRIMARY KEY,
  transition_id TEXT NOT NULL,
  event_json JSONB NOT NULL,
  previous_hash CHAR(64) NOT NULL,
  event_hash CHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL
);
