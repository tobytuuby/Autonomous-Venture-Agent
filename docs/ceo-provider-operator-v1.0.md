# Shadow venture inference operator entrypoint — v1.0

The existing CEOAgent, durable state, synthetic manager/workers and CEO review
are used without granting live authority. This is an implementation/operator
guide, not a new phase authorization, certification or change to policy.

## Operator setup and execution

An authorized operator must provide these four environment variables through
their approved secret injection mechanism to the process running the command:

- CEO_MODEL_ENDPOINT: the approved model-only HTTPS API base including its version
  path (the adapter appends /chat/completions). No credentials, query or fragment.
- CEO_MODEL_NAME: a model supporting chat completions and plain JSON content.
- CEO_MODEL_TOKEN: a credential scoped to inference for that service.
- CEO_KERNEL_GATE_FILE: an existing, reviewed pre-model certification JSON record
  inside the approved project root. The existing ADV-001..ADV-049 gate is required.

Do not copy a gate example into place as certification, store a token in Git or
command arguments, print secret environment values, or reuse an unrestricted
coding agent as this provider. Provider-side execution restrictions must be
established by the operator; a text-only request does not prove what an arbitrary
remote service does internally. No provider tools, hosted tools, local shell,
browser, files or business actions are available through this advisory flow.

Run from /home/epsilon/venture-control-workspace with the injected environment:

```sh
python3 -m agents.ceo.venture_exercise --durable-ceo --require-provider --check-provider
python3 -m agents.ceo.venture_exercise --durable-ceo --require-provider \
  --database artifacts/provider-venture.sqlite \
  --report artifacts/provider-venture.json
```

The first command checks configuration and the existing gate, creates no output
files, and makes no inference/network request. Its success is not a reachability
or authentication result. The second sends up to three sequential inference
requests: evaluation, manager planning, CEO review. Shelving all candidates stops
after evaluation. Worker functions run locally over hypothetical inputs only.
Each complete response must pass the existing semantic/authority validators.
The registry allocation remains synthetic and available-to-spend remains zero.

The required-provider option cannot select fixtures and requires durable CEO
mode. Partial configuration and failed gates cannot select fixtures either.
The legacy unconfigured exercise remains an explicitly labeled fixture exercise.
Advisory HTTP bodies contain only model and messages; they omit tools,
tool_choice and the formerly hard-coded reasoning_effort parameter. The HTTPS
adapter refuses redirects to prevent forwarding its bearer credential.

CLI exit codes: 0 = completed or configuration-only check valid; 2 = provider
configuration/transport/envelope denied; 3 = pre-model certification not satisfied;
4 = local path/state or semantic validation denied. Argument errors also exit 2.
Remote exception chains and error bodies are suppressed from CLI output.

Use a fresh database name for a changed provider/configuration. The runner
fingerprint is venture-exercise-v3; existing v2 records are preserved and conflict
rather than being silently rebound. Completed decisions replay without inference.
Rejected/quarantined decisions remain terminal; investigate the recorded states,
then use a fresh run only after fixing the problem. A crash before response
persistence may repeat an advisory request. There is no exactly-once or concurrent
runner guarantee.

## Existing service and credential boundary

Read-only systemd metadata on 2026-10-26 showed venture-ceo-shadow.service loaded
and inactive, running as venture-ceo, with NoNewPrivileges=yes,
ProtectSystem=strict, ProtectHome=read-only and PrivateTmp=yes. Its environment
file references include /etc/venture-ceo.env and /etc/venture-ceo-shadow.env.
Those references do not prove that credentials exist or are usable. No protected
file or service environment value was read. CanStart=yes describes unit
capability, not the caller's permission to start it.

The installed ExecStart is python3 -m agents.ceo.runner. That runner checks
readiness and constructs an agent; it does not perform the three-stage exercise.
Its writable directory is /var/lib/venture-ceo, while the exercise confines
artifacts and gate paths to this project. Starting that unchanged unit cannot
demonstrate this flow. No service was started, overridden, installed or granted
additional permissions, and no credential was extracted from another account.
A service-owned credential remains unverified and was not repurposed.

The remaining operator action is to make an approved, restricted inference
service's endpoint/model/token and the existing legitimate project-local gate
available to a permitted project process, then run the two commands above.
If the operator chooses service-account execution instead, they must separately
review its entrypoint and project artifact access while preserving its hardening;
this change does not install or authorize such a service alteration.

## Evidence limits

The accompanying implementation report and raw tests establish mocked HTTP
execution, fail-closed behavior and durable replay. They establish no live
inference, endpoint reachability, provider authentication, provider-side tool
isolation or independent certification. Configured response provenance retains
configured_provider_response_not_independently_verified and never promotes a
test double into genuine inference evidence. All existing live authority fields
remain false; model output is never execution authorization.
