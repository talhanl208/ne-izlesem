"""Kendi kendine bakım: elle uğraşmadan önbelleği küçük, IMDb puanlarını güncel tutar.

PythonAnywhere'in yeni ücretsiz hesaplarında zamanlanmış görev olmadığı için bakım,
siteye gelen bir isteğin yanıtı ziyaretçiye ulaştıktan SONRA, arada bir çalışır.
Yani kimse beklemez; en fazla 10 dakikada bir "zamanı geldi mi?" diye bakılır.

* Önbellek: her CLEANUP_INTERVAL_HOURS saatte bir süresi dolanlar silinir,
  toplam boyut CACHE_MAX_MB'ı aşarsa en eskiler budanır, boşalan yer diske döner.
* IMDb puanları: IMDB_AUTO_UPDATE_DAYS günde bir resmi veri setinden yenilenir.
  İndirme başarısız olursa eski puanlar korunur ve ertesi gün tekrar denenir.
"""
from __future__ import annotations

import logging
import threading
import time

from flask import Flask

from .db import Store
from .imdb_dataset import download_and_import

log = logging.getLogger("neizlesem.bakim")
CHECK_EVERY = 600          # saniye: en sık bu aralıkla kontrol edilir
IMDB_RETRY_AFTER = 86400   # başarısız IMDb güncellemesi bir gün sonra yeniden denenir
_lock = threading.Lock()


def due_tasks(store: Store, cfg: dict, now: float | None = None) -> list[str]:
    now = now or time.time()
    tasks = []

    last_cleanup = float(store.meta_get("last_cleanup", 0) or 0)
    if now - last_cleanup >= cfg["CLEANUP_INTERVAL_HOURS"] * 3600:
        tasks.append("cleanup")

    days = cfg["IMDB_AUTO_UPDATE_DAYS"]
    if days > 0:
        updated = store.meta_get("imdb_updated_ts")
        if updated is None and store.imdb_count() > 0:
            # Elle güncellenmiş eski kurulum: zamanını bugünden başlat
            store.meta_set("imdb_updated_ts", now)
            updated = now
        updated = float(updated or 0)
        attempt = float(store.meta_get("imdb_last_attempt", 0) or 0)
        if now - updated >= days * 86400 and now - attempt >= IMDB_RETRY_AFTER:
            tasks.append("imdb")
    return tasks


def run_maintenance(store: Store, cfg: dict, session=None, now: float | None = None) -> dict:
    """Zamanı gelen bakım işlerini yapar. Aynı anda ikinci kez çalışmaz."""
    if not _lock.acquire(blocking=False):
        return {}
    report: dict = {}
    try:
        for task in due_tasks(store, cfg, now):
            if task == "cleanup":
                report["cleanup"] = store.cleanup(cfg["CACHE_MAX_MB"] * 1024 * 1024)
                store.meta_set("last_cleanup", time.time())
                log.info("Önbellek temizlendi: %s", report["cleanup"])
            elif task == "imdb":
                store.meta_set("imdb_last_attempt", time.time())
                try:
                    report["imdb"] = download_and_import(store, session=session)
                    log.info("IMDb puanları güncellendi: %s yapım", report["imdb"])
                except Exception as exc:  # ağ hatası vb.: eski veri yerinde kalır
                    report["imdb_error"] = str(exc)
                    log.warning("IMDb güncellemesi başarısız, yarın tekrar denenecek: %s", exc)
    except Exception as exc:  # bakım hiçbir koşulda siteyi düşürmemeli
        report["error"] = str(exc)
        log.exception("Bakım sırasında hata")
    finally:
        _lock.release()
    return report


def register(app: Flask) -> None:
    if not app.config.get("AUTO_MAINTENANCE"):
        return
    store: Store = app.extensions["neizlesem"]["store"]
    session = app.extensions["neizlesem"]["tmdb"].session
    cfg = {k: app.config[k] for k in ("CACHE_MAX_MB", "CLEANUP_INTERVAL_HOURS", "IMDB_AUTO_UPDATE_DAYS")}
    state = {"next_check": 0.0}

    @app.after_request
    def _schedule(resp):
        now = time.monotonic()
        if now >= state["next_check"]:
            state["next_check"] = now + CHECK_EVERY
            # Yanıt ziyaretçiye gönderildikten sonra çalışır; kimse beklemez.
            resp.call_on_close(lambda: run_maintenance(store, cfg, session))
        return resp
