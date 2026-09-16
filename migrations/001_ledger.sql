BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS operational_events (
    event_seq       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id        uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    event_type      text NOT NULL,
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    venture_id      uuid,
    actor_id        text,
    payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    previous_hash   text,
    event_hash      text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS accounting_ledger (
    entry_seq       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_id        uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    transaction_id  uuid NOT NULL DEFAULT gen_random_uuid(),
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    venture_id      uuid,
    account         text NOT NULL,
    amount          numeric(20,6) NOT NULL CHECK (amount <> 0),
    currency        text NOT NULL DEFAULT 'USD' CHECK (char_length(currency) = 3),
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    previous_hash   text,
    entry_hash      text NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION phase0_chain_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    prior_hash text;
    canonical text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(TG_TABLE_NAME, 0));

    IF TG_TABLE_NAME = 'operational_events' THEN
        SELECT event_hash INTO prior_hash
        FROM operational_events
        ORDER BY event_seq DESC
        LIMIT 1;

        NEW.previous_hash := prior_hash;
        canonical := concat_ws('|', coalesce(prior_hash, ''), NEW.event_seq,
            NEW.event_id, NEW.event_type, NEW.occurred_at, coalesce(NEW.venture_id::text, ''),
            coalesce(NEW.actor_id, ''), NEW.payload::text);
        NEW.event_hash := encode(digest(canonical, 'sha256'), 'hex');
    ELSE
        SELECT entry_hash INTO prior_hash
        FROM accounting_ledger
        ORDER BY entry_seq DESC
        LIMIT 1;

        NEW.previous_hash := prior_hash;
        canonical := concat_ws('|', coalesce(prior_hash, ''), NEW.entry_seq,
            NEW.entry_id, NEW.transaction_id, NEW.occurred_at,
            coalesce(NEW.venture_id::text, ''), NEW.account, NEW.amount,
            NEW.currency, NEW.metadata::text);
        NEW.entry_hash := encode(digest(canonical, 'sha256'), 'hex');
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION phase0_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'append-only ledger table % cannot be updated or deleted', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS operational_events_chain_insert ON operational_events;
CREATE TRIGGER operational_events_chain_insert
BEFORE INSERT ON operational_events
FOR EACH ROW EXECUTE FUNCTION phase0_chain_insert();

DROP TRIGGER IF EXISTS accounting_ledger_chain_insert ON accounting_ledger;
CREATE TRIGGER accounting_ledger_chain_insert
BEFORE INSERT ON accounting_ledger
FOR EACH ROW EXECUTE FUNCTION phase0_chain_insert();

DROP TRIGGER IF EXISTS operational_events_append_only ON operational_events;
CREATE TRIGGER operational_events_append_only
BEFORE UPDATE OR DELETE ON operational_events
FOR EACH ROW EXECUTE FUNCTION phase0_append_only();

DROP TRIGGER IF EXISTS accounting_ledger_append_only ON accounting_ledger;
CREATE TRIGGER accounting_ledger_append_only
BEFORE UPDATE OR DELETE ON accounting_ledger
FOR EACH ROW EXECUTE FUNCTION phase0_append_only();

COMMIT;
