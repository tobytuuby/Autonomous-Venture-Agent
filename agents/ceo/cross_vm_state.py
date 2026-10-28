"""Durable fail-closed replay and task reservation for preparation-only handoffs.

Independent store per trust boundary. Never grants execution, owner or finance
authority. An ambiguous network delivery keeps its reservation indefinitely.
"""
import sqlite3
from pathlib import Path


class DurableHandoffState:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.parent.is_dir():
            raise ValueError("state parent must exist")
        self.db = sqlite3.connect(str(self.path), isolation_level=None, timeout=5)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS nonces(actor TEXT NOT NULL, nonce TEXT NOT NULL, expires_at TEXT NOT NULL, PRIMARY KEY(actor,nonce))")
        self.db.execute("CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'RESERVED')")

    def close(self):
        self.db.close()

    def _reserve(self, statement, params):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            cursor = self.db.execute(statement, params)
            self.db.execute("COMMIT")
            return cursor.rowcount == 1
        except sqlite3.IntegrityError:
            self.db.execute("ROLLBACK")
            return False
        except Exception:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def consume_nonce(self, actor, nonce, expires_at):
        if any(type(x) is not str or not x for x in (actor, nonce, expires_at)):
            raise ValueError("nonce arguments invalid")
        return self._reserve(
            "INSERT INTO nonces(actor,nonce,expires_at) VALUES(?,?,?)",
            (actor, nonce, expires_at))

    def reserve_task(self, task_id, content_sha256):
        if (type(task_id) is not str or not task_id or
                type(content_sha256) is not str or len(content_sha256) != 64):
            raise ValueError("task arguments invalid")
        return self._reserve(
            "INSERT INTO tasks(task_id,content_sha256) VALUES(?,?)",
            (task_id, content_sha256))

    def task_status(self, task_id):
        row = self.db.execute("SELECT content_sha256,state FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return dict(content_sha256=row[0], state=row[1]) if row else None
