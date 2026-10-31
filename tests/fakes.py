"""Testler için sahte TMDB / OMDb sunucusu.

Gerçek API'ye gitmeden uçtan uca akışı çalıştırmak için `requests.Session.get`
yerine geçen küçük bir taklit. Film verileri tamamen uydurmadır ("Test Filmi 1"...).
"""
from __future__ import annotations

import random
import re
from urllib.parse import urlparse

from neizlesem.catalog import CONCEPTS
from neizlesem.textutil import lower_tr

# Katalogdaki her İngilizce etikete sabit bir kimlik ver.
KEYWORDS: dict[str, int] = {}
_next = 1000
for _c in CONCEPTS.values():
    for _name in _c.en:
        if _name not in KEYWORDS:
            KEYWORDS[_name] = _next
            _next += 1
KEYWORDS.update({"chess": 9001, "chess player": 9002, "aftercreditsstinger": 9003, "sequel": 9004})
KW_NAMES = {v: k for k, v in KEYWORDS.items()}

REVENGE, HEIST, TIME_TRAVEL = KEYWORDS["revenge"], KEYWORDS["heist"], KEYWORDS["time travel"]

POS_REVIEW = (
    "The acting is brilliant and the cast has great chemistry. The story is gripping from start to finish. "
    "Cinematography is stunning. The ending was a masterpiece, I will rewatch it."
)
NEG_REVIEW = (
    "The plot is predictable and the pacing is slow, it drags in the middle. "
    "Acting was fine but the script is weak and full of cliches. Too long."
)
MIXED_REVIEW = (
    "Great performances, but the story is not very original. The music is beautiful. "
    "The action scenes are exciting and well done."
)


def _make_movies(n: int = 90) -> dict[int, dict]:
    rnd = random.Random(42)
    genres = [28, 12, 35, 80, 18, 27, 878, 53, 9648, 10749]
    pool = list(KEYWORDS.values())
    movies = {}
    for i in range(1, n + 1):
        kw = set(rnd.sample(pool, 4))
        g = set(rnd.sample(genres, 2))
        movies[i] = {
            "id": i,
            "title": f"Test Filmi {i}",
            "original_title": f"Test Movie {i}",
            "genre_ids": sorted(g),
            "keywords": kw,
            "vote_average": round(rnd.uniform(5.0, 8.8), 1),
            "vote_count": rnd.randint(200, 30000),
            "popularity": round(rnd.uniform(5, 300), 1),
            "release_date": f"{rnd.randint(1985, 2025)}-0{rnd.randint(1, 9)}-1{rnd.randint(0, 9)}",
            "original_language": rnd.choice(["en", "en", "en", "tr", "ko"]),
            "runtime": rnd.randint(85, 170),
            "poster_path": f"/poster{i}.jpg" if i % 7 else None,
            "backdrop_path": f"/backdrop{i}.jpg",
        }
    # Elle kurulmuş, beklenen sonuçları bildiğimiz filmler
    movies[1].update(title="İntikam Soygunu", keywords={REVENGE, HEIST, KEYWORDS["betrayal"]},
                     genre_ids=[28, 80], vote_average=8.4, vote_count=25000, popularity=400)
    movies[2].update(title="Yalnız İntikam", keywords={REVENGE}, genre_ids=[18, 53],
                     vote_average=8.9, vote_count=40000, popularity=380)
    movies[3].update(title="Korkunç Soygun", keywords={HEIST, REVENGE, KEYWORDS["ghost"]},
                     genre_ids=[27], vote_average=7.0, vote_count=5000, popularity=390)
    movies[4].update(title="Zaman Hırsızları", keywords={HEIST, TIME_TRAVEL}, genre_ids=[878, 28],
                     vote_average=7.6, vote_count=9000, popularity=350)
    return movies


MOVIES = _make_movies()

# Her temada eşleşen dev gişe filmi: 40 etiket (intikam ve soygun da içinde), çok popüler.
_pool = [k for k in KEYWORDS.values() if k not in (REVENGE, HEIST)]
MOVIES[95] = {
    "id": 95, "title": "Gişe Canavarı", "original_title": "Box Office Monster", "genre_ids": [28, 12],
    "keywords": {REVENGE, HEIST, *_pool[:38]}, "vote_average": 8.0, "vote_count": 60000, "popularity": 950.0,
    "release_date": "2021-05-05", "original_language": "en", "runtime": 150,
    "poster_path": "/poster95.jpg", "backdrop_path": "/backdrop95.jpg",
}
# "İntikam Soygunu"nun devam filmi: neredeyse aynı etiketler (çeşitlendirme testi için)
MOVIES[96] = dict(MOVIES[1], id=96, title="İntikam Soygunu 2", original_title="Test Movie 96",
                  keywords=set(MOVIES[1]["keywords"]) | {KEYWORDS["sequel"]}, vote_average=8.3,
                  vote_count=24000, popularity=390.0, release_date="2022-03-03",
                  poster_path="/poster96.jpg", backdrop_path="/backdrop96.jpg")
# Konusunda intikam geçen, az bilinen bir film (konu metni bonusu ve keşif modu testi)
MOVIES[97] = {
    "id": 97, "title": "Sessiz Hesap", "original_title": "Quiet Score", "genre_ids": [18, 53],
    "keywords": {REVENGE}, "vote_average": 7.6, "vote_count": 420, "popularity": 15.0,
    "release_date": "2008-02-02", "original_language": "en", "runtime": 101,
    "poster_path": "/poster97.jpg", "backdrop_path": "/backdrop97.jpg",
    "overview": "Ailesini kaybeden bir adamın sessiz intikamı.",
}

# Az oylu Türk korku filmleri (TMDB'de niş yapımlar genelde birkaç düzine/yüz oy alır)
for _id, _title, _votes, _avg, _runtime in [
    (91, "Lanetli Köy", 140, 6.1, 98),
    (92, "Gece Ziyareti", 38, 5.9, 0),      # TMDB'de süresi girilmemiş
    (93, "Karanlık Konak", 12, 6.4, 104),
    (94, "Kısa Korku", 25, 6.0, 14),        # kısa film: listede olmamalı
]:
    MOVIES[_id] = {
        "id": _id, "title": _title, "original_title": _title, "genre_ids": [27, 53],
        "keywords": {KEYWORDS["ghost"]}, "vote_average": _avg, "vote_count": _votes, "popularity": 20.0 + _id,
        "release_date": "2019-10-10", "original_language": "tr", "runtime": _runtime,
        "poster_path": f"/poster{_id}.jpg", "backdrop_path": f"/backdrop{_id}.jpg",
    }


class FakeResponse:
    def __init__(self, data, status: int = 200):
        self._data = data
        self.status_code = status

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def iter_content(self, chunk_size=1):
        yield b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _summary(m: dict, lang: str = "tr") -> dict:
    overview = m.get("overview") or (f"{m['title']} için Türkçe özet." if m["id"] % 5 else "")
    return {k: m[k] for k in ("id", "title", "original_title", "genre_ids", "vote_average", "vote_count",
                              "popularity", "release_date", "original_language", "poster_path", "backdrop_path")} | {
        "overview": overview if lang == "tr" else ""}


def _ids(value: str | None) -> tuple[set[int], str]:
    if not value:
        return set(), ""
    mode = "and" if "," in value else "or"
    return {int(x) for x in re.split(r"[,|]", value) if x}, mode


class FakeSession:
    """requests.Session yerine: .get(url, params=..., headers=..., timeout=...)"""

    def __init__(self, fail_auth: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.fail_auth = fail_auth

    def get(self, url, params=None, headers=None, timeout=None, stream=False):
        params = dict(params or {})
        self.calls.append((url, params))
        u = urlparse(url)
        if "omdbapi" in u.netloc:
            return FakeResponse(self._omdb(params))
        if self.fail_auth:
            return FakeResponse({"status_message": "Invalid API key"}, 401)
        path = u.path.replace("/3", "", 1)
        return self._tmdb(path, params)

    # ---------------------------------------------------------------- OMDb
    def _omdb(self, params):
        imdb_id = params.get("i", "")
        n = int(imdb_id[2:]) if imdb_id.startswith("tt") else 0
        m = MOVIES.get(n)
        if not m:
            return {"Response": "False", "Error": "Incorrect IMDb ID."}
        return {
            "Response": "True", "imdbRating": f"{min(9.5, m['vote_average'] + 0.2):.1f}",
            "imdbVotes": f"{m['vote_count'] * 9:,}",
            "Ratings": [{"Source": "Rotten Tomatoes", "Value": f"{int(m['vote_average'] * 10)}%"},
                        {"Source": "Metacritic", "Value": f"{int(m['vote_average'] * 9)}/100"}],
            "Awards": "Won 1 Oscar. 5 wins & 10 nominations total" if n == 1 else "N/A",
        }

    # ---------------------------------------------------------------- TMDB
    def _tmdb(self, path, p):
        if path == "/search/keyword":
            q = p.get("query", "").lower()
            res = [{"id": i, "name": n} for n, i in KEYWORDS.items() if q in n]
            res.sort(key=lambda r: (r["name"] != q, len(r["name"])))
            return FakeResponse({"page": 1, "results": res[:20], "total_results": len(res)})
        m = re.fullmatch(r"/keyword/(\d+)", path)
        if m:
            kid = int(m.group(1))
            return FakeResponse({"id": kid, "name": KW_NAMES[kid]} if kid in KW_NAMES else {}, 200 if kid in KW_NAMES else 404)
        if path == "/discover/movie":
            return FakeResponse(self._discover(p))
        m = re.fullmatch(r"/movie/(\d+)/keywords", path)
        if m:
            mv = MOVIES.get(int(m.group(1)))
            if not mv:
                return FakeResponse({}, 404)
            return FakeResponse({"id": mv["id"], "keywords": [{"id": k, "name": KW_NAMES[k]} for k in mv["keywords"]]})
        m = re.fullmatch(r"/movie/(\d+)", path)
        if m:
            mv = MOVIES.get(int(m.group(1)))
            if not mv:
                return FakeResponse({}, 404)
            return FakeResponse(self._movie(mv, p))
        m = re.fullmatch(r"/person/(\d+)/movie_credits", path)
        if m:
            pid = int(m.group(1))
            cast = [_summary(MOVIES[i]) | {"character": "Rol"} for i in range(5, 12)]
            for c, mv_id in zip(cast, range(5, 12)):
                c["vote_count"] = 1000 + pid + mv_id
            return FakeResponse({"cast": cast, "crew": []})
        if path == "/trending/movie/week":
            return FakeResponse({"results": [_summary(mv) for mv in list(MOVIES.values())[:20]]})
        if path == "/watch/providers/movie":
            return FakeResponse({"results": [
                {"provider_id": 8, "provider_name": "Netflix", "logo_path": "/n.jpg", "display_priorities": {"TR": 1}},
                {"provider_id": 119, "provider_name": "Amazon Prime Video", "logo_path": "/a.jpg", "display_priorities": {"TR": 2}},
                {"provider_id": 3, "provider_name": "Google Play Movies", "logo_path": "/g.jpg", "display_priorities": {"TR": 3}},
            ]})
        if path == "/search/movie":
            q = lower_tr(p.get("query", ""))
            res = [_summary(mv) for mv in MOVIES.values() if q in lower_tr(mv["title"])]
            return FakeResponse({"page": 1, "results": res[:20]})
        return FakeResponse({}, 404)

    def _discover(self, p):
        kw, kw_mode = _ids(p.get("with_keywords"))
        gw, g_mode = _ids(p.get("with_genres"))
        x_kw, _ = _ids(p.get("without_keywords"))
        x_g, _ = _ids(p.get("without_genres"))
        out = []
        for mv in MOVIES.values():
            if kw and (not kw <= mv["keywords"] if kw_mode == "and" else not kw & mv["keywords"]):
                continue
            g = set(mv["genre_ids"])
            if gw and (not gw <= g if g_mode == "and" else not gw & g):
                continue
            if x_kw & mv["keywords"] or x_g & g:
                continue
            if mv["vote_count"] < float(p.get("vote_count.gte", 0)):
                continue
            if "vote_count.lte" in p and mv["vote_count"] > float(p["vote_count.lte"]):
                continue
            if mv["vote_average"] < float(p.get("vote_average.gte", 0)):
                continue
            if p.get("with_original_language") and mv["original_language"] != p["with_original_language"]:
                continue
            if "with_runtime.gte" in p and mv["runtime"] < float(p["with_runtime.gte"]):
                continue
            if "with_runtime.lte" in p and mv["runtime"] > float(p["with_runtime.lte"]):
                continue
            gte, lte = p.get("primary_release_date.gte"), p.get("primary_release_date.lte")
            if gte and mv["release_date"] < gte or lte and mv["release_date"] > lte:
                continue
            out.append(mv)
        key = p.get("sort_by", "popularity.desc").split(".")[0]
        out.sort(key=lambda m: m[key], reverse=True)
        page = int(p.get("page", 1))
        chunk = out[(page - 1) * 20: page * 20]
        return {"page": page, "results": [_summary(m) for m in chunk], "total_results": len(out),
                "total_pages": max(1, (len(out) + 19) // 20)}

    def _movie(self, mv, p):
        lang = p.get("language", "en-US")
        data = _summary(mv, "tr" if lang.startswith("tr") else "en")
        data.update(runtime=mv["runtime"], tagline="Her şeyin bir bedeli var." if lang.startswith("tr") else "",
                    genres=[{"id": g, "name": str(g)} for g in mv["genre_ids"]], imdb_id=f"tt{mv['id']:07d}",
                    budget=50_000_000, revenue=210_000_000, production_countries=[{"name": "Amerika Birleşik Devletleri"}])
        if not lang.startswith("tr"):
            data["overview"] = f"English overview of {mv['original_title']}."
        appends = (p.get("append_to_response") or "").split(",")
        if "keywords" in appends:
            data["keywords"] = {"keywords": [{"id": k, "name": KW_NAMES[k]} for k in mv["keywords"]]}
        if "external_ids" in appends:
            data["external_ids"] = {"imdb_id": f"tt{mv['id']:07d}"}
        if "credits" in appends:
            data["credits"] = {
                "cast": [{"id": 500 + j, "name": f"Oyuncu {j}", "character": f"Karakter {j}",
                          "profile_path": None} for j in range(1, 9)],
                "crew": [{"id": 900, "name": "Yönetmen Kişi", "job": "Director"},
                         {"id": 901, "name": "Senarist Kişi", "job": "Screenplay"},
                         {"id": 902, "name": "Besteci Kişi", "job": "Original Music Composer"}],
            }
        if "videos" in appends:
            data["videos"] = {"results": [{"site": "YouTube", "key": "abcDEF12345", "type": "Trailer",
                                           "iso_639_1": "en", "official": True, "name": "Official Trailer"}]}
        if "watch/providers" in appends:
            data["watch/providers"] = {"results": {"TR": {"link": "https://www.themoviedb.org/movie/1/watch",
                                                          "flatrate": [{"provider_name": "Netflix", "logo_path": "/n.jpg", "display_priority": 1}]}}}
        if "recommendations" in appends:
            data["recommendations"] = {"results": [_summary(MOVIES[i]) for i in range(10, 20)]}
        if "release_dates" in appends:
            data["release_dates"] = {"results": [{"iso_3166_1": "TR", "release_dates": [{"certification": "13+"}]}]}
        if "reviews" in appends:
            texts = [POS_REVIEW, POS_REVIEW, MIXED_REVIEW, NEG_REVIEW] if mv["id"] % 3 else [POS_REVIEW]
            data["reviews"] = {"results": [
                {"author": f"izleyici{j}", "content": t, "url": f"https://www.themoviedb.org/review/{mv['id']}{j}",
                 "author_details": {"rating": 9.0 if t is POS_REVIEW and j == 0 else None}}
                for j, t in enumerate(texts)]}
        return data
