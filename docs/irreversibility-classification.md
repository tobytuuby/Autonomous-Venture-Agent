# Irreversibility classification

| Class | Example | Minimum latency | Kill-switch behavior |
|---|---|---:|---|
| Reversible | Draft or read-only request | 0s | Soft stop blocks new work |
| Recoverable | External reservation with provider cancellation | 10s | Hard stop revokes reservation |
| High irreversibility | Capture, transfer, or destructive external action | 30s | Action cannot fire until the gate opens; hard stop intercepts during the window |

P0.12 exercises the high-irreversibility gate with a deterministic delayed action and revokes a live OpenBao synthetic lease as the test-mode external instrument.
