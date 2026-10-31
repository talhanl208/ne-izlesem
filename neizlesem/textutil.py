"""Türkçe biçimlendirme yardımcıları."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TR_TZ = timezone(timedelta(hours=3))  # Türkiye 2016'dan beri sürekli UTC+3
WEEKDAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def join_tr(items: list[str], conj: str = "ve") -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]


def runtime_text(minutes: int | None) -> str | None:
    if not minutes:
        return None
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h} sa {m} dk"
    return f"{h} sa" if h else f"{m} dk"


def date_tr(iso: str | None) -> str | None:
    if not iso or len(iso) < 10:
        return None
    try:
        y, mo, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
        return f"{d} {MONTHS[mo - 1]} {y}"
    except (ValueError, IndexError):
        return None


def year_of(iso: str | None) -> str | None:
    return iso[:4] if iso and len(iso) >= 4 else None


def votes_text(n: int | None) -> str:
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " milyon"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " bin"
    return str(n)


def money_text(n: int | None) -> str | None:
    if not n or n < 10_000:
        return None
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " milyar $"
    return f"{n / 1_000_000:.0f} milyon $"


def lower_tr(text: str) -> str:
    """Türkçe küçük harf (İ→i, I→ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def clamp_text(text: str | None, limit: int = 220) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def now_tr() -> datetime:
    return datetime.now(TR_TZ)


def today_tr() -> str:
    """'29 Ekim 2026, Perşembe'"""
    n = now_tr()
    return f"{n.day} {MONTHS[n.month - 1]} {n.year}, {WEEKDAYS[n.weekday()]}"
