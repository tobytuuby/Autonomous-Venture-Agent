"""P7.0 matrix case registry.

The registry is data, not authority. It defines the required case denominator
for synthetic execution and evidence production.
"""

AUTHORITIES = (
    "network",
    "broker",
    "payment",
    "credential",
    "deployment",
    "customer",
    "capital",
    "venture",
    "worker",
)

STATE_FAMILIES = (
    "request",
    "approval",
    "dispatch",
    "response",
    "reconciliation",
    "failure",
    "freeze",
    "revoke",
    "quarantine-wind-down",
)

RECOVERY_CONTROLS = (
    "freeze",
    "revoke",
    "quarantine",
    "restore",
    "rollback",
    "wind-down",
)

RECOVERY_MODES = ("normal", "injected-failure")


def authority_cases():
    return tuple(
        {
            "case_id": (
                f"P7.5.AUTHORITY.{authority}.{state}.{index:03d}"
            ),
            "authority": authority,
            "state": state,
        }
        for index, (authority, state) in enumerate(
            ((a, s) for a in AUTHORITIES for s in STATE_FAMILIES),
            start=1,
        )
    )


def recovery_cases():
    return tuple(
        {
            "case_id": f"P7.5.RECOVERY.{control}.{mode}.{index:03d}",
            "control": control,
            "mode": mode,
        }
        for index, (control, mode) in enumerate(
            ((c, m) for c in RECOVERY_CONTROLS for m in RECOVERY_MODES),
            start=1,
        )
    )
