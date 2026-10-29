"""Öneri motoru: seçilen temalara/türlere göre en uygun filmleri bulur ve sıralar.

Akış
1. Türkçe temalar → TMDB anahtar kelime kimlikleri (eş anlamlılarla).
2. TMDB "discover" ile aday toplama:
   - hepsini birden içerenler (VE sorgusu),
   - herhangi birini içerenler (VEYA sorgusu, popülerlik + en yüksek puan),
   - her tema için ayrı en iyiler.
3. Adayların gerçek anahtar kelimeleri çekilir → kaç temayı tuttuğu hesaplanır (uygunluk %).
   "Olmasın" denen temaları/türleri içerenler elenir.
4. En iyi adaylar zenginleştirilir: IMDb puanı, Rotten Tomatoes/Metacritic, yorum analizi.
5. Sıralama = %60 uygunluk + %40 Pusula Puanı (veya kullanıcının seçtiği ölçüt).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date

from .catalog import CONCEPTS, GENRES, LANGUAGES, PERIODS, RATINGS, RUNTIMES, SORTS, keyword_translation
from .db import Store
from .movie import build_card
from .omdb import OMDbClient
from .scoring import quick_score
from .tmdb import HOUR, TMDBClient, parallel_map

_CUSTOM_KEY = re.compile(r"^t\d{1,9}$")
CACHE_VERSION = "v1"


@dataclass
class Term:
    key: str
    label: str
    emoji: str
    ids: list[int] = field(default_factory=list)
    kind: str = "concept"  # concept | custom | genre

    def as_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "emoji": self.emoji, "ids": self.ids, "kind": self.kind}

    @classmethod
    def from_dict(cls, d: dict) -> "Term":
        return cls(**d)


@dataclass
class SearchParams:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    genres: list[int] = field(default_factory=list)
    exclude_genres: list[int] = field(default_factory=list)
    period: str = ""
    min_rating: str = ""
    max_runtime: str = ""
    language: str = ""
    providers: list[int] = field(default_factory=list)
    hidden_gems: bool = False
    sort: str = "uygun"

    @classmethod
    def from_args(cls, args) -> "SearchParams":
        def many(name: str) -> list[str]:
            out = []
            for raw in args.getlist(name):
                for part in str(raw).split(","):
                    part = part.strip()
                    if part and part not in out:
                        out.append(part)
            return out

        def valid_key(k: str) -> bool:
            return k in CONCEPTS or bool(_CUSTOM_KEY.match(k))

        def ints(name: str, allowed=None) -> list[int]:
            out = []
            for v in many(name):
                if v.isdigit() and (allowed is None or int(v) in allowed) and int(v) not in out:
                    out.append(int(v))
            return out

        include = [k for k in many("k") if valid_key(k)][:8]
        exclude = [k for k in many("x") if valid_key(k) and k not in include][:8]
        genres = ints("g", GENRES)[:5]
        xgenres = [g for g in ints("xg", GENRES) if g not in genres][:5]

        def choice(name: str, options) -> str:
            v = (args.get(name) or "").strip()
            return v if v in {o[0] for o in options} else ""

        sort = (args.get("sirala") or "uygun").strip()
        return cls(
            include=include, exclude=exclude, genres=genres, exclude_genres=xgenres,
            period=choice("donem", PERIODS), min_rating=choice("puan", RATINGS),
            max_runtime=choice("sure", RUNTIMES), language=choice("dil", LANGUAGES),
            providers=ints("p")[:6], hidden_gems=args.get("cevher") == "1",
            sort=sort if sort in {s[0] for s in SORTS} else "uygun",
        )

    def query_pairs(self, drop: tuple[str, str] | None = None, **override) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for k in self.include:
            pairs.append(("k", k))
        for k in self.exclude:
            pairs.append(("x", k))
        for g in self.genres:
            pairs.append(("g", str(g)))
        for g in self.exclude_genres:
            pairs.append(("xg", str(g)))
        for p in self.providers:
            pairs.append(("p", str(p)))
        simple = {"donem": self.period, "puan": self.min_rating, "sure": self.max_runtime,
                  "dil": self.language, "cevher": "1" if self.hidden_gems else "", "sirala": self.sort}
        simple.update(override)
        for k, v in simple.items():
            if v:
                pairs.append((k, v))
        if drop:
            pairs = [p for p in pairs if p != drop]
        return pairs

    def cache_key(self) -> str:
        data = {k: v for k, v in self.__dict__.items() if k != "sort"}
        raw = json.dumps(data, sort_keys=True)
        return f"search:{CACHE_VERSION}:" + hashlib.sha1(raw.encode()).hexdigest()

    @property
    def is_empty(self) -> bool:
        return not (self.include or self.genres)


# ----------------------------------------------------------------- terimler

def resolve_terms(keys: list[str], tmdb: TMDBClient, workers: int = 8) -> list[Term]:
    def resolve(key: str) -> Term:
        if key in CONCEPTS:
            c = CONCEPTS[key]
            ids: list[int] = []
            for kid in parallel_map(tmdb.resolve_keyword, c.en, workers=len(c.en)):
                if kid and kid not in ids:
                    ids.append(kid)
            return Term(key, c.label, c.emoji, ids, "concept")
        kid = int(key[1:])
        data = tmdb.keyword(kid)
        name = data.get("name") or f"#{kid}"
        return Term(key, keyword_translation(name) or name, "🏷️", [kid] if data else [], "custom")

    resolved = parallel_map(resolve, keys, workers)
    out = []
    for key, term in zip(keys, resolved):
        if term is None:
            label = CONCEPTS[key].label if key in CONCEPTS else key
            term = Term(key, label, "❔", [], "concept")
        out.append(term)
    return out


def genre_terms(genre_ids: list[int]) -> list[Term]:
    return [Term(f"g{g}", GENRES[g], "🎬", [g], "genre") for g in genre_ids if g in GENRES]


# ----------------------------------------------------------------- sorgular

def _period_dates(period: str) -> tuple[str | None, str | None]:
    if not period:
        return None, None
    if period == "son10":
        return f"{date.today().year - 10}-01-01", None
    start, _, end = period.partition("-")
    return (f"{start}-01-01" if start else None, f"{end}-12-31" if end else None)


def base_params(p: SearchParams, exclude_ids: list[int], has_terms: bool) -> dict:
    params: dict = {
        "sort_by": "popularity.desc",
        "vote_count.gte": 30 if p.hidden_gems else (150 if has_terms else 400),
        "with_runtime.gte": 60,  # kısa filmleri dışarıda bırak
    }
    if p.genres:
        params["with_genres"] = "|".join(map(str, p.genres))
    if p.exclude_genres:
        params["without_genres"] = ",".join(map(str, p.exclude_genres))
    if exclude_ids:
        params["without_keywords"] = "|".join(map(str, exclude_ids))  # "|" = herhangi birini içeren elensin
    gte, lte = _period_dates(p.period)
    if gte:
        params["primary_release_date.gte"] = gte
    if lte:
        params["primary_release_date.lte"] = lte
    if p.min_rating:
        params["vote_average.gte"] = max(0.0, float(p.min_rating) - 0.6)  # TMDB, IMDb'den biraz düşük puanlar
    if p.max_runtime:
        params["with_runtime.lte"] = int(p.max_runtime)
    if p.language:
        params["with_original_language"] = p.language
    if p.providers:
        params["watch_region"] = "TR"
        params["with_watch_providers"] = "|".join(map(str, p.providers))
        params["with_watch_monetization_types"] = "flatrate|free|ads"
    return params


def plan_queries(p: SearchParams, base: dict, terms: list[Term]) -> list[tuple[str, dict, int]]:
    q: list[tuple[str, dict, int]] = []
    min_votes = base["vote_count.gte"]
    if terms:
        all_kw = "|".join(str(i) for t in terms for i in t.ids)
        if len(terms) > 1:
            and_kw = ",".join(str(t.ids[0]) for t in terms)
            q += [("and", {**base, "with_keywords": and_kw}, pg) for pg in (1, 2)]
        q += [("or", {**base, "with_keywords": all_kw}, pg) for pg in (1, 2, 3)]
        q.append(("or-top", {**base, "with_keywords": all_kw, "sort_by": "vote_average.desc",
                             "vote_count.gte": max(min_votes, 800)}, 1))
        if len(terms) > 1:
            for t in terms:
                q.append((f"term:{t.key}", {**base, "with_keywords": "|".join(map(str, t.ids))}, 1))
        if p.hidden_gems:
            q += [("gems", {**base, "with_keywords": all_kw, "sort_by": "vote_average.desc",
                            "vote_count.gte": 80, "vote_count.lte": 2500}, pg) for pg in (1, 2)]
    else:
        q += [("pop", base, pg) for pg in (1, 2, 3)]
        q += [("top", {**base, "sort_by": "vote_average.desc", "vote_count.gte": max(min_votes, 1500)}, pg)
              for pg in (1, 2)]
        if p.hidden_gems:
            q += [("gems", {**base, "sort_by": "vote_average.desc", "vote_count.gte": 80,
                            "vote_count.lte": 2500}, pg) for pg in (1, 2)]
    return q


# ----------------------------------------------------------------- eşleşme

def compute_match(kw_ids: set[int] | None, genre_ids: set[int], terms: list[Term], genres: list[Term],
                  known_terms: set[str]) -> dict:
    matched, missed = [], []
    for t in terms:
        hit = bool(set(t.ids) & kw_ids) if kw_ids is not None else (t.key in known_terms)
        (matched if hit else missed).append(t.label)
    g_matched = [g.label for g in genres if g.ids[0] in genre_ids]
    g_missed = [g.label for g in genres if g.ids[0] not in genre_ids]
    total = len(terms) + 0.5 * len(genres)
    ratio = (len(matched) + 0.5 * len(g_matched)) / total if total else 1.0
    return {
        "ratio": round(ratio, 3),
        "pct": round(100 * ratio) if total else None,
        "matched": matched + g_matched,
        "missed": missed + g_missed,
        "terms_hit": len(matched),
        "terms_total": len(terms),
    }


def rank_value(match_ratio: float, score: float | None) -> float:
    return 0.6 * match_ratio + 0.4 * ((score if score is not None else 5.5) / 10)


SORT_KEYS = {
    "uygun": lambda c: c["rank"],
    "puan": lambda c: c["pusula"]["score"] or 0,
    "imdb": lambda c: (c["ratings"]["imdb"] or 0, c["pusula"]["score"] or 0),
    "yeni": lambda c: c["release_date"] or "",
    "populer": lambda c: c["popularity"] or 0,
}


def sort_results(results: list[dict], sort: str) -> list[dict]:
    return sorted(results, key=SORT_KEYS.get(sort, SORT_KEYS["uygun"]), reverse=True)


# ----------------------------------------------------------------- ana akış

def run_search(p: SearchParams, tmdb: TMDBClient, omdb: OMDbClient | None, store: Store,
               result_limit: int = 20, candidate_limit: int = 60, workers: int = 8) -> dict:
    cache_key = p.cache_key()
    cached = store.cache_get(cache_key)
    if cached is not None:
        cached["results"] = sort_results(cached["results"], p.sort)
        return cached

    terms = resolve_terms(p.include, tmdb, workers)
    unresolved = [t.label for t in terms if not t.ids]
    terms = [t for t in terms if t.ids]
    ex_terms = resolve_terms(p.exclude, tmdb, workers)
    exclude_ids = sorted({i for t in ex_terms for i in t.ids})
    g_terms = genre_terms(p.genres)

    base = base_params(p, exclude_ids, bool(terms))
    queries = plan_queries(p, base, terms)
    pages = parallel_map(lambda q: tmdb.discover(q[1], q[2]), queries, workers)

    candidates: dict[int, dict] = {}
    for (tag, _, _), data in zip(queries, pages):
        for s in (data or {}).get("results", []):
            if not s.get("id"):
                continue
            c = candidates.setdefault(s["id"], {"summary": s, "tags": set()})
            c["tags"].add(tag)

    def known_terms(tags: set[str]) -> set[str]:
        if "and" in tags:
            return {t.key for t in terms}
        if len(terms) == 1 and tags & {"or", "or-top", "gems"}:
            return {terms[0].key}
        return {tag.split(":", 1)[1] for tag in tags if tag.startswith("term:")}

    # Ön eleme: bildiğimiz eşleşme + TMDB puanı
    for c in candidates.values():
        c["known"] = known_terms(c["tags"])
        s = c["summary"]
        ratio = len(c["known"]) / len(terms) if terms else 1.0
        c["pre"] = rank_value(ratio, quick_score(s.get("vote_average"), s.get("vote_count")))
    shortlist = sorted(candidates.values(), key=lambda c: c["pre"], reverse=True)[:candidate_limit]

    # Gerçek anahtar kelimelerle kesin eşleşme
    need_keywords = bool(terms or exclude_ids)
    kw_sets = parallel_map(tmdb.movie_keyword_ids, [c["summary"]["id"] for c in shortlist], workers) \
        if need_keywords else [None] * len(shortlist)

    scored = []
    exclude_set = set(exclude_ids)
    for c, kw in zip(shortlist, kw_sets):
        s = c["summary"]
        genre_ids = set(s.get("genre_ids", []))
        if kw is not None and kw & exclude_set:
            continue
        if genre_ids & set(p.exclude_genres):
            continue
        match = compute_match(kw, genre_ids, terms, g_terms, c["known"])
        if terms and match["terms_hit"] == 0:
            continue
        c["match"] = match
        c["rank0"] = rank_value(match["ratio"], quick_score(s.get("vote_average"), s.get("vote_count")))
        scored.append(c)
    scored.sort(key=lambda c: c["rank0"], reverse=True)
    to_enrich = scored[: result_limit + 8]

    def enrich(c: dict) -> dict | None:
        mid = c["summary"]["id"]
        tr = tmdb.movie_tr(mid)
        if not tr.get("id"):
            return None
        en = tmdb.movie_en(mid)
        card = build_card(tr, en, store, omdb)
        card["match"] = c["match"]
        card["rank"] = round(rank_value(c["match"]["ratio"], card["pusula"]["score"]), 4)
        return card

    cards = [card for card in parallel_map(enrich, to_enrich, workers) if card]

    if p.min_rating:
        floor = float(p.min_rating)
        cards = [c for c in cards
                 if (c["ratings"]["imdb"] if c["ratings"]["imdb"] is not None else (c["ratings"]["tmdb"] or 0)) >= floor]

    cards = sort_results(cards, "uygun")[:result_limit]
    result = {
        "results": cards,
        "terms": [t.as_dict() for t in terms],
        "excluded": [t.as_dict() for t in ex_terms],
        "genre_terms": [t.as_dict() for t in g_terms],
        "unresolved": unresolved,
        "candidate_count": len(candidates),
    }
    store.cache_set(cache_key, result, 6 * HOUR)
    result["results"] = sort_results(cards, p.sort)
    return result


def surprise_pick(results: list[dict], top: int = 8) -> dict | None:
    pool = sorted(results, key=lambda c: c["rank"], reverse=True)[:top]
    return random.choice(pool) if pool else None
