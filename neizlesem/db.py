"""SQLite tabanlı küçük depo: API önbelleği + IMDb resmi puan tablosu.

Her işlem kendi bağlantısını açar; bu sayede paralel iş parçacıkları güvenle yazabilir.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS imdb_ratings (
    tconst TEXT PRIMARY KEY,
    rating REAL NOT NULL,
    votes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=20)

    # ---- önbellek -------------------------------------------------------
    def cache_get(self, key: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if not row or row[1] < time.time():
            return None
        return json.loads(row[0])

    def cache_set(self, key: str, value, ttl: float) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                    (key, payload, time.time() + ttl),
                )
        except sqlite3.OperationalError:
            # Yoğun anda kilitlenirse önbelleğe yazmamak sorun değil.
            pass

    def cache_clear(self, expired_only: bool = True) -> int:
        with self._conn() as conn:
            if expired_only:
                cur = conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            else:
                cur = conn.execute("DELETE FROM cache")
            return cur.rowcount

    # ---- IMDb resmi puanları --------------------------------------------
    def imdb_get(self, tconst: str):
        if not tconst:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT rating, votes FROM imdb_ratings WHERE tconst = ?", (tconst,)
            ).fetchone()
        return {"rating": row[0], "votes": row[1]} if row else None

    def imdb_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM imdb_ratings").fetchone()[0]

    def imdb_replace(self, rows: Iterable[tuple[str, float, int]], chunk: int = 5000) -> int:
        """Tabloyu tek işlemde yeniler; yarıda kalırsa eski veri korunur."""
        total = 0
        conn = self._conn()
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM imdb_ratings")
            batch = []
            for row in rows:
                batch.append(row)
                if len(batch) >= chunk:
                    conn.executemany("INSERT OR REPLACE INTO imdb_ratings VALUES (?, ?, ?)", batch)
                    total += len(batch)
                    batch.clear()
            if batch:
                conn.executemany("INSERT OR REPLACE INTO imdb_ratings VALUES (?, ?, ?)", batch)
                total += len(batch)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return total

    # ---- meta -----------------------------------------------------------
    def meta_get(self, key: str, default=None):
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def meta_set(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))
