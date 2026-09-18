# P2 migration determination

P2.0 defines versioned contracts and authority-review fixtures only. It does
not introduce durable lifecycle tables or alter authoritative PostgreSQL state.
Therefore no SQL migration is required for P2.0.

Durable opportunity/evidence/lifecycle persistence is deferred to the owning
P2.1/P2.2/P2.4 increments. Any required migration must be additive, versioned,
idempotent, scope-aware, and separately reviewed before it is added.
