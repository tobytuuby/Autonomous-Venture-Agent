-- P2.2 evidence normalization, append-only lineage and contradiction records.
CREATE TABLE IF NOT EXISTS p2_normalized_evidence (
  normalized_evidence_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  normalized_hash CHAR(64) NOT NULL UNIQUE,
  canonical_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS p2_normalization_lineage (
  sequence BIGSERIAL PRIMARY KEY,
  normalized_evidence_id TEXT NOT NULL REFERENCES p2_normalized_evidence(normalized_evidence_id),
  raw_evidence_id TEXT NOT NULL,
  source_hash CHAR(64) NOT NULL,
  operation TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (normalized_evidence_id, raw_evidence_id, source_hash)
);
CREATE TABLE IF NOT EXISTS p2_contradiction_detection (
  contradiction_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  claim_key TEXT NOT NULL,
  contradiction_json JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('detected','quarantined','reviewed')),
  detected_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS p2_normalization_events (
  sequence BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  event_json JSONB NOT NULL,
  event_hash CHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL
);
