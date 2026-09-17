# Autonomous Venture Agent — Phase 1 Policy Specification

## v1.0

**Status:** Draft for review
**Phase:** P1 — CEO Stage 0 shadow hardening and Gate 2 closure
**Depends on:** `phase0-policy-kernel-spec-v11.md`, `phase0-implementation-plan-v3.2.md`, and the P0.15 implementation already present in the repository
**Source documents and exact hashes:**
- `phase0-policy-kernel-spec-v11.md`: `40734f0e452806259f8d52be55d281291778d797f0230386da956c8a033f22a1`
- `phase0-implementation-plan-v3.2.md`: `10fb7b5c71f00f26f9d32ffc85259eba2f3396751eee7aeb7b365e30dd89d65b`
- `project-phase-plan-v1.0.md`: `c792f578917391280299bceee8102bae7b3a34d61557133126c61592b2727397`
**Authority boundary:** Shadow reasoning only. No production CEO, Venture Manager, worker, external payment, or real-capital action is enabled by this specification.

## 1. Purpose and relationship to Phase 0

P1 completes and independently assesses the Stage 0 shadow CEO boundary. It does not relabel or redo P0.15. The P0.15 implementation is the baseline for the CEO agent, provider boundary, shadow runner, decision logging, tool-list fingerprinting, and committed Gate 2 report/manifest.

P1 addresses the remaining evidence, durability, replay, configuration, review, and certification gaps. A successful P1 exit does not authorize Stage 1, external action, real payment, or deployment of a production CEO.

## 2. Normative requirements

### CEO-001 — Shadow-only authority

The Stage 0 CEO may produce reasoning and structured proposals only. It MUST NOT receive or exercise capabilities that can allocate capital, launch ventures, spawn workers, issue payments, mutate production state, or bypass the capability broker.

### CEO-002 — Exact configuration identity

Every certification run MUST record a non-secret configuration fingerprint covering provider endpoint origin, model name, prompt hash, tool-list hash, policy/spec versions, runner version, and relevant runtime version. Secrets MUST NOT appear in reports, logs, manifests, or committed artifacts.

### CEO-003 — Provider boundary

Model calls MUST pass through one explicit provider adapter boundary. The boundary MUST expose request metadata sufficient for independent verification while redacting credentials and sensitive payload material.

### CEO-004 — Durable decision state

The shadow runner MUST persist decision identity, scenario ID, configuration fingerprint, request status, response status, and terminal classification durably. A retry after interruption MUST be idempotent and MUST NOT create duplicate terminal decisions.

### CEO-005 — Crash recovery

After process interruption or container loss, recovery MUST reconstruct state from the authoritative durable store, not from model conversation history or process memory. In-flight records MUST resolve deterministically to retryable, completed, or quarantined states.

### CEO-006 — Evidence that distinguishes execution modes

A P1 certification report MUST distinguish:
- verified external provider execution;
- externally configured but not independently verifiable execution;
- synthetic or offline execution; and
- failed or incomplete execution.

A summary manifest alone MUST NOT close Gate 2.

### CEO-007 — 49-case denominator preservation

P1 MUST rerun and report the existing `ADV-001`–`ADV-049` universe without renumbering, omitting, or folding in BOOT, P0.16, or provider-specific supplemental checks. The denominator remains `/49`.

### CEO-008 — ADV-040 durable-state replay

`ADV-040` MUST be exercised against the CEO-shaped shadow identity and production-equivalent durable portfolio/ledger fixture. Generic process recovery is mechanism evidence, not a substitute for this scenario.

### CEO-009 — No action on model suggestion

A model response MUST never directly authorize or execute an action. Any proposed action is inert shadow output and MUST be rejected or quarantined if it is outside the allowed schema or shadow policy.

### CEO-010 — Decision-log integrity

Decision logs MUST be append-only or tamper-evident for certification purposes, preserve policy/configuration references, and support deterministic replay. Corrections MUST be represented as new records, not silent mutation.

### CEO-011 — Human review and limitations

The phase report MUST identify a named review decision, unresolved limitations, external dependencies, and whether each claim is independently verified, externally configured but unverified, synthetic, or not applicable. “PASS” MUST NOT be used where the evidence only supports an unverified external claim.

### CEO-012 — Reachability prohibition

The CEO role, shadow runner, and model provider boundary MUST NOT be able to reach `RealPaymentAdapter`, `BootstrapTreasury`, live broker execution, or any external capital/payment path. Red-team reachability tests MUST prove the prohibition.

## 3. Required evidence

P1 evidence MUST include, at minimum:

- configuration fingerprint with secret-free fields;
- provider-boundary request/response or equivalent independently verifiable trace;
- raw per-scenario report for all `ADV-001`–`ADV-049` cases;
- durable decision-log sample and replay output;
- crash/restart recovery evidence, including `ADV-040`;
- negative reachability evidence for capital/payment and execution capabilities;
- exact prompt and tool-list hashes;
- technical/non-technical certification report;
- explicit list of claims that remain externally configured but not independently verifiable.

## 4. Prohibitions

P1 MUST NOT:

- attach a real CEO identity;
- enable Stage 1 or any real capital action;
- contact or pay an external party;
- treat a synthetic transport as evidence of a real provider call;
- store API keys, bearer tokens, or secret configuration values in Git;
- change the `ADV-001`–`ADV-049` denominator;
- use BOOT or P0.16 results as substitutes for the ADV suite;
- infer authorization from a model response.

## 5. Exit interpretation

P1 may be marked technically complete only when all normative requirements are implemented and the technical/non-technical report distinguishes independently verified evidence from claims that remain externally configured or unverified.

Even then, the project remains in shadow mode unless a separately approved future phase changes the execution class. P1 completion does not authorize P7 activity or any real-world action.

## 6. Change control

Any change to a normative requirement, invariant, evidence class, denominator, or authority boundary requires `phase1-policy-spec-v1.1.md` or later. This v1.0 file remains historical once superseded.
