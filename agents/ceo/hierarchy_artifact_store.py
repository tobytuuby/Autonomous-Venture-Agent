"""Small durable immutable store for signed preparation evidence.

Artifacts are untrusted until their SHA-256 is validated against the signed
workflow command. No artifacts are executable or suitable for external release.
"""
import hashlib
import sqlite3
from pathlib import Path

PREFIX = "preparation-"
MAX_BYTES = 10000


class DurableRoleArtifactStore:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.is_symlink() or not self.path.parent.is_dir():
            raise ValueError("durable existing artifact directory required")
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS artifacts(
            ref TEXT PRIMARY KEY, content BLOB NOT NULL)""")

    def store(self, ref, content):
        if (type(content) is not bytes or not 1 <= len(content) <= MAX_BYTES
                or type(ref) is not str
                or ref != PREFIX + hashlib.sha256(content).hexdigest()):
            raise ValueError("immutable artifact digest mismatch")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT content FROM artifacts WHERE ref=?", (ref,)).fetchone()
            if row is None:
                self.db.execute("INSERT INTO artifacts VALUES (?,?)", (ref, content))
            elif row[0] != content:
                raise ValueError("conflicting artifact denied")
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def load(self, ref):
        if type(ref) is not str or not ref.startswith(PREFIX):
            raise ValueError("artifact reference denied")
        row = self.db.execute("SELECT content FROM artifacts WHERE ref=?", (ref,)).fetchone()
        if row is None or not isinstance(row[0], bytes):
            raise ValueError("missing preparation artifact")
        content = row[0]
        if len(content) > MAX_BYTES or ref != PREFIX + hashlib.sha256(content).hexdigest():
            raise ValueError("artifact corruption")
        return content

    def close(self):
        self.db.close()
