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
    if not app.config.get("TESTING") and app.config["SECRET_KEY"] == Config.DEFAULT_SECRET:
        app.logger.warning("SECRET_KEY varsayılan değerde; .env dosyasında değiştir.")

    store = Store(app.config["DATABASE_PATH"])
    timeout = app.config["HTTP_TIMEOUT"]
    app.extensions["neizlesem"] = {
        "store": store,
        "tmdb": TMDBClient(app.config["TMDB_API_KEY"], store, timeout, session=session),
        "omdb": OMDbClient(app.config["OMDB_API_KEY"], store, timeout, session=session),
    }

    from . import filters, routes, security
    filters.register(app)
    security.register(app)
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
        """API önbelleğini temizler."""
        n = app.extensions["neizlesem"]["store"].cache_clear(expired_only=not hepsi)
        click.echo(f"{n} önbellek kaydı silindi.")
