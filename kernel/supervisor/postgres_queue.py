"""Authoritative PostgreSQL queue adapter for P0.7."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.types.json import Jsonb


class PostgresJobQueue:
    def __init__(self, dsn="dbname=postgres user=venture-broker host=/var/run/postgresql"):
        self.dsn = dsn

    def _connect(self):
        return psycopg.connect(self.dsn)

    def enqueue(self, job_id, idempotency_key, payload):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO agent_jobs (job_id, idempotency_key, payload, status)
                       VALUES (%s, %s, %s, 'queued')
                       ON CONFLICT (idempotency_key) DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                       RETURNING job_id, idempotency_key, payload, status, attempts""",
                    (job_id, idempotency_key, Jsonb(payload)),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(zip(("job_id", "idempotency_key", "payload", "status", "attempts"), row))

    def claim(self, worker_id):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """WITH next_job AS (
                           SELECT job_id FROM agent_jobs
                           WHERE status = 'queued'
                           ORDER BY claimed_at NULLS FIRST, job_id
                           FOR UPDATE SKIP LOCKED LIMIT 1
                       )
                       UPDATE agent_jobs j
                       SET status = 'claimed', claimed_by = %s, claimed_at = now(), attempts = attempts + 1
                       FROM next_job n WHERE j.job_id = n.job_id
                       RETURNING j.job_id, j.idempotency_key, j.payload, j.status, j.attempts""",
                    (worker_id,),
                )
                row = cur.fetchone()
            conn.commit()
        return None if row is None else dict(zip(("job_id", "idempotency_key", "payload", "status", "attempts"), row))

    def reclaim_stale(self, max_age: timedelta):
        cutoff = datetime.now(timezone.utc) - max_age
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE agent_jobs SET status = 'queued', claimed_by = NULL, claimed_at = NULL
                       WHERE status = 'claimed' AND claimed_at < %s""",
                    (cutoff,),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def complete(self, job_id):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE agent_jobs SET status = 'completed', completed_at = now()
                       WHERE job_id = %s AND status = 'claimed' RETURNING job_id""",
                    (job_id,),
                )
                changed = cur.fetchone() is not None
            conn.commit()
        return changed
