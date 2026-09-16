# P0.13 adversarial harness

This increment runs the 24 scenarios that are executable against one hard-coded venture, generic red-team identities, and the kernel mechanisms available through P0.12. It intentionally does not invent CEO/Venture-Manager identities, a second venture, worker archetypes, or lifecycle state before P0.14.

The executable scenarios are recorded in tests/certification/p013-manifest.json; each entry points to the mechanism-level unit evidence that must remain green. The pending scenarios are explicit and remain outside the numerator.
