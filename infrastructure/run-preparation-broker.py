"""Deploy only a transient local preparation timer; all project writes stay in root.

No /etc unit installation. Timer disappears on reboot. Run with sudo from root.
"""
from pathlib import Path
import configparser
import os
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents.ceo.service_identity import provision, ServiceIdentities

if __name__ == "__main__":
    if os.geteuid() != 0 or Path.cwd().resolve() != ROOT:
        raise SystemExit("Run as the trusted service operator from the approved project root")
    state = ROOT / "artifacts/milestone1-service"
    if not state.exists():
        state.mkdir(mode=0o700)
    if not list(state.iterdir()):
        provision(state)
    else:
        ServiceIdentities(state)  # Never rotate or repair partial identity state.
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read(ROOT / "infrastructure/systemd/venture-preparation-broker.service")
    args = ["/usr/bin/systemd-run", "--unit=venture-preparation-broker",
            "--description=Deterministic preparation attestation only",
            "--on-active=2s", "--on-unit-active=1h", "--timer-property=AccuracySec=1min"]
    for key, value in config["Service"].items():
        if key != "ExecStart":
            args.append("--property=" + key + "=" + value)
    args.extend(shlex.split(config["Service"]["ExecStart"]))
    subprocess.run(args, check=True)
    print("Transient preparation timer requested; verify service Result and status artifact.")
