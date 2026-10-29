"""Sayfalar ve küçük JSON uçları."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from . import catalog
from .movie import build_detail
from .recommender import SearchParams, Term, genre_terms, resolve_terms, run_search, surprise_pick
from .textutil import lower_tr, ticket_serial, today_tr, year_of
from .tmdb import TMDBClient, TMDBError, TMDBNotConfigured

bp = Blueprint("main", __name__)


def services():
    s = current_app.extensions["neizlesem"]
    return s["store"], s["tmdb"], s["omdb"]


@bp.errorhandler(TMDBNotConfigured)
def _not_configured(_exc):
    return render_template("setup.html"), 503


@bp.errorhandler(TMDBError)
def _tmdb_error(exc):
    return render_template("error.html", title="Film verilerine ulaşamadık", message=str(exc), retry=True), 502


def _tmdb_logo() -> str | None:
    """TMDB'nin resmi logosu static/img klasörüne konduysa onu kullan."""
    static = Path(current_app.static_folder) / "img"
    for name in ("tmdb-logo.svg", "tmdb-logo.png"):
        if (static / name).exists():
            return url_for("static", filename=f"img/{name}")
    return None


@bp.app_context_processor
def _globals():
    store = current_app.extensions["neizlesem"]["store"]
    return {
        "omdb_on": current_app.extensions["neizlesem"]["omdb"].configured,
        "imdb_updated": store.meta_get("imdb_updated"),
        "tmdb_logo": _tmdb_logo(),
        "allow_indexing": current_app.config.get("ALLOW_INDEXING", False),
    }


def _provider_options(tmdb: TMDBClient) -> list[dict]:
    if not tmdb.configured:
        return []
    try:
        providers = tmdb.watch_providers_tr()
    except TMDBError:
        return []

    def prio(p):
        return (p.get("display_priorities") or {}).get("TR", p.get("display_priority", 99))
    providers = sorted(providers, key=prio)
    preferred = [p for p in providers if (p.get("provider_name") or "").lower() in catalog.PREFERRED_PROVIDERS]
    chosen = preferred or providers[:10]
    return [{"id": p["provider_id"], "name": p["provider_name"],
             "logo": TMDBClient.image(p.get("logo_path"), "w92")} for p in chosen[:12]]


@bp.route("/")
def index():
    store, tmdb, _ = services()
    params = SearchParams.from_args(request.args)
    custom = []
    custom_keys = [k for k in params.include + params.exclude if k.startswith("t")]
    if custom_keys and tmdb.configured:
        for term in resolve_terms(custom_keys, tmdb):
            custom.append({"key": term.key, "label": term.label,
                           "state": 1 if term.key in params.include else 2})
    return render_template(
        "index.html",
        params=params,
        groups=catalog.grouped_concepts(),
        popular=[catalog.CONCEPTS[s] for s in catalog.POPULAR],
        concepts=catalog.CONCEPTS,
        genres=catalog.GENRES,
        moods=catalog.MOODS,
        periods=catalog.PERIODS, ratings=catalog.RATINGS, runtimes=catalog.RUNTIMES,
        languages=catalog.LANGUAGES,
        providers=_provider_options(tmdb),
        custom=custom,
        configured=tmdb.configured,
        today_text=today_tr(),
        serial=ticket_serial(),
    )


def _search(params: SearchParams) -> dict:
    store, tmdb, omdb = services()
    cfg = current_app.config
    return run_search(params, tmdb, omdb, store,
                      result_limit=cfg["RESULT_LIMIT"], candidate_limit=cfg["CANDIDATE_LIMIT"],
                      workers=cfg["MAX_WORKERS"])


@bp.route("/sonuclar")
def results():
    params = SearchParams.from_args(request.args)
    data = _search(params)
    return render_template("results.html", params=params, data=data, sorts=catalog.SORTS,
                           genres=catalog.GENRES)


@bp.route("/surpriz")
def surprise():
    params = SearchParams.from_args(request.args)
    pick = surprise_pick(_search(params)["results"])
    if not pick:
        return redirect(url_for("main.results") + "?" + urlencode(params.query_pairs()))
    pairs = [(k, v) for k, v in params.query_pairs() if k in ("k", "g")]
    return redirect(url_for("main.movie", movie_id=pick["id"]) + ("?" + urlencode(pairs) if pairs else ""))


@bp.route("/film/<int:movie_id>")
def movie(movie_id: int):
    store, tmdb, omdb = services()
    params = SearchParams.from_args(request.args)
    selected: list[Term] = []
    if params.include:
        selected += [t for t in resolve_terms(params.include, tmdb) if t.ids]
    selected += genre_terms(params.genres)
    detail = build_detail(movie_id, tmdb, omdb, store, current_app.config["MAX_WORKERS"], selected)
    if not detail:
        abort(404)
    back = url_for("main.results") + "?" + urlencode(params.query_pairs()) if (params.include or params.genres) else None
    return render_template("detail.html", d=detail, back=back, came_from=params.query_pairs())


@bp.route("/ara")
def search():
    _, tmdb, _ = services()
    q = (request.args.get("q") or "").strip()[:80]
    films = []
    if q:
        for r in tmdb.search_movies(q).get("results", [])[:20]:
            films.append({
                "id": r["id"], "title": r.get("title"), "original_title": r.get("original_title"),
                "year": year_of(r.get("release_date")), "poster": TMDBClient.image(r.get("poster_path"), "w185"),
                "tmdb": r.get("vote_average"), "votes": r.get("vote_count"),
            })
        films.sort(key=lambda f: f["votes"] or 0, reverse=True)
    return render_template("search.html", q=q, films=films)


@bp.route("/api/anahtar-kelime")
def keyword_suggest():
    _, tmdb, _ = services()
    q = (request.args.get("q") or "").strip()[:40]
    if len(q) < 2:
        return jsonify([])
    needle = lower_tr(q)
    out = []
    for c in catalog.CONCEPTS.values():
        if needle in lower_tr(c.label) or any(needle in e for e in c.en):
            out.append({"key": c.slug, "label": c.label, "emoji": c.emoji, "source": "katalog"})
    seen = {o["label"].lower() for o in out}
    if tmdb.configured:
        try:
            for r in tmdb.search_keywords(q)[:12]:
                label = catalog.keyword_translation(r["name"]) or r["name"]
                if label.lower() in seen:
                    continue
                seen.add(label.lower())
                out.append({"key": f"t{r['id']}", "label": label, "emoji": "🏷️", "source": "tmdb"})
        except TMDBError:
            pass
    return jsonify(out[:12])


@bp.route("/nasil-calisir")
def about():
    from .scoring import WEIGHTS
    return render_template("about.html", weights=WEIGHTS)


@bp.route("/robots.txt")
def robots():
    if current_app.config.get("ALLOW_INDEXING"):
        body = "User-agent: *\nAllow: /\n"
    else:
        body = "User-agent: *\nDisallow: /\n"
    return current_app.response_class(body, mimetype="text/plain")
