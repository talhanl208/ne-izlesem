import gzip
import io
import sqlite3
import time

from neizlesem import create_app, maintenance
from neizlesem.db import Store
from tests.fakes import FakeSession

CFG = {"CACHE_MAX_MB": 150, "CLEANUP_INTERVAL_HOURS": 6, "IMDB_AUTO_UPDATE_DAYS": 30}


def _gz(rows: str) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as fh:
        fh.write(rows.encode())
    return buf.getvalue()


class DatasetResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self.body), chunk_size):
            yield self.body[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class DatasetSession:
    def __init__(self, body: bytes | None = None, status: int = 200):
        self.body, self.status, self.calls = body, status, 0

    def get(self, url, **kw):
        self.calls += 1
        return DatasetResponse(self.body or b"", self.status)


def test_new_database_uses_incremental_vacuum(tmp_path):
    store = Store(str(tmp_path / "yeni.db"))
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA auto_vacuum").fetchone()[0] == 2


def test_old_database_is_converted_on_cleanup(tmp_path):
    path = tmp_path / "eski.db"
    sqlite3.connect(path).execute("CREATE TABLE x (a)").connection.close()  # auto_vacuum=0
    store = Store(str(path))
    store.cleanup()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA auto_vacuum").fetchone()[0] == 2


def test_cleanup_removes_expired_and_trims_to_cap(tmp_path):
    store = Store(str(tmp_path / "c.db"))
    store.cache_set("eski", "x" * 1000, ttl=-10)
    for i in range(50):
        store.cache_set(f"k{i:02d}", "y" * 10_000, ttl=1000 + i)
    stats = store.cleanup(max_bytes=200_000)
    assert stats["expired"] == 1
    assert stats["bytes"] <= 160_000 and stats["trimmed"] > 0
    # en eskiler gitti, en yeniler kaldı
    assert store.cache_get("k00") is None
    assert store.cache_get("k49") is not None


def test_cleanup_shrinks_file(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    for i in range(300):
        store.cache_set(f"k{i}", "z" * 20_000, ttl=-1)
    before = store.file_bytes()
    store.cleanup()
    assert store.file_bytes() < before / 3


def test_due_tasks_schedule(tmp_path):
    store = Store(str(tmp_path / "d.db"))
    now = time.time()
    assert due_tasks(store, now) == ["cleanup", "imdb"]          # hiç yapılmamış
    store.meta_set("last_cleanup", now)
    store.meta_set("imdb_updated_ts", now)
    assert due_tasks(store, now + 3600) == []                    # 1 saat sonra: bir şey yok
    assert due_tasks(store, now + 7 * 3600) == ["cleanup"]       # 7 saat sonra: temizlik
    assert "imdb" in due_tasks(store, now + 31 * 86400)          # 31 gün sonra: IMDb


def due_tasks(store, now):
    return maintenance.due_tasks(store, CFG, now)


def test_existing_manual_imdb_import_is_not_redownloaded(tmp_path):
    store = Store(str(tmp_path / "m.db"))
    store.imdb_replace([("tt0000001", 8.0, 1000)])  # elle yüklenmiş, zaman damgası yok
    assert "imdb" not in due_tasks(store, time.time())


def test_imdb_auto_update_and_retry(tmp_path):
    store = Store(str(tmp_path / "i.db"))
    store.meta_set("last_cleanup", time.time())
    body = _gz("tconst\taverageRating\tnumVotes\ntt0000009\t7.9\t5000\n")
    report = maintenance.run_maintenance(store, CFG, DatasetSession(body))
    assert report["imdb"] == 1
    assert store.imdb_get("tt0000009") == {"rating": 7.9, "votes": 5000}

    # Başarısız indirme: eski veri korunur, bir gün dolmadan tekrar denenmez
    later = time.time() + 31 * 86400
    failing = DatasetSession(status=503)
    report = maintenance.run_maintenance(store, CFG, failing, now=later)
    assert "imdb_error" in report and failing.calls == 1
    assert store.imdb_get("tt0000009") is not None
    store.meta_set("imdb_last_attempt", later)
    report = maintenance.run_maintenance(store, CFG, failing, now=later + 3600)
    assert "imdb" not in report and "imdb_error" not in report
    assert failing.calls == 1


def test_maintenance_runs_after_response(tmp_path):
    app = create_app({
        "TESTING": True, "AUTO_MAINTENANCE": True, "IMDB_AUTO_UPDATE_DAYS": 0,
        "TMDB_API_KEY": "x", "DATABASE_PATH": str(tmp_path / "w.db"),
    }, session=FakeSession())
    store = app.extensions["neizlesem"]["store"]
    store.cache_set("bayat", "eski", ttl=-5)
    client = app.test_client()
    resp = client.get("/nasil-calisir")
    resp.close()
    assert store.meta_get("last_cleanup") is not None
    assert store.cache_get("bayat") is None
    # 10 dakika dolmadan ikinci istek yeni bakım planlamaz
    store.meta_set("last_cleanup", 0)
    client.get("/nasil-calisir").close()
    assert store.meta_get("last_cleanup") == "0"


def test_maintenance_disabled_in_tests_by_default(app):
    assert app.config["AUTO_MAINTENANCE"] is False


def test_cli_bakim(tmp_path):
    app = create_app({"TESTING": True, "IMDB_AUTO_UPDATE_DAYS": 0, "TMDB_API_KEY": "x",
                      "DATABASE_PATH": str(tmp_path / "cli.db")}, session=FakeSession())
    out = app.test_cli_runner().invoke(args=["bakim"]).output
    assert "Zamanı gelen işler: cleanup" in out and "Önbellek:" in out
