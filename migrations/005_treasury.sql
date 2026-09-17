CREATE TABLE IF NOT EXISTS treasury_parameters (
    parameter_version bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    protected_cash_floor_pct numeric NOT NULL CHECK (protected_cash_floor_pct >= 0 AND protected_cash_floor_pct <= 1),
    operating_reserve_pct numeric NOT NULL CHECK (operating_reserve_pct >= 0 AND operating_reserve_pct <= 1),
    max_portfolio_deployable_pct numeric NOT NULL CHECK (max_portfolio_deployable_pct >= 0 AND max_portfolio_deployable_pct <= 1),
    max_new_venture_funding_pct numeric NOT NULL CHECK (max_new_venture_funding_pct >= 0 AND max_new_venture_funding_pct <= 1),
    venture_reinvestment_pct numeric NOT NULL CHECK (venture_reinvestment_pct >= 0 AND venture_reinvestment_pct <= 1),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bootstrap_treasury_state (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    mode text NOT NULL CHECK (mode IN ('bootstrap', 'standard')),
    seed_balance numeric(20,6) NOT NULL CHECK (seed_balance > 0),
    eligible_balance numeric(20,6) NOT NULL CHECK (eligible_balance >= 0),
    available_profit numeric(20,6) NOT NULL DEFAULT 0,
    deployed numeric(20,6) NOT NULL DEFAULT 0,
    new_venture_deployed numeric(20,6) NOT NULL DEFAULT 0,
    entry_event_id text NOT NULL UNIQUE,
    exit_event_id text UNIQUE,
    exit_sweep_id text UNIQUE,
    transition_version bigint NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS treasury_commitments (
    allocation_id text PRIMARY KEY,
    amount numeric(20,6) NOT NULL CHECK (amount > 0),
    new_venture boolean NOT NULL DEFAULT false,
    status text NOT NULL CHECK (status IN ('pending', 'committed')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS treasury_transition_events (
    event_id text PRIMARY KEY,
    event_type text NOT NULL,
    sweep_id text UNIQUE,
    available_profit numeric(20,6),
    created_at timestamptz NOT NULL DEFAULT now()
);