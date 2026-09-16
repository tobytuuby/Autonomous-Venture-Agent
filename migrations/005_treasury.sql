CREATE TABLE IF NOT EXISTS treasury_parameters (
    parameter_version bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    protected_cash_floor_pct numeric NOT NULL CHECK (protected_cash_floor_pct >= 0 AND protected_cash_floor_pct <= 1),
    operating_reserve_pct numeric NOT NULL CHECK (operating_reserve_pct >= 0 AND operating_reserve_pct <= 1),
    max_portfolio_deployable_pct numeric NOT NULL CHECK (max_portfolio_deployable_pct >= 0 AND max_portfolio_deployable_pct <= 1),
    max_new_venture_funding_pct numeric NOT NULL CHECK (max_new_venture_funding_pct >= 0 AND max_new_venture_funding_pct <= 1),
    venture_reinvestment_pct numeric NOT NULL CHECK (venture_reinvestment_pct >= 0 AND venture_reinvestment_pct <= 1),
    created_at timestamptz NOT NULL DEFAULT now()
);