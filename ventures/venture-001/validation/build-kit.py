"""Deterministically rebuild the two-file buyer ZIP from repository root."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

base = Path("ventures/venture-001")
with ZipFile(base / "Studio-Restock-Kit-v1.0.zip", "w") as archive:
    for name in ("START-HERE.md", "restock.html"):
        entry = ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
        entry.compress_type = ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, (base / "product" / name).read_bytes())
