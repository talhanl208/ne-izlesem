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
        is_new = not Path(path).exists()
        conn = sqlite3.connect(path, timeout=20, isolation_level=None)
        try:
            if is_new:
                # Silinen kayıtların yeri diske geri verilebilsin (dosya şişmesin)
                conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

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
            count = cur.rowcount
        self.reclaim_space()
        return count

    def cache_bytes(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COALESCE(SUM(LENGTH(value)), 0) FROM cache").fetchone()[0]

    def cleanup(self, max_bytes: int | None = None) -> dict:
        """Süresi dolan kayıtları siler; önbellek max_bytes'ı aşarsa en eskilerden
        başlayarak sınırın %80'ine kadar budar ve boşalan yeri diske geri verir."""
        stats = {"expired": 0, "trimmed": 0}
        with self._conn() as conn:
            stats["expired"] = conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),)).rowcount

        if max_bytes:
            size = self.cache_bytes()
            if size > max_bytes:
                target = int(max_bytes * 0.8)
                doomed: list[str] = []
                with self._conn() as conn:
                    for key, length in conn.execute("SELECT key, LENGTH(value) FROM cache ORDER BY expires_at ASC"):
                        if size <= target:
                            break
                        doomed.append(key)
                        size -= length
                for i in range(0, len(doomed), 500):
                    part = doomed[i:i + 500]
                    with self._conn() as conn:
                        conn.execute(f"DELETE FROM cache WHERE key IN ({','.join('?' * len(part))})", part)
                stats["trimmed"] = len(doomed)

        self.reclaim_space()
        stats["bytes"] = self.cache_bytes()
        return stats

    def reclaim_space(self) -> None:
        """Boşalan sayfaları diske geri ver. Eski veritabanlarını bir kereliğine
        artımlı moda çevirir (VACUUM), sonra her seferinde ucuz incremental_vacuum."""
        conn = sqlite3.connect(self.path, timeout=60, isolation_level=None)
        try:
            mode = conn.execute("PRAGMA auto_vacuum").fetchone()[0]
            if mode != 2:
                conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
                conn.execute("VACUUM")
            else:
                # Her adım bir sayfa boşaltır; hepsinin çalışması için sonucu tüket
                conn.execute("PRAGMA incremental_vacuum").fetchall()
        except sqlite3.OperationalError:
            pass  # o an meşgulse bir sonraki bakımda yapılır
        finally:
            conn.close()

    def file_bytes(self) -> int:
        try:
            return Path(self.path).stat().st_size
        except OSError:
            return 0

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
