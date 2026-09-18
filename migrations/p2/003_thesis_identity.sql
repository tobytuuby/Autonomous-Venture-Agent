-- P2.3 thesis identity, dimension assignments, and append-only lineage.
CREATE TABLE IF NOT EXISTS p2_thesis_fingerprints (
  thesis_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  fingerprint CHAR(64) NOT NULL UNIQUE,
  canonical_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS p2_dimension_assignments (
  assignment_id TEXT PRIMARY KEY,
  thesis_id TEXT NOT NULL REFERENCES p2_thesis_fingerprints(thesis_id),
  dimension TEXT NOT NULL,
  normalized_evidence_id TEXT NOT NULL,
  canonical_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (thesis_id, dimension, normalized_evidence_id)
);
CREATE TABLE IF NOT EXISTS p2_thesis_lineage (
  sequence BIGSERIAL PRIMARY KEY,
  thesis_id TEXT NOT NULL REFERENCES p2_thesis_fingerprints(thesis_id),
  normalized_evidence_id TEXT NOT NULL,
  assignment_id TEXT NOT NULL,
  transformation TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (thesis_id, normalized_evidence_id)
);
CREATE TABLE IF NOT EXISTS p2_thesis_events (
  sequence BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  event_json JSONB NOT NULL,
  event_hash CHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL
);
