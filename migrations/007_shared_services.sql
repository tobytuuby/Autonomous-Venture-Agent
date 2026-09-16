-- P0.14 shared-service demand and quarantine durable shape.
CREATE TABLE IF NOT EXISTS shared_service_demands (
    service_id text NOT NULL,
    venture_id text NOT NULL,
    qualifying_request_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (service_id, venture_id, qualifying_request_id)
);

CREATE TABLE IF NOT EXISTS shared_service_instances (
    service_id text PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('active', 'quarantined')),
    admitted_venture_count integer NOT NULL CHECK (admitted_venture_count >= 2),
    created_at timestamptz NOT NULL DEFAULT now()
);
