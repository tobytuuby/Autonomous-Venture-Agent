"""Optional VM-only setup: extract runtime libraries/fonts inside artifacts; no system install.
Requires the existing Playwright/Chromium installation and Ubuntu apt package indexes.
This is validation infrastructure, never a customer prerequisite.
"""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[3]
os.chdir(root)
base = root / "artifacts/venture-001-browser"
debs = base / "debs"
libroot = base / "libroot"
debs.mkdir(parents=True, exist_ok=True)
packages = [
    "libatk1.0-0t64", "libatk-bridge2.0-0t64", "libxcomposite1", "libxdamage1",
    "libxfixes3", "libxrandr2", "libgbm1", "libasound2t64", "libatspi2.0-0t64",
    "libxrender1", "libxi6", "libxres1", "fonts-liberation", "fonts-dejavu-core",
]
subprocess.run(["apt-get", "download", *packages], cwd=debs, check=True)
for archive in sorted(debs.glob("*.deb")):
    subprocess.run(["dpkg-deb", "-x", str(archive), str(libroot)], check=True)
(base / "fonts.conf").write_text(
    '<?xml version="1.0"?><fontconfig>'
    f'<dir>{libroot}/usr/share/fonts</dir>'
    f'<cachedir>{base}/font-cache</cachedir></fontconfig>\n'
)
with (base / "runtime-packages.txt").open("w") as output:
    for archive in sorted(debs.glob("*.deb")):
        subprocess.run(["dpkg-deb", "--show", str(archive)], stdout=output, check=True)
print("Workspace-local browser libraries and fonts ready. No system packages changed.")
