# P12 Limited Production Test Charter — Baseline Draft

**Version:** 0.1
**Status:** INCOMPLETE DRAFT — NOT APPROVED FOR EXECUTION
**Prepared:** 2026-09-29
**Roadmap:** project-phase-plan-v2.2.md
**Purpose:** Establish a proposed baseline for a non-monetary, limited production test. This document does not authorize P12 implementation, network access, credentials, or test execution.

## 1. Proposed target

- **Candidate domain:** ctkfamily.com; Kalaap Das reports owning and self-hosting it.
- **Production service/runtime:** Kalaap Das reports that the site runs on a self-hosted Linux VM with Apache, and that most of the site uses PHP. This is user-provided information, not independently verified; exact VM identity, Apache/PHP versions, application architecture, and deployment details remain TBD.
- **Environment:** Intended target is the production website; exact production host, exposure, and runtime are TBD.
- **Tenant or venture:** TBD; may be not applicable for a public website.
- **Endpoint:** Kalaap Das reports that repository review found no documented health/status endpoint or references for `health`, `status`, `healthz`, `ready`, or `ping`. A minimal unauthenticated `/health` endpoint returning `200 OK` with no sensitive information is a proposed candidate only; it does not currently exist as a verified endpoint.
- **Accountable service owner:** Kalaap Das, designated by the user; service ownership is user-reported.
- The repository and local venture-control bridge are not production targets.

No endpoint, target identifier, account, or access path may be inferred or substituted by the implementer.

## 2. Objective and proposed success criteria

**Objective:** Verify that one observer can read the selected service's health signal and stop cleanly without changing application state.

The proposed test succeeds only if all planned probes satisfy health criteria and service limits supplied by the service owner, no writes or other state changes occur, and no customer or personal data is returned or retained.

- Health/status acceptance criteria: TBD; must use the selected service's existing documented criteria.
- Availability and latency thresholds: TBD; must use existing service SLOs and monitoring definitions.
- Test-induced state changes: zero.
- Monetary exposure and loss: zero.
- Any production criteria not already documented must be resolved by the owner before P12 audit.

## 3. Allowed and forbidden operations

**Proposed allowed operation:** Once an endpoint exists and is reviewed, one fixed read operation such as HTTP GET to one allowlisted health/status path may be considered. The proposed `/health` endpoint is not yet implemented or approved. Creating or deploying it would change the production service and is outside this read-only test baseline; no production code change or deployment is authorized here. Exact method, host, path, protocol, and response fields must be bound into the final charter.

**Prohibited in this baseline:**

- writes, mutations, business workflows, retries, redirects, arbitrary URL input, and automatic remediation;
- provider calls, deployment, credential discovery, customer contact, customer-data access, financial activity, or worker/venture execution;
- collecting response bodies or sensitive values in test logs;
- expanding to another host, endpoint, tenant, or operation.

Any required network or credential access remains denied unless separately specified, reviewed, and explicitly authorized for the exact test. This draft performs no access or probe.

## 4. Data boundary

- Use a dedicated synthetic test tenant and synthetic marker data only.
- Read only the minimum health/status fields required by the objective.
- Exclude customer records, personal data, transaction details, secrets, and production business payloads.
- If the endpoint can return excluded data, select another endpoint or do not proceed.
- Log only timestamps, probe count, status classification, latency, stop events, and necessary non-sensitive correlation identifiers.
- Data classification, privacy determination, evidence location, and retention period: TBD.

## 5. Proposed limits

- Targets: one.
- Tenant/venture: one dedicated synthetic test tenant, if applicable.
- Observer concurrency: one.
- Duration: 10 minutes.
- Probe frequency: one per minute; maximum 10 probes.
- Retries: zero.
- Writes/state changes: zero.
- Monetary exposure/loss: zero.
- P11 candidate upper ceiling remains 30 minutes; this baseline proposes 10 minutes.

These limits are proposed values, not an execution grant. The exact target and service owner must confirm any service-specific impact limit before P12 audit.

## 6. Safeguards and stop conditions

Before any separately authorized test, the service owner and test operator must confirm that monitoring is active and the stop mechanism has been rehearsed in a non-production environment.

Stop immediately on any of the following:

- unexpected response, failed owner-defined health criterion, or existing SLO breach;
- write/state-change attempt or any authority/action drift;
- indication of customer, personal, transaction, or secret data;
- impact threshold breach, lost monitoring, or evidence-integrity failure;
- service-owner, operator, or designated stop-authority request.

Numerical thresholds for error rate, latency, saturation, and other service impact are TBD and must be taken from the selected service's existing SLO/alerting configuration. The exact human stop authority and on-call/alert route are TBD. No alert route is contacted by this draft.

## 7. Recovery and containment

For a strictly read-only observer, the proposed recovery is to stop the observer and close its connection, with no application-state rollback. No retry, repair, or self-remediation is allowed.

- Non-production rehearsal environment and evidence: TBD.
- Operator runbook and stop command: TBD.
- If any state change or unexpected effect occurs, stop, preserve evidence, notify the service owner, and do not resume until the user makes a new decision.

## 8. Approvals, review, and decision authority

- Service-owner approval: Kalaap Das, subject to confirmation for the selected service.
- Security approval: TBD.
- Data/privacy approval: TBD; document whether the synthetic-only boundary makes a separate review applicable.
- Other required operational, legal, or compliance approvals: TBD based on the target and data boundary.
- Charter author and implementation: prepared by the assistant from user-provided facts and decisions.
- Independent reviewer and final decision authority: Kalaap Das, as stated by the user. The user reviews the exact artifacts and evidence and records the decision.
- The assistant may prepare materials and report technical observations; it does not decide ACCEPTED, BLOCKED, test pass/fail, or production readiness.
- P12 audit decision: the user's attributable ACCEPTED or BLOCKED decision must bind the exact charter hash and reviewed source commit. This draft has no such decision.

## 9. Evidence contract

Capture and preserve:

- exact charter bytes and SHA-256;
- source commit and configuration fingerprints;
- pre-test baseline and post-test summary;
- planned and actual probe count, timestamps, status classifications, and latency summaries;
- monitoring and stop-event evidence;
- confirmation of zero writes, zero monetary exposure/loss, and no sensitive data retained;
- approvals, operator identity/role, deviations, incidents, and the user's final audit decision.

Do not capture credentials, tokens, raw sensitive response bodies, or customer/personal data. Evidence store, access controls, retention period, and tamper-evidence method: TBD.

## 10. Open items before a complete charter

1. Identify the exact production environment and host serving ctkfamily.com; confirm the reported Linux/Apache/PHP details as needed for the plan.
2. Decide separately whether to create a minimal `/health` endpoint; first implement and inspect it in non-production, define exactly what `200 OK` means, and verify its response contains no sensitive information. Any production deployment requires its own explicit review and authorization.
3. If an endpoint is created or otherwise selected, bind its exact host/path, method, protocol, and response fields into the charter.
4. Identify whether a dedicated synthetic tenant applies.
5. Confirm the service's health criteria, SLOs, and impact thresholds.
6. Resolve whether tightly scoped network or credential access is required and obtain separate authorization if applicable.
7. Name the on-call contact/stop authority and approved alert route.
8. Complete service-owner, security, privacy, and any applicable operational approvals.
9. Specify rehearsal evidence, evidence store, retention, and access controls.
10. Bind the final charter hash and reviewed source commit for the user's P12 audit decision.

Until the open items are resolved and the user records the required decisions, this document remains an incomplete planning draft. It does not authorize P12 implementation or any production test.
