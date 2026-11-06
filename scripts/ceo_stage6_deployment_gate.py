"""Fail-closed Stage6 source gate and local read-only preflight. No deployment code.

Reconstruct exact recorded installed Python bytes inside the project. Historical
disk identity never attests current installations or loaded process bytes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "tests/acceptance-evidence/ceo-legacy-units-20261104/final.json"
OUT = ROOT / "tests/acceptance-evidence/ceo-stage6-20261104"
TREES = {
    "ceo": "/usr/local/lib/venture-ceo-level2c/",
    "broker": "/usr/local/lib/venture-control-broker-level2c/",
}
CANDIDATES = {
    "agents/ceo/ceo_research_review.py",
    "agents/ceo/hierarchy_providers.py",
    "agents/ceo/provider_gateway.py",
    "agents/ceo/provider_reservation.py",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def recorded_blob(rel, expected):
    path = ROOT / rel
    if path.is_file() and sha(path.read_bytes()) == expected:
        return path.read_bytes()
    history = subprocess.check_output(
        ["git", "log", "--format=%H", "--", rel], cwd=ROOT, text=True)
    for revision in history.splitlines():
        result = subprocess.run(["git", "show", revision + ":" + rel],
                                cwd=ROOT, capture_output=True)
        if result.returncode == 0 and sha(result.stdout) == expected:
            return result.stdout
    raise ValueError("Unreconstructable recorded Python source: " + rel)


def deployment_decision():
    """Existing Stage6 denial shared by deployment entrypoints; no override."""
    return dict(decision="DENY", deployment_allowed=False, resume_verified=False,
                reasons=["STAGE6_INDEPENDENT_OPERATIONAL_ACCEPTANCE_NOT_VERIFIED"])


def blockers(broker_reservation, broker_http, broker_entrypoint):
    # These are necessary source capabilities, never sufficient runtime proof.
    reasons = []
    if "CONTROL_LEDGER_V1" not in broker_reservation:
        reasons.append("INSTALLED_BROKER_REJECTS_TRACKED_CEO_RESERVATION")
    tree = ast.parse(broker_http)
    readonly = [node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "do_GET"]
    if not readonly or not any("exchange_sessions" in ast.unparse(node)
                              and "remote_reservations" in ast.unparse(node)
                              for node in readonly):
        reasons.append("NO_EXISTING_READ_ONLY_CEO_SESSION_AND_CALL_PROOF_API")
    if 'role="ceo"' not in broker_entrypoint and "role='ceo'" not in broker_entrypoint:
        reasons.append("BROKER_ENTRYPOINT_HAS_NO_CEO_EXECUTION_BINDING")
    # No user-supplied booleans can satisfy these independent evidence gaps.
    reasons.extend([
        "CURRENT_INSTALLED_AND_LOADED_BYTES_NOT_ATTESTED",
        "CEO_LOCAL_AUTHORITY_BINDING_NOT_PROVEN",
        "ACTIVE_PROCESS_AND_PENDING_WORK_ISOLATION_NOT_PROVEN",
        "GITHUB_CLAUDE_REVIEW_NOT_VERIFIED",
    ])
    return reasons


# C2A is an observation, never a maintained exclusion lease or joined proof.
PROC_ROOT = Path("/proc")
LIVE_C1_ROOT = Path("/usr/local/lib/venture-control-broker-level2c/artifacts")
IDENTITY_FIELDS = ("Id", "User", "FragmentPath", "ExecStart", "ControlGroup")


def broker_closed_observation(config, synthetic=False):
    """Probe C1 without drain/release/write or waiting. Locks die on return."""
    import fcntl
    import os
    from kernel.broker.isolated_mtls import MaintenanceAdmission
    control = active = None
    try:
        path = Path(config["path"])
        if synthetic:
            path.resolve().relative_to(ROOT)
        else:
            path.relative_to(LIVE_C1_ROOT)
        if not path.is_absolute() or str(path) != config["path"] or ".." in path.parts:
            return False
        # Reuse C1's inode/owner/mode checks, but open read-only, including
        # _check's pathname revalidation. Never call its mutating operations.
        class ReadOnlyAdmission(MaintenanceAdmission):
            def _open(self, active=False):
                import stat
                if not synthetic:
                    self.uid = config["uid"]
                    if type(self.uid) is not int or self.uid < 0:
                        raise ValueError("owner UID pin")
                directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
                fd = None
                try:
                    for part in self.path.parent.parts[1:]:
                        child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=directory)
                        os.close(directory)
                        directory = child
                        if os.fstat(directory).st_uid not in (0, self.uid):
                            raise ValueError("ancestor owner")
                    info = os.fstat(directory)
                    if (info.st_uid != self.uid or stat.S_IMODE(info.st_mode) != 0o700
                            or (info.st_dev, info.st_ino) != self.identity[4:]):
                        raise ValueError("directory pin")
                    fd = os.open(self.path.name + (".active" if active else ""),
                                 os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                 dir_fd=directory)
                    info = os.fstat(fd)
                    offset = 2 if active else 0
                    if (not stat.S_ISREG(info.st_mode) or info.st_uid != self.uid
                            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                            or (info.st_dev, info.st_ino) != self.identity[offset:offset+2]
                            or (active and info.st_size != 0)):
                        raise ValueError("file pin")
                    result, fd = fd, None
                    return result
                finally:
                    if fd is not None:
                        os.close(fd)
                    os.close(directory)
        gate = ReadOnlyAdmission(str(path), config["identity"])
        if not synthetic and config["uid"] != gate.uid:
            return False
        control = gate._open()
        gate._lock(control, fcntl.LOCK_EX, gate._deadline(0))
        active = gate._open(True)
        gate._lock(active, fcntl.LOCK_EX, gate._deadline(0))
        return gate._check(control) == b"CLOSED\n"
    except Exception:
        return False
    finally:
        for fd in (active, control):
            if fd is not None:
                os.close(fd)


def observe_local_writers(config=None):
    """Read selected systemd identities and all /proc writer metadata only."""
    import os
    result = dict(units=[], processes=[], jobs=[], errors=[])
    def systemctl(*args):
        return json.loads(subprocess.check_output(
            ["systemctl", *args, "--no-pager", "--output=json"],
            text=True, timeout=10))
    try:
        names = set()
        for row in systemctl("list-units", "--all", "--type=service,timer"):
            names.add(row["unit"])
        for row in systemctl("list-unit-files", "--type=service,timer"):
            names.add(row["unit_file"])
        for name in sorted(names if config is None else names & set(config["units"])):
            # Templates without instances cannot run; installed instances and
            # loaded/transient units are still independently enumerated.
            if "@." in name:
                continue
            raw = subprocess.check_output(
                ["systemctl", "show", name, "--no-pager",
                 "--property=" + ",".join((*IDENTITY_FIELDS, "LoadState",
                                            "MainPID", "ActiveState", "SubState"))],
                text=True, timeout=10)
            result["units"].append(dict(line.split("=", 1)
                                        for line in raw.splitlines() if "=" in line))
        result["jobs"] = systemctl("list-jobs")
    except Exception:
        result["errors"].append("SYSTEMD_OBSERVATION_INCOMPLETE")
    try:
        for entry in PROC_ROOT.iterdir():
            if not entry.name.isdecimal():
                continue
            try:
                # No environment, arguments, secret credentials or ledger reads.
                start = (entry / "stat").read_text().rsplit(")", 1)[1].split()[19]
                status = dict(line.split(":", 1) for line in
                              (entry / "status").read_text().splitlines() if ":" in line)
                writable = []
                for fd in (entry / "fd").iterdir():
                    target = os.readlink(fd)
                    flags = next(line.split()[1] for line in
                                 (entry / "fdinfo" / fd.name).read_text().splitlines()
                                 if line.startswith("flags:"))
                    if int(flags, 8) & os.O_ACCMODE in (os.O_WRONLY, os.O_RDWR):
                        writable.append(target)
                result["processes"].append(dict(
                    pid=int(entry.name), exe=os.readlink(entry / "exe"),
                    uids=[int(n) for n in status["Uid"].split()],
                    cap_eff=int(status["CapEff"], 16),
                    start=start,
                    writable_fds=sorted(writable),
                    cgroups=(entry / "cgroup").read_text().splitlines()))
                if (entry / "stat").read_text().rsplit(")", 1)[1].split()[19] != start:
                    result["errors"].append("PROCESS_IDENTITY_CHANGED")
            except (OSError, ValueError, KeyError, IndexError, StopIteration):
                result["errors"].append("PROCESS_OBSERVATION_INCOMPLETE")
    except OSError:
        result["errors"].append("PROC_UNAVAILABLE")
    return result


def validate_protected_roots(config):
    """Private roots: DAC confines access to pinned owners and privileged PIDs."""
    import stat
    identities = []
    for pin in config["protected_roots"]:
        path = Path(pin["path"])
        approved = (ROOT, *(Path(tree) / "artifacts" for tree in TREES.values()))
        if not any(path.is_relative_to(root) for root in approved):
            raise ValueError("unapproved protected root")
        if not path.is_absolute() or str(path.resolve()) != pin["path"]:
            raise ValueError("canonical protected root required")
        info = path.stat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
                or (info.st_uid, info.st_dev, info.st_ino) !=
                (pin["uid"], pin["dev"], pin["ino"])):
            raise ValueError("protected root identity")
        identities.append((info.st_dev, info.st_ino, info.st_uid, info.st_mode,
                           info.st_mtime_ns, info.st_ctime_ns))
    return identities


def process_metadata_known(process):
    uids = process.get("uids")
    groups = process.get("cgroups")
    fds = process.get("writable_fds")
    caps = process.get("cap_eff")
    return (isinstance(uids, list) and len(uids) == 4
            and all(type(uid) is int and uid >= 0 for uid in uids)
            and isinstance(fds, list) and all(isinstance(fd, str) for fd in fds)
            and type(caps) is int and caps >= 0 and bool(process.get("start"))
            and isinstance(groups, list) and bool(groups)
            and all(isinstance(g, str) and len(g.split(":", 2)) == 3
                    and g.split(":", 2)[2].startswith("/") for g in groups)
            and isinstance(process.get("exe"), str) and process["exe"].startswith("/"))


def protected_writer(process, config):
    """Unknown metadata denies; unrelated UIDs without write FDs can pass."""
    if not process_metadata_known(process):
        return True
    uids, groups = process["uids"], process["cgroups"]
    fds, caps = process["writable_fds"], process["cap_eff"]
    owners = {p["uid"] for p in config["protected_roots"]}
    owners.update(p["uid"] for p in config["units"].values())
    if 0 in uids or owners.intersection(uids) or caps & sum(1 << bit for bit in (0, 1, 2, 3, 6, 7, 8, 16, 17, 18, 19, 21, 32)):
        return True
    for group in groups:
        actual = group.split(":", 2)[2]
        if any(actual == p["writer_cgroup"] or actual.startswith(p["writer_cgroup"] + "/")
               for p in config["units"].values()):
            return True
    for fd in fds:
        target = fd.removesuffix(" (deleted)")
        if any(target == p["path"] or target.startswith(p["path"] + "/")
               for p in config["protected_roots"]):
            return True
    return False


def writer_exclusion_preflight(config=None, snapshot=None):
    """Pinned local observation only; never a maintained exclusion lease.

    Legacy snapshots retain C2A semantics. Live observations require private
    protected-root and writer UID/cgroup pins and stable repeated samples.
    """
    synthetic = snapshot is not None
    reasons = []
    report = dict(decision="DENY", deployment_allowed=False,
                  resume_verified=False, local_exclusion_ready=False,
                  cross_vm_coverage_verified=False, atomic_snapshot=False,
                  loaded_bytes_verified=False, scope="ONE_HOST_ONLY",
                  units=[], processes=[], broker_closed_no_leases_observed=False,
                  classification=("SYNTHETIC_SNAPSHOT" if synthetic else
                                  "READ_ONLY_NONATOMIC_LOCAL_METADATA"))
    try:
        if not isinstance(config, dict) or not config.get("units"):
            raise ValueError("unconfigured")
        pins = config["units"]
        if not isinstance(pins, dict):
            raise ValueError("unit pins")
        for name, pin in pins.items():
            if (not name.endswith((".service", ".timer"))
                    or pin.get("role") not in
                    ("manager", "worker", "ceo", "api", "timer", "broker", "other")
                    or any(not isinstance(pin.get(k), str) for k in IDENTITY_FIELDS)
                    or pin["Id"] != name or not pin["FragmentPath"]
                    or pin.get("role") == "timer" and not name.endswith(".timer")):
                raise ValueError("identity pins")
        broker_names = [n for n, p in pins.items() if p["role"] == "broker"]
        if len(broker_names) > 1:
            raise ValueError("broker identity")
        bounded = bool(config.get("protected_roots"))
        if not synthetic and not bounded:
            raise ValueError("protected roots required")
        if bounded:
            roots_before = validate_protected_roots(config)
            if any(type(p.get("uid")) is not int or p["uid"] <= 0
                   or not p.get("writer_cgroup", "").startswith("/") for p in pins.values()):
                raise ValueError("writer UID/cgroup pins required")
        observed = snapshot if synthetic else observe_local_writers(config)
        if any(not isinstance(observed[k], list)
               for k in ("units", "processes", "jobs", "errors")):
            raise ValueError("observation shape")
        if observed["errors"]:
            reasons.append("INCOMPLETE_LOCAL_OBSERVATION")
        if any(not bounded or not isinstance(job.get("unit"), str)
               or job["unit"] in pins for job in observed["jobs"]):
            reasons.append("ACTIVE_SYSTEMD_TASKS")
        seen = set()
        allowed_pid = None
        broker = config.get("broker")
        if broker and (len(broker_names) != 1 or broker.get("unit") != broker_names[0]):
            raise ValueError("broker configuration identity")
        # Synthetic snapshots cannot supply a broker-ready boolean. Tests
        # exercise the same real C1 files and locks in project-local fixtures.
        broker_closed = broker_closed_observation(broker, synthetic=synthetic) if broker else False
        report["broker_closed_no_leases_observed"] = broker_closed
        if broker_names and not broker:
            reasons.append("BROKER_C1_UNCONFIGURED")
        if broker and not broker_closed:
            reasons.append("BROKER_C1_NOT_CLOSED_AND_DRAINED")
        for unit in observed["units"]:
            name = unit["Id"]
            pin = pins.get(name)
            report["units"].append({k: unit.get(k) for k in
                                    ("Id", "MainPID", "ActiveState", "SubState", "ControlGroup")})
            if name in seen or pin is None:
                reasons.append("UNKNOWN_OR_DUPLICATE_UNIT")
                continue
            seen.add(name)
            if (unit.get("LoadState") != "loaded"
                    or any(unit.get(k) != pin[k] for k in IDENTITY_FIELDS)):
                reasons.append("UNIT_IDENTITY_MISMATCH")
            if name.endswith(".service") and "MainPID" not in unit:
                raise ValueError("missing service MainPID")
            pid = int(unit.get("MainPID", "0"))
            if pid < 0:
                raise ValueError("pid")
            inactive = (unit.get("ActiveState") == "inactive"
                        and unit.get("SubState") == "dead" and pid == 0
                        and not unit.get("ControlGroup"))
            if inactive:
                continue
            if (pin["role"] == "broker" and broker_closed
                    and unit.get("ActiveState") == "active"
                    and unit.get("SubState") == "running" and pid > 0
                    and pin["ControlGroup"].startswith("/")
                    and broker.get("unit") == name
                    and broker.get("exe", "").startswith("/")):
                allowed_pid = pid
            else:
                reasons.append("ACTIVE_OR_UNCERTAIN_WRITER_UNIT")
        if seen != set(pins):
            reasons.append("MISSING_EXPECTED_UNITS")
        process_ids = set()
        for process in observed["processes"]:
            pid = process["pid"]
            if type(pid) is not int or pid <= 0 or pid in process_ids:
                raise ValueError("process identity")
            process_ids.add(pid)
            report["processes"].append(dict(pid=pid, exe=process.get("exe"),
                                            cgroups=process.get("cgroups")))
            if bounded and not process_metadata_known(process):
                reasons.append("UNKNOWN_PROCESS_METADATA")
                continue
            if pid != allowed_pid:
                if not bounded or protected_writer(process, config):
                    reasons.append("UNKNOWN_OR_EXTRA_PROCESS_WRITER")
                continue
            if bounded and process.get("uids") != [pins[broker["unit"]]["uid"]] * 4:
                reasons.append("BROKER_PROCESS_IDENTITY_MISMATCH")
            group = pins[broker["unit"]]["ControlGroup"]
            groups = process["cgroups"]
            if (process["exe"] != broker["exe"] or not groups
                    or any(line.split(":", 2)[2] != group for line in groups)):
                reasons.append("BROKER_PROCESS_IDENTITY_MISMATCH")
        if allowed_pid is not None and allowed_pid not in process_ids:
            reasons.append("BROKER_MAINPID_NOT_OBSERVED")
        if not synthetic:
            after = observe_local_writers(config)
            if after != observed:
                reasons.append("LOCAL_OBSERVATION_CHANGED")
            if broker and not broker_closed_observation(broker, synthetic=False):
                reasons.append("BROKER_C1_CHANGED")
        if bounded and validate_protected_roots(config) != roots_before:
            reasons.append("PROTECTED_ROOTS_CHANGED")
    except Exception:
        reasons.append("UNCONFIGURED_OR_INVALID_LOCAL_EVIDENCE")
    report["local_exclusion_ready"] = not reasons
    report["reasons"] = sorted(set(reasons))
    report["blockers"] = ["SEPARATE_JOINED_PROOF_REQUIRED",
                          "CURRENT_LOADED_BYTES_AND_REVIEW_NOT_VERIFIED"]
    return report


def project_json(path):
    candidate = Path(path).resolve()
    candidate.relative_to(ROOT)
    if candidate.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("input too large")
    return json.loads(candidate.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--reconstruct", action="store_true",
                        help="write public recorded Python sources under artifacts")
    modes.add_argument("--assess-boundary", action="store_true",
                        help="read-only detection only; always denies deployment/resume")
    modes.add_argument("--preflight-resume", action="store_true",
                       help="probe CEO cooperative exclusion; deployment remains DENY")
    modes.add_argument("--preflight-writers", action="store_true",
                       help="read-only ONE_HOST evidence; always Stage6 DENY")
    parser.add_argument("--writer-config")
    parser.add_argument("--writer-snapshot", help="synthetic test evidence only")
    parser.add_argument("--deployment-lock")
    for name in ("workflow", "resources", "ceo-calls", "public-trust"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    if args.preflight_writers:
        if any((args.deployment_lock, args.workflow, args.resources,
                args.ceo_calls, args.public_trust)):
            parser.error("writer preflight accepts only writer inputs")
        sys.path.insert(0, str(ROOT))
        try:
            config = project_json(args.writer_config) if args.writer_config else None
            snapshot = project_json(args.writer_snapshot) if args.writer_snapshot else None
            if args.writer_snapshot and not isinstance(snapshot, dict):
                raise ValueError("invalid synthetic snapshot")
            result = writer_exclusion_preflight(config, snapshot)
        except Exception:
            result = writer_exclusion_preflight()
            result["classification"] = "INVALID_INPUT"
        print(json.dumps(result, sort_keys=True))
        return 2
    if args.writer_config or args.writer_snapshot:
        parser.error("writer inputs require --preflight-writers")
    if args.preflight_resume:
        if any((args.workflow, args.resources, args.ceo_calls, args.public_trust)):
            parser.error("preflight does not accept partial state coverage")
        sys.path.insert(0, str(ROOT))
        from agents.ceo.deployment_pause import preflight
        print(json.dumps(preflight(args.deployment_lock), sort_keys=True))
        return 2
    if args.deployment_lock:
        parser.error("--deployment-lock requires --preflight-resume")
    if args.assess_boundary:
        sys.path.insert(0, str(ROOT))
        from agents.ceo.resume_boundary import assess, fingerprint
        from agents.ceo.escalation_inbox import inside_root
        try:
            trust = inside_root(args.public_trust)
            before = fingerprint(trust)
            if trust.stat().st_size > 65536:
                raise ValueError("public trust bound")
            pins = json.loads(trust.read_bytes())["actors"]
            actors = {actor: (pin["role"], bytes.fromhex(pin["public_key"]))
                      for actor, pin in pins.items()}
            result = assess(workflow=args.workflow, resources=args.resources,
                            ceo_calls=args.ceo_calls, actors=actors)
            if fingerprint(trust) != before:
                result.update(observation="UNKNOWN", reasons=["PUBLIC_PINS_CHANGED"])
        except Exception:
            result = dict(decision="HOLD", deployment_allowed=False,
                          resume_verified=False, dry_run=True,
                          reasons=["INVALID_OR_UNREADABLE_INPUT"])
        print(json.dumps(result, sort_keys=True))
        return 2
    if any((args.workflow, args.resources, args.ceo_calls, args.public_trust)):
        parser.error("state paths require --assess-boundary")
    assert Path.cwd().resolve() == ROOT
    hashes = json.loads(RECORD.read_text())["hashes"]
    manifest, sources = [], {}
    target = ROOT / "artifacts/ceo-stage6-installed"
    for tree, prefix in TREES.items():
        for installed, expected in sorted(hashes.items()):
            if not installed.startswith(prefix) or not installed.endswith(".py"):
                continue
            rel = installed[len(prefix):]
            if Path(rel).is_absolute() or ".." in Path(rel).parts:
                raise ValueError("Unsafe recorded path")
            raw = recorded_blob(rel, expected)
            sources[tree, rel] = raw.decode()
            candidate = (ROOT / rel).read_bytes() if tree == "ceo" and rel in CANDIDATES else raw
            manifest.append(dict(tree=tree, path=rel, installed_sha256=expected,
                                 candidate_sha256=sha(candidate),
                                 candidate_override=candidate != raw))
            if args.reconstruct:
                for profile, content in (("installed", raw), ("candidate", candidate)):
                    destination = target / profile / tree / rel
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(content)
    reasons = blockers(
        sources["broker", "agents/ceo/provider_reservation.py"],
        sources["broker", "kernel/broker/isolated_mtls.py"],
        sources["broker", "kernel/broker/mtls_server.py"])
    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(classification="EXACT_RECORDED_INSTALLED_SOURCE_RECONSTRUCTION",
                  source_record_sha256=sha(RECORD.read_bytes()),
                  deployment_allowed=False, blockers=reasons,
                  current_installation_verified=False, production_state_accessed=False,
                  files=manifest)
    (OUT / "deployment-gate.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(deployment_allowed=False, blockers=reasons,
                         reconstructed_python_files=len(manifest)), indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
