"""OMDb istemcisi (isteğe bağlı).

OMDb tek istekte IMDb + Rotten Tomatoes + Metacritic puanlarını verir.
Ücretsiz anahtar günde 1000 istek hakkı tanır; kota dolunca sessizce devre dışı kalır.
Not: PythonAnywhere ücretsiz hesapta omdbapi.com izinli listede değil; orada IMDb
puanı resmi IMDb veri setinden (imdb_dataset.py) gelir.
"""
from __future__ import annotations

import re

import requests

from .db import Store
from .tmdb import DAY, HOUR, make_session


def _num(text) -> float | None:
    if not text or text == "N/A":
        return None
    m = re.search(r"[\d.,]+", str(text))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_omdb(data: dict) -> dict:
    out = {"imdb_rating": None, "imdb_votes": None, "rt": None, "metacritic": None, "awards": None}
    if not data or data.get("Response") == "False":
        return out
    out["imdb_rating"] = _num(data.get("imdbRating"))
    votes = _num(data.get("imdbVotes"))
    out["imdb_votes"] = int(votes) if votes is not None else None
    for r in data.get("Ratings", []):
        src, val = r.get("Source", ""), r.get("Value", "")
        if src == "Rotten Tomatoes":
            n = _num(val)
            out["rt"] = int(n) if n is not None else None
        elif src == "Metacritic":
            n = _num(val.split("/")[0] if val else None)
            out["metacritic"] = int(n) if n is not None else None
    if out["metacritic"] is None:
        n = _num(data.get("Metascore"))
        out["metacritic"] = int(n) if n is not None else None
    awards = data.get("Awards")
    out["awards"] = awards if awards and awards != "N/A" else None
    return out


class OMDbClient:
    BASE = "https://www.omdbapi.com/"
    _BLOCK_KEY = "omdb:blocked"

    def __init__(self, api_key: str, store: Store, timeout: float = 8, session=None):
        self.api_key = (api_key or "").strip()
        self.store = store
        self.timeout = timeout
        self.session = session or make_session()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def by_imdb_id(self, imdb_id: str | None) -> dict | None:
        if not imdb_id or not self.configured:
            return None
        key = f"omdb:{imdb_id}"
        cached = self.store.cache_get(key)
        if cached is not None:
            return cached
        if self.store.cache_get(self._BLOCK_KEY):
            return None
        try:
            resp = self.session.get(
                self.BASE, params={"i": imdb_id, "apikey": self.api_key}, timeout=self.timeout
            )
            data = resp.json()
        except (requests.RequestException, ValueError):
            return None

        error = (data.get("Error") or "").lower() if isinstance(data, dict) else ""
        if "limit" in error:           # günlük kota doldu
            self.store.cache_set(self._BLOCK_KEY, True, 6 * HOUR)
            return None
        if "api key" in error:         # anahtar geçersiz
            self.store.cache_set(self._BLOCK_KEY, True, DAY)
            return None

        parsed = parse_omdb(data)
        self.store.cache_set(key, parsed, 7 * DAY)
        return parsed
