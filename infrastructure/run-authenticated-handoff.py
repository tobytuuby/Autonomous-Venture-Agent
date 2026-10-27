"""Start a separate transient verification-only timer; no key provisioning.

All files created here stay in ignored project artifacts, owned by root, 0700/
0600. Does not replace, stop or restart any existing service/timer. No /etc unit
installation, private key, provider configuration or owner enrollment.
"""
from pathlib import Path
import configparser
import os
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents.ceo.authenticated_handoff import private_directory, private_json
from agents.ceo.scheduled_exercise import write_json


def main():
    if os.geteuid() != 0 or Path.cwd().resolve() != ROOT:
        raise SystemExit("Trusted operator must run from approved project root")
    base = ROOT / "artifacts/authenticated-handoff"
    from agents.ceo.escalation_inbox import inside_root
    for path in (base, base / "state", base / "ingress", base / "requests"):
        inside_root(path)
        if not path.exists():
            path.mkdir(mode=0o700)
        private_directory(path)
    trust = base / "ingress/trust.json"
    if not trust.exists():
        write_json(trust, dict(actors={}), exclusive=True)
    private_json(trust)  # Never replace or enroll any identity.
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read(ROOT / "infrastructure/systemd/venture-authenticated-handoff.service")
    args = ["/usr/bin/systemd-run", "--unit=venture-authenticated-handoff",
            "--description=Authenticated preparation handoff; no signer",
            "--on-active=2s", "--on-unit-active=1h", "--timer-property=AccuracySec=1min"]
    for key, value in config["Service"].items():
        if key != "ExecStart":
            args.append("--property=" + key + "=" + value)
    args.extend(shlex.split(config["Service"]["ExecStart"]))
    subprocess.run(args, check=True)
    print("Transient verification-only timer requested; verify Result and private status artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
