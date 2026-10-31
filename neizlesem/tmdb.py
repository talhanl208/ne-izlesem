"""TMDB (The Movie Database) istemcisi.

Neden TMDB? IMDb'nin herkese açık bir API'si yok; TMDB ise ücretsiz ve filmleri
çok detaylı "anahtar kelimelerle" (revenge, heist, time travel...) etiketliyor.
Ayrıca Türkçe özet, oyuncu kadrosu, kullanıcı yorumları, fragman ve Türkiye'deki
yayın platformlarını da veriyor. Her yanıt SQLite'ta önbelleğe alınır.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import Store

HOUR = 3600
DAY = 24 * HOUR


class TMDBError(Exception):
    """TMDB'den veri alınamadı."""


class TMDBNotConfigured(TMDBError):
    """API anahtarı girilmemiş."""


class TMDBAuthError(TMDBError):
    """API anahtarı geçersiz."""


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = "NeIzlesem/1.0 (+https://github.com/)"
    return session


def parallel_map(fn: Callable, items: Iterable, workers: int = 8) -> list:
    """fn'i öğelere paralel uygular, sırayı korur.

    Tek bir öğedeki hata için None döner (bir film yüzünden arama çökmesin).
    Anahtar eksik/geçersizse ya da TÜM istekler TMDB hatası verdiyse hatayı yükseltir.
    """
    items = list(items)
    if not items:
        return []
    errors: list[TMDBError] = []

    def safe(item):
        try:
            return fn(item)
        except (TMDBNotConfigured, TMDBAuthError):
            raise
        except TMDBError as exc:
            errors.append(exc)
            return None
        except Exception:
            return None

    if workers <= 1 or len(items) == 1:
        results = [safe(i) for i in items]
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
            results = list(pool.map(safe, items))
    if errors and len(errors) == len(items):
        raise errors[0]
    return results


class TMDBClient:
    BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p/"

    def __init__(self, api_key: str, store: Store, timeout: float = 10, session=None):
        self.api_key = (api_key or "").strip()
        self.store = store
        self.timeout = timeout
        self.session = session or make_session()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    # ---- düşük seviye ---------------------------------------------------
    def get(self, path: str, params: dict | None = None, ttl: float = DAY):
        params = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
        cache_key = "tmdb:" + path + "?" + urlencode(sorted(params.items()))
        cached = self.store.cache_get(cache_key)
        if cached is not None:
            return cached
        if not self.configured:
            raise TMDBNotConfigured("TMDB API anahtarı tanımlı değil.")

        query = dict(params)
        headers = {"Accept": "application/json"}
        if self.api_key.startswith("eyJ"):  # v4 okuma token'ı
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:                               # v3 API anahtarı
            query["api_key"] = self.api_key

        try:
            resp = self.session.get(self.BASE + path, params=query, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TMDBError("TMDB'ye ulaşılamadı. İnternet bağlantısını kontrol et.") from exc

        if resp.status_code == 401:
            raise TMDBAuthError("TMDB API anahtarı geçersiz. .env dosyasındaki TMDB_API_KEY değerini kontrol et.")
        if resp.status_code == 404:
            self.store.cache_set(cache_key, {}, HOUR)
            return {}
        if resp.status_code >= 400:
            raise TMDBError(f"TMDB hata döndürdü (HTTP {resp.status_code}).")

        data = resp.json()
        self.store.cache_set(cache_key, data, ttl)
        return data

    @classmethod
    def image(cls, path: str | None, size: str = "w342") -> str | None:
        return f"{cls.IMAGE_BASE}{size}{path}" if path else None

    # ---- anahtar kelimeler ----------------------------------------------
    def search_keywords(self, query: str) -> list[dict]:
        data = self.get("/search/keyword", {"query": query.strip()}, ttl=30 * DAY)
        return data.get("results", []) if data else []

    def keyword(self, keyword_id: int) -> dict:
        return self.get(f"/keyword/{int(keyword_id)}", ttl=90 * DAY) or {}

    def resolve_keyword(self, name: str) -> int | None:
        """İngilizce anahtar kelime adını TMDB kimliğine çevirir (önce birebir eşleşme)."""
        name = name.strip().lower()
        results = self.search_keywords(name)
        for r in results:
            if (r.get("name") or "").strip().lower() == name:
                return r["id"]
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        for r in results[:5]:
            if pattern.search((r.get("name") or "").lower()):
                return r["id"]
        return None

    def movie_keyword_ids(self, movie_id: int) -> set[int]:
        data = self.get(f"/movie/{int(movie_id)}/keywords", ttl=30 * DAY) or {}
        return {k["id"] for k in data.get("keywords", [])}

    # ---- keşif & arama --------------------------------------------------
    def discover(self, params: dict, page: int = 1) -> dict:
        p = {"language": "tr-TR", "include_adult": "false", "include_video": "false", "page": page}
        p.update(params)
        return self.get("/discover/movie", p, ttl=6 * HOUR) or {}

    def search_movies(self, query: str, page: int = 1) -> dict:
        return self.get(
            "/search/movie",
            {"query": query.strip(), "language": "tr-TR", "include_adult": "false", "page": page},
            ttl=DAY,
        ) or {}

    # ---- film ayrıntıları -----------------------------------------------
    def movie_tr(self, movie_id: int) -> dict:
        """Türkçe ayrıntı + anahtar kelime, kadro, fragman, platform, öneri — tek istekte."""
        return self.get(
            f"/movie/{int(movie_id)}",
            {
                "language": "tr-TR",
                "append_to_response": "keywords,external_ids,credits,videos,watch/providers,recommendations,release_dates",
                "include_video_language": "tr,en,null",
            },
            ttl=3 * DAY,
        ) or {}

    def movie_en(self, movie_id: int) -> dict:
        """İngilizce özet (Türkçesi yoksa) + izleyici yorumları."""
        return self.get(
            f"/movie/{int(movie_id)}",
            {"language": "en-US", "append_to_response": "reviews"},
            ttl=3 * DAY,
        ) or {}

    def person_movie_credits(self, person_id: int) -> dict:
        return self.get(f"/person/{int(person_id)}/movie_credits", {"language": "tr-TR"}, ttl=14 * DAY) or {}

    def trending_week(self) -> list[dict]:
        data = self.get("/trending/movie/week", {"language": "tr-TR"}, ttl=12 * HOUR) or {}
        return data.get("results", [])

    def watch_providers_tr(self) -> list[dict]:
        data = self.get("/watch/providers/movie", {"watch_region": "TR", "language": "tr-TR"}, ttl=7 * DAY) or {}
        return data.get("results", [])
