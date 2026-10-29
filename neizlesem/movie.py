"""Film verisini (TMDB + IMDb + OMDb + yorum analizi) tek yapıda birleştirir."""
from __future__ import annotations

import re

from .catalog import GENRES, keyword_translation
from .db import Store
from .omdb import OMDbClient
from .reviews import analyze_reviews
from .scoring import pusula_score, verdict
from .textutil import clamp_text, date_tr, money_text, runtime_text, votes_text, year_of
from .tmdb import TMDBClient, parallel_map

LANG_NAMES = {
    "en": "İngilizce", "tr": "Türkçe", "ko": "Korece", "ja": "Japonca", "fr": "Fransızca",
    "es": "İspanyolca", "it": "İtalyanca", "de": "Almanca", "hi": "Hintçe", "zh": "Çince",
    "cn": "Kantonca", "ru": "Rusça", "da": "Danca", "sv": "İsveççe", "no": "Norveççe",
    "fa": "Farsça", "pt": "Portekizce", "pl": "Lehçe", "th": "Tayca", "ar": "Arapça",
}
_YT_KEY = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def collect_ratings(tr: dict, store: Store, omdb: OMDbClient | None) -> dict:
    imdb_id = (tr.get("external_ids") or {}).get("imdb_id") or tr.get("imdb_id")
    out = {
        "imdb_id": imdb_id, "imdb": None, "imdb_votes": None, "imdb_source": None,
        "tmdb": tr.get("vote_average"), "tmdb_votes": tr.get("vote_count"),
        "rt": None, "metacritic": None, "awards": None,
    }
    local = store.imdb_get(imdb_id) if imdb_id else None
    if local:
        out.update(imdb=local["rating"], imdb_votes=local["votes"], imdb_source="IMDb veri seti")
    extra = omdb.by_imdb_id(imdb_id) if (omdb and omdb.configured and imdb_id) else None
    if extra:
        if out["imdb"] is None and extra.get("imdb_rating") is not None:
            out.update(imdb=extra["imdb_rating"], imdb_votes=extra.get("imdb_votes"), imdb_source="OMDb")
        out.update(rt=extra.get("rt"), metacritic=extra.get("metacritic"), awards=extra.get("awards"))
    out["imdb_votes_text"] = votes_text(out["imdb_votes"]) if out["imdb_votes"] else None
    out["tmdb_votes_text"] = votes_text(out["tmdb_votes"]) if out["tmdb_votes"] else None
    return out


def compute_pusula(ratings: dict, review_summary: dict | None) -> dict:
    return pusula_score(
        imdb_rating=ratings.get("imdb"), imdb_votes=ratings.get("imdb_votes"),
        tmdb_avg=ratings.get("tmdb"), tmdb_votes=ratings.get("tmdb_votes"),
        rt=ratings.get("rt"), metacritic=ratings.get("metacritic"),
        review_summary=review_summary,
    )


def _genres(tr: dict) -> list[str]:
    if tr.get("genres"):
        return [GENRES.get(g["id"], g.get("name", "")) for g in tr["genres"] if g.get("id") != 10770]
    return [GENRES[g] for g in tr.get("genre_ids", []) if g in GENRES]


def _directors(tr: dict) -> list[dict]:
    crew = (tr.get("credits") or {}).get("crew", [])
    return [{"id": c["id"], "name": c["name"]} for c in crew if c.get("job") == "Director"]


def build_card(tr: dict, en: dict, store: Store, omdb: OMDbClient | None) -> dict:
    """Sonuç listesindeki kart için özet veri."""
    ratings = collect_ratings(tr, store, omdb)
    reviews = analyze_reviews((en.get("reviews") or {}).get("results", []))
    pusula = compute_pusula(ratings, reviews)
    overview = tr.get("overview") or ""
    lang = "tr"
    if not overview:
        overview, lang = en.get("overview") or "", "en"
    return {
        "id": tr["id"],
        "title": tr.get("title") or en.get("title") or tr.get("original_title"),
        "original_title": tr.get("original_title"),
        "year": year_of(tr.get("release_date")),
        "release_date": tr.get("release_date") or "",
        "runtime_text": runtime_text(tr.get("runtime")),
        "genres": _genres(tr),
        "poster": TMDBClient.image(tr.get("poster_path"), "w342"),
        "backdrop": TMDBClient.image(tr.get("backdrop_path"), "w780"),
        "overview": clamp_text(overview, 230),
        "overview_lang": lang,
        "popularity": tr.get("popularity") or 0,
        "directors": [d["name"] for d in _directors(tr)][:2],
        "ratings": ratings,
        "pusula": {"score": pusula["score"], "confidence": pusula["confidence"]},
        "review_count": reviews["count"],
        "pros": [p["label"] for p in reviews["pros"][:3]],
    }


# ---------------------------------------------------------------- detay sayfası

def _certification(tr: dict) -> str | None:
    results = (tr.get("release_dates") or {}).get("results", [])
    by_country = {r.get("iso_3166_1"): r.get("release_dates", []) for r in results}
    for country in ("TR", "US", "GB"):
        for rd in by_country.get(country, []):
            cert = (rd.get("certification") or "").strip()
            if cert:
                return cert if country == "TR" else f"{cert} ({country})"
    return None


def _trailer(tr: dict) -> dict | None:
    videos = [v for v in (tr.get("videos") or {}).get("results", [])
              if v.get("site") == "YouTube" and _YT_KEY.match(v.get("key") or "")]
    if not videos:
        return None

    def rank(v):
        return (
            v.get("type") == "Trailer",
            v.get("iso_639_1") == "tr",
            bool(v.get("official")),
            v.get("size") or 0,
        )
    best = max(videos, key=rank)
    return {"key": best["key"], "name": best.get("name") or "Fragman",
            "turkish": best.get("iso_639_1") == "tr"}


def _providers(tr: dict) -> dict | None:
    data = ((tr.get("watch/providers") or {}).get("results") or {}).get("TR")
    if not data:
        return None

    def items(kind):
        return [{"name": p["provider_name"], "logo": TMDBClient.image(p.get("logo_path"), "w92")}
                for p in sorted(data.get(kind, []), key=lambda p: p.get("display_priority", 99))]
    out = {"link": data.get("link"), "abonelik": items("flatrate") + items("free") + items("ads"),
           "kiralik": items("rent"), "satin": items("buy")}
    return out if (out["abonelik"] or out["kiralik"] or out["satin"]) else None


def _keywords(tr: dict) -> list[dict]:
    words = (tr.get("keywords") or {}).get("keywords", [])
    out = []
    for k in words:
        label = keyword_translation(k["name"])
        out.append({"id": k["id"], "label": label or k["name"], "translated": bool(label)})
    out.sort(key=lambda k: not k["translated"])
    return out[:24]


def build_detail(movie_id: int, tmdb: TMDBClient, omdb: OMDbClient | None, store: Store,
                 workers: int = 6, selected_terms: list | None = None) -> dict | None:
    tr, en = parallel_map(lambda f: f(movie_id), [tmdb.movie_tr, tmdb.movie_en], workers=2)
    tr, en = tr or {}, en or {}
    if not tr.get("id"):
        return None

    ratings = collect_ratings(tr, store, omdb)
    reviews = analyze_reviews((en.get("reviews") or {}).get("results", []))
    pusula = compute_pusula(ratings, reviews)

    credits = tr.get("credits") or {}
    cast_raw = [c for c in credits.get("cast", []) if c.get("name")][:10]

    def known_for(person_id: int) -> list[dict]:
        data = tmdb.person_movie_credits(person_id)
        films = [f for f in data.get("cast", [])
                 if f.get("id") != movie_id and (f.get("vote_count") or 0) >= 300 and f.get("release_date")]
        films.sort(key=lambda f: f.get("vote_count", 0), reverse=True)
        seen, out = set(), []
        for f in films:
            if f["id"] in seen:
                continue
            seen.add(f["id"])
            out.append({"id": f["id"], "title": f.get("title"), "year": year_of(f.get("release_date"))})
            if len(out) == 3:
                break
        return out

    lead_ids = [c["id"] for c in cast_raw[:4]]
    known = dict(zip(lead_ids, parallel_map(known_for, lead_ids, workers)))
    cast = [{
        "id": c["id"], "name": c["name"], "character": c.get("character") or "",
        "photo": TMDBClient.image(c.get("profile_path"), "w185"),
        "known_for": known.get(c["id"]) or [],
    } for c in cast_raw]

    crew = credits.get("crew", [])

    def people(jobs: tuple[str, ...], limit: int = 3) -> list[str]:
        names = []
        for c in crew:
            if c.get("job") in jobs and c["name"] not in names:
                names.append(c["name"])
        return names[:limit]

    overview = tr.get("overview") or ""
    overview_lang = "tr"
    if not overview:
        overview, overview_lang = en.get("overview") or "", "en"

    recs = [{
        "id": r["id"], "title": r.get("title"), "year": year_of(r.get("release_date")),
        "poster": TMDBClient.image(r.get("poster_path"), "w185"),
        "tmdb": r.get("vote_average"),
    } for r in (tr.get("recommendations") or {}).get("results", [])[:12] if r.get("poster_path")][:8]

    movie_kw_ids = {k["id"] for k in (tr.get("keywords") or {}).get("keywords", [])}
    movie_genre_ids = {g["id"] for g in tr.get("genres", [])}
    matched, missed = [], []
    for term in selected_terms or []:
        hit = bool(set(term.ids) & movie_kw_ids) if term.kind != "genre" else bool(set(term.ids) & movie_genre_ids)
        (matched if hit else missed).append(term.label)

    detail = {
        "id": tr["id"],
        "title": tr.get("title") or en.get("title"),
        "original_title": tr.get("original_title"),
        "tagline": tr.get("tagline") or en.get("tagline") or "",
        "overview": overview,
        "overview_lang": overview_lang,
        "year": year_of(tr.get("release_date")),
        "release_date_text": date_tr(tr.get("release_date")),
        "runtime_text": runtime_text(tr.get("runtime")),
        "genres": _genres(tr),
        "language": LANG_NAMES.get(tr.get("original_language"), (tr.get("original_language") or "").upper()),
        "original_language": tr.get("original_language"),
        "certification": _certification(tr),
        "poster": TMDBClient.image(tr.get("poster_path"), "w500"),
        "backdrop": TMDBClient.image(tr.get("backdrop_path"), "w1280"),
        "budget_text": money_text(tr.get("budget")),
        "revenue_text": money_text(tr.get("revenue")),
        "countries": [c.get("name") for c in tr.get("production_countries", [])][:3],
        "ratings": ratings,
        "pusula": pusula,
        "verdict": verdict(pusula["score"]),
        "reviews": reviews,
        "cast": cast,
        "directors": people(("Director",)),
        "writers": people(("Screenplay", "Writer", "Story", "Novel", "Author")),
        "composer": people(("Original Music Composer", "Music"), 2),
        "dop": people(("Director of Photography",), 1),
        "trailer": _trailer(tr),
        "providers": _providers(tr),
        "keywords": _keywords(tr),
        "recommendations": recs,
        "matched": matched,
        "missed": missed,
        "imdb_url": f"https://www.imdb.com/title/{ratings['imdb_id']}/" if ratings.get("imdb_id") else None,
        "tmdb_url": f"https://www.themoviedb.org/movie/{tr['id']}",
    }
    from .narrative import build_story  # döngüsel içe aktarmayı önlemek için burada
    detail["story"] = build_story(detail)
    return detail
