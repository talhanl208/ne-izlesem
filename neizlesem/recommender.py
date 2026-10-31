"""Öneri motoru: seçilen temalara/türlere göre en uygun filmleri bulur, sıralar ve sayfalar.

Akış
1. Türkçe temalar → TMDB anahtar kelime kimlikleri (eş anlamlılarla).
2. Geniş aday havuzu: hepsini içerenler (VE), herhangi birini içerenler (VEYA) farklı
   sıralamalarla (popülerlik, oy sayısı, puan), dönemlere bölünmüş taramalar ve her tema
   için ayrı taramalar. Havuz küçükse oy eşiği kademeli düşürülür (niş aramalar).
3. Her adayın gerçek etiketleri çekilir ve ilgi puanı hesaplanır:
   - kapsama: seçilen temaların kaçı var; nadir temalar daha ağır basar (IDF),
   - merkezilik: tema, filmin az sayıdaki etiketinden biriyse hikâyenin merkezindedir;
     50 etiketli bir gişe filminde tesadüfen geçiyorsa değildir (BM25 uzunluk normalizasyonu),
   - konu metni: tema Türkçe özette de geçiyorsa küçük bir bonus.
4. Sıralama = ilgi + kalite (Bayes düzeltmeli puan) ± tanınırlık (öneri tarzına göre),
   ardından MMR ile çeşitlendirme: birbirine çok benzeyen filmler (aynı seri, aynı etiketler)
   art arda gelmez. "Karıştır" küçük bir rastgelelik ekler.
5. Sayfa sayfa zenginleştirme: IMDb puanı, eleştirmen puanları, yorum analizi.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass, field
from datetime import date

from .catalog import (CONCEPTS, GENRES, LANGUAGES, MODES, PERIODS, RATINGS, RUNTIMES, SORTS,
                      STORY_STEMS, keyword_translation)
from .db import Store
from .movie import build_card
from .omdb import OMDbClient
from .scoring import quick_score
from .textutil import lower_tr
from .tmdb import HOUR, TMDBClient, parallel_map

_CUSTOM_KEY = re.compile(r"^t\d{1,9}$")
CACHE_VERSION = "v4"
MODE_KEYS = {m[0] for m in MODES}


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
    mode: str = "dengeli"   # populer | dengeli | kesif
    sort: str = "uygun"
    seed: int = 0           # "Karıştır": 0 = karıştırma yok

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
        mode = (args.get("tarz") or "").strip()
        if mode not in MODE_KEYS:
            mode = "kesif" if args.get("cevher") == "1" else "dengeli"  # eski bağlantılar
        seed_raw = (args.get("karistir") or "").strip()
        seed = int(seed_raw) % 1_000_000 if seed_raw.isdigit() else 0
        return cls(
            include=include, exclude=exclude, genres=genres, exclude_genres=xgenres,
            period=choice("donem", PERIODS), min_rating=choice("puan", RATINGS),
            max_runtime=choice("sure", RUNTIMES), language=choice("dil", LANGUAGES),
            providers=ints("p")[:6], mode=mode,
            sort=sort if sort in {s[0] for s in SORTS} else "uygun", seed=seed,
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
                  "dil": self.language, "tarz": "" if self.mode == "dengeli" else self.mode,
                  "sirala": "" if self.sort == "uygun" else self.sort,
                  "karistir": str(self.seed) if self.seed else ""}
        simple.update(override)
        for k, v in simple.items():
            if v:
                pairs.append((k, v))
        if drop:
            pairs = [p for p in pairs if p != drop]
        return pairs

    def query_without(self, *names: str) -> list[tuple[str, str]]:
        """Belirtilen filtre(ler) olmadan aynı arama (ör. 'puan', 'p', 'x')."""
        return [(k, v) for k, v in self.query_pairs() if k not in names]

    def cache_key(self) -> str:
        """Aday havuzunun anahtarı: sıralama ve karıştırma havuzu değiştirmez."""
        data = {k: v for k, v in self.__dict__.items() if k not in ("sort", "seed")}
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

# Tarz → ilk turdaki en az oy sayısı (temalı, temasız)
FIRST_TIER_VOTES = {"populer": (300, 800), "dengeli": (150, 400), "kesif": (40, 100)}


def _period_dates(period: str) -> tuple[str | None, str | None]:
    if not period:
        return None, None
    if period == "son10":
        return f"{date.today().year - 10}-01-01", None
    start, _, end = period.partition("-")
    return (f"{start}-01-01" if start else None, f"{end}-12-31" if end else None)


def default_min_votes(p: SearchParams, has_terms: bool) -> int:
    with_terms, without = FIRST_TIER_VOTES.get(p.mode, FIRST_TIER_VOTES["dengeli"])
    return with_terms if has_terms else without


def base_params(p: SearchParams, exclude_ids: list[int], has_terms: bool,
                min_votes: int | None = None, skip_shorts: bool = True) -> dict:
    params: dict = {
        "sort_by": "popularity.desc",
        "vote_count.gte": default_min_votes(p, has_terms) if min_votes is None else min_votes,
    }
    if skip_shorts:
        # Kısa filmleri dışarıda bırak. Not: TMDB'de süresi girilmemiş filmleri de eler,
        # bu yüzden son (gevşetilmiş) turda kapatılıyor ve kısa filmler sonradan ayıklanıyor.
        params["with_runtime.gte"] = 60
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
        # Geniş pay: TMDB puanı IMDb'den belirgin düşük olabiliyor; kesin eleme IMDb puanıyla yapılır.
        params["vote_average.gte"] = max(0.0, float(p.min_rating) - 1.0)
    if p.max_runtime:
        params["with_runtime.lte"] = int(p.max_runtime)
    if p.language:
        params["with_original_language"] = p.language
    if p.providers:
        params["watch_region"] = "TR"
        params["with_watch_providers"] = "|".join(map(str, p.providers))
        params["with_watch_monetization_types"] = "flatrate|free|ads"
    return params


def _eras(p: SearchParams) -> list[dict]:
    """Dönem filtresi yoksa farklı dönemlerden de aday topla (hep yeni gişe filmleri gelmesin)."""
    if p.period:
        return []
    return [
        {"primary_release_date.lte": "1999-12-31"},
        {"primary_release_date.gte": "2000-01-01", "primary_release_date.lte": "2012-12-31"},
    ]


def plan_queries(p: SearchParams, base: dict, terms: list[Term], tier: int = 0) -> list[tuple[str, dict, int]]:
    """(etiket, parametreler, sayfa) listesi. Etiket, adayın hangi temaları kesin taşıdığını söyler."""
    q: list[tuple[str, dict, int]] = []
    mv = base["vote_count.gte"]
    top = {"sort_by": "vote_average.desc", "vote_count.gte": max(mv, 300)}
    gems = {"sort_by": "vote_average.desc", "vote_count.gte": max(min(mv, 60), 5), "vote_count.lte": 3000}

    if terms:
        all_kw = "|".join(str(i) for t in terms for i in t.ids)
        multi = len(terms) > 1
        and_kw = ",".join(str(t.ids[0]) for t in terms)
        if tier == 0:
            if multi:
                q += [("and", {**base, "with_keywords": and_kw}, pg) for pg in (1, 2, 3)]
                q.append(("and-top", {**base, **top, "vote_count.gte": max(mv, 200), "with_keywords": and_kw}, 1))
            q += [("or", {**base, "with_keywords": all_kw}, pg) for pg in (1, 2)]
            q.append(("or-vc", {**base, "with_keywords": all_kw, "sort_by": "vote_count.desc"}, 1))
            q.append(("or-top", {**base, **top, "with_keywords": all_kw}, 1))
            q += [("or-era", {**base, **era, "with_keywords": all_kw}, 1) for era in _eras(p)]
            if multi:
                for t in terms:
                    ids = "|".join(map(str, t.ids))
                    q.append((f"term:{t.key}", {**base, "with_keywords": ids}, 1))
                    q.append((f"term:{t.key}", {**base, **top, "with_keywords": ids}, 1))
            if p.mode == "kesif":
                q += [("or-gem", {**base, **gems, "with_keywords": all_kw}, pg) for pg in (1, 2)]
                if multi:
                    q.append(("and-gem", {**base, **gems, "with_keywords": and_kw}, 1))
        else:
            if multi:
                q.append(("and", {**base, "with_keywords": and_kw}, 1))
                for t in terms:
                    q.append((f"term:{t.key}", {**base, "with_keywords": "|".join(map(str, t.ids))}, 1))
            q += [("or", {**base, "with_keywords": all_kw}, pg) for pg in (1, 2)]
            q.append(("or-top", {**base, **top, "vote_count.gte": mv, "with_keywords": all_kw}, 1))
    else:
        if tier == 0:
            q += [("pop", base, pg) for pg in (1, 2, 3)]
            q += [("top", {**base, **top, "vote_count.gte": max(mv, 1000)}, pg) for pg in (1, 2)]
            q.append(("vc", {**base, "sort_by": "vote_count.desc"}, 1))
            q += [("era", {**base, **era}, 1) for era in _eras(p)]
            if p.mode == "kesif":
                q += [("gem", {**base, **gems}, pg) for pg in (1, 2)]
        else:
            q += [("pop", base, pg) for pg in (1, 2, 3)]
            q.append(("top", {**base, **top, "vote_count.gte": mv}, 1))
    return q


# ----------------------------------------------------------------- ilgi puanı

def compute_match(kw_ids: set[int] | None, genre_ids: set[int], terms: list[Term], genres: list[Term],
                  known_terms: set[str]) -> dict:
    matched, missed, hit_keys = [], [], []
    for t in terms:
        hit = bool(set(t.ids) & kw_ids) if kw_ids is not None else (t.key in known_terms)
        (matched if hit else missed).append(t.label)
        if hit:
            hit_keys.append(t.key)
    g_matched = [g.label for g in genres if g.ids[0] in genre_ids]
    g_missed = [g.label for g in genres if g.ids[0] not in genre_ids]
    total = len(terms) + 0.5 * len(genres)
    ratio = (len(matched) + 0.5 * len(g_matched)) / total if total else 1.0
    return {
        "ratio": round(ratio, 3),
        "pct": round(100 * ratio) if total else None,
        "matched": matched + g_matched,
        "missed": missed + g_missed,
        "hit_keys": hit_keys,
        "terms_hit": len(matched),
        "terms_total": len(terms),
    }


def term_weights(terms: list[Term], df: dict[str, int]) -> dict[str, float]:
    """Nadir temalar daha ağır basar: ağırlık ~ sqrt(IDF), ortalaması 1 olacak şekilde."""
    if len(terms) < 2:
        return {t.key: 1.0 for t in terms}
    known = [v for v in df.values() if v]
    fallback = sorted(known)[len(known) // 2] if known else 100
    n = max(known + [fallback]) * 10
    raw = {t.key: math.sqrt(math.log(1 + n / max(df.get(t.key) or fallback, 1))) for t in terms}
    mean = sum(raw.values()) / len(raw)
    return {k: v / mean for k, v in raw.items()}


def centrality(n_keywords: int, avg_len: float) -> float:
    """BM25 uzunluk normalizasyonu → 0..1. Az etiketli filmde tema daha merkezîdir."""
    if not n_keywords or not avg_len:
        return 0.5
    k1, b = 1.2, 0.75
    norm = (k1 + 1) / (1 + k1 * (1 - b + b * n_keywords / avg_len))
    norm = min(1.35, max(0.45, norm))
    return (norm - 0.45) / 0.9


def story_hits(text: str, hit_keys: list[str]) -> list[str]:
    low = lower_tr(text or "")
    return [k for k in hit_keys if any(stem in low for stem in STORY_STEMS.get(k, ()))]


def relevance(match: dict, weights: dict[str, float], genres: list[Term], central: float, story: list[str]) -> float:
    terms_total = match["terms_total"]
    if not terms_total and not genres:
        return 1.0
    hit = set(match["hit_keys"])
    w_total = sum(weights.values()) + 0.5 * len(genres)
    w_hit = sum(w for k, w in weights.items() if k in hit)
    g_hit = len(match["matched"]) - len(match["hit_keys"])
    coverage = (w_hit + 0.5 * g_hit) / w_total if w_total else 1.0
    if not terms_total:
        return coverage
    story_part = len(story) / len(hit) if hit else 0.0
    return coverage * (0.72 + 0.18 * central + 0.10 * story_part)


def popularity(votes: int | None) -> float:
    return min(1.0, max(0.0, math.log10((votes or 0) + 1) / math.log10(30000)))


def rank_value(rel: float, quality: float | None, pop: float, mode: str = "dengeli") -> float:
    """quality: 0..10 puan. Tarz, tanınırlığın ödül mü ceza mı olduğunu belirler."""
    q = (quality if quality is not None else 5.5) / 10
    if mode == "populer":
        return 0.50 * rel + 0.30 * q + 0.20 * pop
    if mode == "kesif":
        fame = max(0.0, (pop - 0.55) / 0.45)        # ~300+ oydan itibaren artan ceza
        return 0.62 * rel + 0.30 * q - 0.22 * fame
    fame = max(0.0, (pop - 0.75) / 0.25)            # sadece çok bilinen gişe filmlerine hafif ceza
    return 0.60 * rel + 0.40 * q - 0.10 * fame


# ----------------------------------------------------------------- havuz

def _slim(s: dict) -> dict:
    keep = ("id", "title", "original_title", "genre_ids", "vote_average", "vote_count",
            "popularity", "release_date", "original_language", "poster_path", "backdrop_path")
    out = {k: s.get(k) for k in keep}
    out["overview"] = (s.get("overview") or "")[:400]
    return out


def build_pool(p: SearchParams, tmdb: TMDBClient, store: Store, candidate_limit: int = 100,
               workers: int = 8, target: int = 48) -> dict:
    """Aramaya uyan tüm adayları puanlanmış halde döndürür (6 saat önbellekte kalır)."""
    cache_key = p.cache_key()
    cached = store.cache_get(cache_key)
    if cached is not None:
        return cached

    terms = resolve_terms(p.include, tmdb, workers)
    unresolved = [t.label for t in terms if not t.ids]
    terms = [t for t in terms if t.ids]
    ex_terms = resolve_terms(p.exclude, tmdb, workers)
    exclude_ids = sorted({i for t in ex_terms for i in t.ids})
    exclude_set = set(exclude_ids)
    g_terms = genre_terms(p.genres)
    need_keywords = bool(terms or exclude_ids)

    first = default_min_votes(p, bool(terms))
    tiers = [first] + [v for v in (50, 5) if v < first]
    candidates: dict[int, dict] = {}
    kw_sets: dict[int, list | None] = {}
    df: dict[str, int] = {}
    items: list[dict] = []

    def known_terms(tags: set[str]) -> set[str]:
        if any(t.startswith("and") for t in tags):
            return {t.key for t in terms}
        if len(terms) == 1 and any(t.startswith("or") for t in tags):
            return {terms[0].key}
        return {tag.split(":", 1)[1] for tag in tags if tag.startswith("term:")}

    for i, min_votes in enumerate(tiers):
        last = i == len(tiers) - 1 and i > 0
        base = base_params(p, exclude_ids, bool(terms), min_votes=min_votes, skip_shorts=not last)
        queries = plan_queries(p, base, terms, tier=i)
        pages = parallel_map(lambda q: tmdb.discover(q[1], q[2]), queries, workers)
        for (tag, params, page), data in zip(queries, pages):
            data = data or {}
            if i == 0 and tag.startswith("term:") and params.get("sort_by") == "popularity.desc" and page == 1:
                df[tag.split(":", 1)[1]] = data.get("total_results") or 0
            for sm in data.get("results", []):
                if not sm.get("id"):
                    continue
                c = candidates.setdefault(sm["id"], {"s": _slim(sm), "tags": set(), "tier": i})
                c["tags"].add(tag)

        # Ön eleme: bildiğimiz eşleşme + TMDB puanı
        for c in candidates.values():
            c["known"] = known_terms(c["tags"])
            ratio = len(c["known"]) / len(terms) if terms else 1.0
            c["pre"] = 0.6 * ratio + 0.4 * quick_score(c["s"]["vote_average"], c["s"]["vote_count"]) / 10
        shortlist = sorted(candidates.values(), key=lambda c: c["pre"], reverse=True)[:candidate_limit * (i + 1)]

        if need_keywords:
            todo = [c["s"]["id"] for c in shortlist if c["s"]["id"] not in kw_sets]
            for mid, kw in zip(todo, parallel_map(tmdb.movie_keyword_ids, todo, workers)):
                kw_sets[mid] = sorted(kw) if kw is not None else None

        items = []
        for c in shortlist:
            sm = c["s"]
            kw = kw_sets.get(sm["id"]) if need_keywords else None
            kw_set = set(kw) if kw is not None else None
            genre_ids = set(sm.get("genre_ids") or [])
            if kw_set is not None and kw_set & exclude_set:
                continue
            if genre_ids & set(p.exclude_genres):
                continue
            match = compute_match(kw_set, genre_ids, terms, g_terms, c["known"])
            if terms and match["terms_hit"] == 0:
                continue
            items.append({"id": sm["id"], "s": sm, "kw": kw, "match": match, "tier": c["tier"]})

        likely = [it for it in items if not p.min_rating
                  or (it["s"]["vote_average"] or 0) >= float(p.min_rating) - 0.5]
        if len(likely) >= target:
            break

    # İlgi puanı (tüm havuz hazır olduktan sonra: ortalama etiket sayısı ve IDF gerekir)
    weights = term_weights(terms, df)
    lengths = [len(it["kw"]) for it in items if it["kw"]]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    for it in items:
        sm = it["s"]
        central = centrality(len(it["kw"]) if it["kw"] else 0, avg_len)
        story = story_hits(f"{sm.get('title') or ''} {sm.get('overview') or ''}", it["match"]["hit_keys"])
        it["story"] = story
        it["rel"] = round(relevance(it["match"], weights, g_terms, central, story), 4)
        it["q"] = round(quick_score(sm["vote_average"], sm["vote_count"]), 3)
        it["pop"] = round(popularity(sm["vote_count"]), 4)

    pool = {
        "items": items,
        "terms": [t.as_dict() for t in terms],
        "excluded": [t.as_dict() for t in ex_terms],
        "genre_terms": [t.as_dict() for t in g_terms],
        "unresolved": unresolved,
        "candidate_count": len(candidates),
    }
    store.cache_set(cache_key, pool, 6 * HOUR)
    return pool


# ----------------------------------------------------------------- sıralama

def _jaccard(a, b) -> float:
    if not a or not b:
        return 0.0
    a, b = set(a), set(b)
    return len(a & b) / len(a | b)


def similarity(x: dict, y: dict) -> float:
    gx, gy = x["s"].get("genre_ids") or [], y["s"].get("genre_ids") or []
    if x.get("kw") and y.get("kw"):
        return 0.75 * _jaccard(x["kw"], y["kw"]) + 0.25 * _jaccard(gx, gy)
    dx, dy = (x["s"].get("release_date") or "")[:3], (y["s"].get("release_date") or "")[:3]
    return 0.6 * _jaccard(gx, gy) + 0.4 * (1.0 if dx and dx == dy else 0.0)


def _jitter(seed: int, movie_id: int) -> float:
    """Karıştır: Gumbel gürültüsü → iyi filmler yine üstte, ama her seferinde farklı karışım."""
    u = random.Random(seed * 1_000_003 + movie_id).random()
    return -math.log(-math.log(min(max(u, 1e-9), 1 - 1e-9)))


def mmr(scored: list[tuple[float, dict]], lam: float = 0.78, item=lambda x: x) -> list:
    """Maximal Marginal Relevance: ilgi yüksek ama son seçilenlere çok benzeyen öğe
    bir sonraki sırayı bekler. `scored` = (puan, öğe) listesi, büyükten küçüğe sıralı."""
    remaining = list(scored)
    out: list = []
    while remaining:
        window = remaining[:40]
        recent = [item(o) for o in out[-12:]]
        best_i, best_v = 0, -1e9
        for idx, (r, obj) in enumerate(window):
            penalty = max((similarity(item(obj), o) for o in recent), default=0.0)
            v = lam * r - (1 - lam) * penalty
            if v > best_v:
                best_i, best_v = idx, v
        out.append(remaining.pop(best_i)[1])
    return out


def order_items(items: list[dict], p: SearchParams, lam: float = 0.78) -> list[dict]:
    if p.sort == "yeni":
        return sorted(items, key=lambda it: it["s"].get("release_date") or "", reverse=True)
    if p.sort == "populer":
        return sorted(items, key=lambda it: (it["s"].get("vote_count") or 0), reverse=True)
    if p.sort in ("puan", "imdb"):
        return sorted(items, key=lambda it: (it["rel"] > 0.5, it["q"]), reverse=True)

    scored = []
    for it in items:
        r = rank_value(it["rel"], it["q"], it["pop"], p.mode)
        if p.seed:
            r += 0.035 * _jitter(p.seed, it["id"])
        scored.append((r, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return mmr(scored, lam)


SORT_KEYS = {
    "uygun": lambda c: c["rank"],
    "puan": lambda c: c["pusula"]["score"] or 0,
    "imdb": lambda c: (c["ratings"]["imdb"] or 0, c["pusula"]["score"] or 0),
    "yeni": lambda c: c["release_date"] or "",
    "populer": lambda c: c["ratings"]["tmdb_votes"] or 0,
}


def sort_results(results: list[dict], sort: str) -> list[dict]:
    return sorted(results, key=SORT_KEYS.get(sort, SORT_KEYS["uygun"]), reverse=True)


# ----------------------------------------------------------------- sayfa

def run_search(p: SearchParams, tmdb: TMDBClient, omdb: OMDbClient | None, store: Store,
               result_limit: int = 16, candidate_limit: int = 100, workers: int = 8,
               cursor: int = 0) -> dict:
    """Havuzu hazırlar (önbellekten), sıralar ve `cursor`dan başlayan bir sayfa döndürür."""
    pool = build_pool(p, tmdb, store, candidate_limit, workers, target=max(48, result_limit * 3))
    ordered = order_items(pool["items"], p)
    terms_hit_total = len(pool["terms"])

    def enrich(it: dict) -> dict | None:
        tr = tmdb.movie_tr(it["id"])
        if not tr.get("id"):
            return None
        runtime = tr.get("runtime") or 0
        if 0 < runtime < 40:  # kısa film
            return None
        if p.max_runtime and (not runtime or runtime > int(p.max_runtime)):
            return None  # süre filtresi açıkken süresi bilinmeyen ya da uzun filmler
        en = tmdb.movie_en(it["id"])
        card = build_card(tr, en, store, omdb)
        card["match"] = it["match"]
        card["story"] = [CONCEPTS[k].label for k in it.get("story", []) if k in CONCEPTS]
        card["low_votes"] = it["tier"] > 0
        rank = rank_value(it["rel"], card["pusula"]["score"], it["pop"], p.mode)
        if p.seed:
            rank += 0.035 * _jitter(p.seed, it["id"])
        card["rank"] = round(rank, 4)
        card["_item"] = it
        return card

    def passes_rating(card: dict) -> bool:
        if not p.min_rating:
            return True
        r = card["ratings"]
        value = r["imdb"] if r["imdb"] is not None else (r["tmdb"] or 0)
        return value >= float(p.min_rating)

    cards: list[dict] = []
    i = max(0, cursor)
    while len(cards) < result_limit and i < len(ordered):
        batch = ordered[i: i + (result_limit - len(cards)) + 4]
        enriched = parallel_map(enrich, batch, workers)
        for it, card in zip(batch, enriched):
            if len(cards) >= result_limit:
                break
            i += 1
            if card and passes_rating(card):
                cards.append(card)

    # Sayfa içinde gerçek puanlarla (IMDb, yorumlar) ince ayar; "En uygun"da yine çeşitlendirerek.
    if p.sort == "uygun":
        ranked = sorted(((c["rank"], c) for c in cards), key=lambda x: x[0], reverse=True)
        cards = mmr(ranked, item=lambda c: c["_item"])
    else:
        cards = sort_results(cards, p.sort)
    for c in cards:
        c.pop("_item", None)
    next_cursor = i if i < len(ordered) else None
    return {
        "results": cards,
        "terms": pool["terms"],
        "excluded": pool["excluded"],
        "genre_terms": pool["genre_terms"],
        "unresolved": pool["unresolved"],
        "candidate_count": pool["candidate_count"],
        "total": len(ordered),
        "cursor": cursor,
        "next_cursor": next_cursor,
        "relaxed": any(c.get("low_votes") for c in cards),
        "terms_total": terms_hit_total,
    }


def surprise_pick(results: list[dict], top: int = 8) -> dict | None:
    pool = sorted(results, key=lambda c: c["rank"], reverse=True)[:top]
    return random.choice(pool) if pool else None
