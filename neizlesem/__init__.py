"""Ne İzlesem? — temaya göre film bulma uygulaması."""
from __future__ import annotations

import click
from flask import Flask

from .config import Config
from .db import Store
from .omdb import OMDbClient
from .tmdb import TMDBClient


def create_app(config: dict | None = None, session=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    if app.config.get("TESTING") and "AUTO_MAINTENANCE" not in (config or {}):
        app.config["AUTO_MAINTENANCE"] = False  # testlerde ağ indirmesi olmasın
    if not app.config.get("TESTING") and app.config["SECRET_KEY"] == Config.DEFAULT_SECRET:
        app.logger.warning("SECRET_KEY varsayılan değerde; .env dosyasında değiştir.")

    store = Store(app.config["DATABASE_PATH"])
    timeout = app.config["HTTP_TIMEOUT"]
    app.extensions["neizlesem"] = {
        "store": store,
        "tmdb": TMDBClient(app.config["TMDB_API_KEY"], store, timeout, session=session),
        "omdb": OMDbClient(app.config["OMDB_API_KEY"], store, timeout, session=session),
    }

    from . import filters, maintenance, routes, security
    filters.register(app)
    security.register(app)
    maintenance.register(app)
    app.register_blueprint(routes.bp)
    _register_cli(app)
    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("imdb-guncelle")
    @click.option("--dosya", type=click.Path(exists=True), help="Elle indirdiğin title.ratings.tsv.gz dosyası")
    @click.option("--min-oy", default=100, show_default=True, help="Bundan az oylu yapımlar alınmaz")
    def imdb_update(dosya, min_oy):
        """IMDb resmi puan veri setini indirip yerel veritabanına aktarır."""
        from .imdb_dataset import download_and_import, import_file
        store = app.extensions["neizlesem"]["store"]
        click.echo("IMDb puanları aktarılıyor (bir iki dakika sürebilir)...")
        try:
            count = import_file(store, dosya, min_oy) if dosya else download_and_import(store, min_oy)
        except Exception as exc:  # ağ hatası, bozuk dosya...
            raise click.ClickException(f"IMDb verisi aktarılamadı: {exc}") from exc
        click.echo(f"Tamam: {count:,} yapımın IMDb puanı kaydedildi.".replace(",", "."))

    @app.cli.command("temalari-esle")
    def resolve_concepts():
        """Türkçe temaları TMDB anahtar kelimelerine eşler ve sonucu raporlar."""
        from .catalog import CONCEPTS
        from .tmdb import TMDBError
        tmdb = app.extensions["neizlesem"]["tmdb"]
        missing = []
        for c in CONCEPTS.values():
            found = []
            for name in c.en:
                try:
                    kid = tmdb.resolve_keyword(name)
                except TMDBError as exc:
                    raise click.ClickException(str(exc)) from exc
                found.append(f"{name}={kid}" if kid else f"{name}=YOK")
            ok = any(not f.endswith("=YOK") for f in found)
            click.echo(f"{'✓' if ok else '✗'} {c.label:<24} {', '.join(found)}")
            if not ok:
                missing.append(c.label)
        click.echo("\nTüm temalar eşleşti." if not missing else f"\nEşleşmeyen temalar: {', '.join(missing)}")

    @app.cli.command("onbellek-temizle")
    @click.option("--hepsi", is_flag=True, help="Süresi dolmamış kayıtları da sil")
    def clear_cache(hepsi):
        """API önbelleğini temizler (normalde site bunu kendisi yapar)."""
        store = app.extensions["neizlesem"]["store"]
        if hepsi:
            n = store.cache_clear(expired_only=False)
            click.echo(f"{n} önbellek kaydı silindi.")
        else:
            stats = store.cleanup(app.config["CACHE_MAX_MB"] * 1024 * 1024)
            click.echo(f"Süresi dolan {stats['expired']}, budanan {stats['trimmed']} kayıt silindi.")
        click.echo(f"Veritabanı boyutu: {store.file_bytes() / 1_048_576:.1f} MB")

    @app.cli.command("bakim")
    def maintenance_now():
        """Zamanı gelen bakım işlerini şimdi yapar ve durumu gösterir."""
        import time as _time
        from .maintenance import due_tasks, run_maintenance
        store = app.extensions["neizlesem"]["store"]
        cfg = {k: app.config[k] for k in ("CACHE_MAX_MB", "CLEANUP_INTERVAL_HOURS", "IMDB_AUTO_UPDATE_DAYS")}
        tasks = due_tasks(store, cfg)
        click.echo("Zamanı gelen işler: " + (", ".join(tasks) if tasks else "yok"))
        if tasks:
            click.echo(str(run_maintenance(store, cfg, app.extensions["neizlesem"]["tmdb"].session)))
        last = float(store.meta_get("last_cleanup", 0) or 0)
        click.echo(f"Son temizlik: {_time.strftime('%Y-%m-%d %H:%M', _time.localtime(last)) if last else 'henüz yok'}")
        click.echo(f"IMDb puanları: {store.meta_get('imdb_updated', 'henüz yok')} ({store.imdb_count():,} yapım)".replace(",", "."))
        click.echo(f"Önbellek: {store.cache_bytes() / 1_048_576:.1f} MB, veritabanı dosyası: {store.file_bytes() / 1_048_576:.1f} MB")
