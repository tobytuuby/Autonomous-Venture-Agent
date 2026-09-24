# P8.0 Test and Evidence Plan

## Denominator

P8.0 has 13 focused test methods covering:

- valid bounded charter;
- all nine live-authority denials;
- live credential and live-mode denials;
- model-output denial;
- one-venture and one-authority-class enforcement;
- numeric ceiling validation;
- operating-window validation;
- approver/monitoring/reconciliation/stop requirements;
- pending written approval;
- hard denial of live action;
- automatic-stop fail-closed behavior;
- charter collision and snapshot integrity;
- all-false authority fingerprint.

The authoritative full regression must report its exact post-change count.

## Evidence requirements

Preserve:

- focused runtime log;
- full-regression log;
- source and test inventories with Git blob SHA and SHA-256;
- JSON schema validation result;
- charter configuration fingerprint;
- before/after authority fingerprints;
- zero external actions, unauthorized actions, and live credentials;
- technical and non-technical reports;
- completed charter and separate live-action approval only before any P8.1 consideration.

A passing P8.0 preflight is not evidence that a live action occurred or is authorized.
