"""IMDb'nin resmi (kişisel/ticari olmayan kullanım için) puan veri seti.

https://datasets.imdbws.com/title.ratings.tsv.gz dosyası her gün güncellenir ve
tüm yapımların IMDb puanı + oy sayısını içerir. Bunu yerel SQLite tablosuna
aktarıyoruz: böylece API limiti olmadan, orijinal IMDb puanını gösterebiliyoruz.
"""
from __future__ import annotations

import csv
import gzip
import os
import tempfile
from datetime import datetime, timezone

from .db import Store
from .tmdb import make_session

DATASET_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"


def _rows(path: str, min_votes: int):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader, None)
        if not header or header[:3] != ["tconst", "averageRating", "numVotes"]:
            raise ValueError("Beklenmeyen dosya biçimi: title.ratings.tsv.gz olmalı.")
        for row in reader:
            try:
                votes = int(row[2])
                if votes >= min_votes:
                    yield row[0], float(row[1]), votes
            except (IndexError, ValueError):
                continue


def import_file(store: Store, path: str, min_votes: int = 100) -> int:
    count = store.imdb_replace(_rows(path, min_votes))
    store.meta_set("imdb_updated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    store.meta_set("imdb_count", count)
    return count


def download_and_import(store: Store, min_votes: int = 100, url: str = DATASET_URL, session=None) -> int:
    session = session or make_session()
    fd, tmp = tempfile.mkstemp(suffix=".tsv.gz")
    os.close(fd)
    try:
        with session.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as out:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    out.write(chunk)
        return import_file(store, tmp, min_votes)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
