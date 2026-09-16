BEGIN;

CREATE TABLE IF NOT EXISTS phase0_migration_smoke (
    id          integer PRIMARY KEY,
    marker      text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO phase0_migration_smoke (id, marker)
VALUES (1, 'P0.1 migration smoke test')
ON CONFLICT (id) DO UPDATE
SET marker = EXCLUDED.marker,
    created_at = now();

COMMIT;
