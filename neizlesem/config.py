"""Uygulama ayarları. Gizli değerler .env dosyasından okunur (repoya girmez)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    DEFAULT_SECRET = "gelistirme-anahtari-degistir"
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
    MAX_CONTENT_LENGTH = 64 * 1024     # dosya yükleme yok; büyük istekleri reddet
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # PythonAnywhere gibi bir vekil sunucunun arkasındaysan 1 yap (gerçek IP'yi okur)
    TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"
    RATE_LIMIT = os.getenv("RATE_LIMIT", "1") == "1"
    # Kişisel kullanım: arama motorları siteyi listelemesin (IMDb şartlarıyla uyumlu)
    ALLOW_INDEXING = os.getenv("ALLOW_INDEXING", "0") == "1"

    # TMDB: v3 "API Key" ya da v4 "API Read Access Token" (eyJ... ile başlar) — ikisi de olur.
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
    # OMDb: isteğe bağlı. Rotten Tomatoes + Metacritic puanları buradan gelir.
    OMDB_API_KEY = os.getenv("OMDB_API_KEY", "").strip()

    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "neizlesem.db"))

    # Kendi kendine bakım (zamanlanmış görev gerektirmez)
    AUTO_MAINTENANCE = os.getenv("AUTO_MAINTENANCE", "1") == "1"
    CACHE_MAX_MB = _int("CACHE_MAX_MB", 150)               # önbellek bu boyutu aşarsa budanır
    CLEANUP_INTERVAL_HOURS = _int("CLEANUP_INTERVAL_HOURS", 6)
    IMDB_AUTO_UPDATE_DAYS = _int("IMDB_AUTO_UPDATE_DAYS", 30)  # 0 = otomatik güncelleme kapalı

    RESULT_LIMIT = _int("RESULT_LIMIT", 20)        # listede gösterilecek film sayısı
    CANDIDATE_LIMIT = _int("CANDIDATE_LIMIT", 60)  # eşleşme için incelenecek aday sayısı
    MAX_WORKERS = _int("MAX_WORKERS", 8)           # paralel API isteği
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))
