-- P0.14 thesis/cooldown durable shape; applied when lifecycle state is promoted to PostgreSQL.
CREATE TABLE IF NOT EXISTS thesis_cooldowns (
    thesis_id text PRIMARY KEY,
    cooldown_until timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
