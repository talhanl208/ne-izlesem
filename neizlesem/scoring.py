"""Pusula Puanı: farklı kaynakları tek, şeffaf bir puanda birleştirir (0-10).

Ham ortalamalar az oylu filmlerde yanıltır (3 kişinin verdiği 9.5 gibi). Bu yüzden
IMDb ve TMDB puanlarına Bayes düzeltmesi uygulanır: oy sayısı arttıkça puan kendi
değerine, azaldıkça genel ortalamaya yaklaşır (IMDb Top 250 de benzer yöntemi kullanır).
"""
from __future__ import annotations

WEIGHTS = {"imdb": 0.35, "tmdb": 0.15, "rt": 0.15, "metacritic": 0.10, "reviews": 0.25}
LABELS = {
    "imdb": "IMDb izleyici puanı",
    "tmdb": "TMDB izleyici puanı",
    "rt": "Rotten Tomatoes (eleştirmen)",
    "metacritic": "Metacritic (eleştirmen)",
    "reviews": "İzleyici yorum analizi",
}


def bayes(rating: float | None, votes: int | None, m: float, c: float) -> float | None:
    if rating is None or not votes:
        return None
    return (votes / (votes + m)) * rating + (m / (votes + m)) * c


def quick_score(tmdb_avg: float | None, tmdb_votes: int | None) -> float:
    """Liste ön elemesi için hızlı puan (yalnızca TMDB verisiyle)."""
    return bayes(tmdb_avg, tmdb_votes, m=300, c=6.3) or 5.5


def pusula_score(
    imdb_rating: float | None = None,
    imdb_votes: int | None = None,
    tmdb_avg: float | None = None,
    tmdb_votes: int | None = None,
    rt: int | None = None,
    metacritic: int | None = None,
    review_summary: dict | None = None,
) -> dict:
    parts: dict[str, dict] = {}

    v = bayes(imdb_rating, imdb_votes, m=3000, c=6.4)
    if v is not None:
        parts["imdb"] = {"value": v, "raw": f"{imdb_rating:.1f} ({_short(imdb_votes)} oy)", "weight": WEIGHTS["imdb"]}

    v = bayes(tmdb_avg, tmdb_votes, m=300, c=6.3)
    if v is not None and tmdb_votes and tmdb_votes >= 20:
        parts["tmdb"] = {"value": v, "raw": f"{tmdb_avg:.1f} ({_short(tmdb_votes)} oy)", "weight": WEIGHTS["tmdb"]}

    if rt is not None:
        parts["rt"] = {"value": rt / 10, "raw": f"%{rt}", "weight": WEIGHTS["rt"]}
    if metacritic is not None:
        parts["metacritic"] = {"value": metacritic / 10, "raw": f"{metacritic}/100", "weight": WEIGHTS["metacritic"]}

    rs = review_summary or {}
    if rs.get("score") is not None and rs.get("count", 0) >= 2:
        confidence = min(1.0, rs["count"] / 8)  # az yorum varsa ağırlığı düşür
        parts["reviews"] = {
            "value": rs["score"],
            "raw": f"{rs['count']} yorum, %{rs.get('positive_share', 0)} olumlu",
            "weight": WEIGHTS["reviews"] * confidence,
        }

    total_w = sum(p["weight"] for p in parts.values())
    if not total_w:
        return {"score": None, "components": [], "confidence": "Yetersiz veri", "coverage": 0}

    score = sum(p["value"] * p["weight"] for p in parts.values()) / total_w
    components = [
        {
            "key": k,
            "label": LABELS[k],
            "value": round(p["value"], 1),
            "raw": p["raw"],
            "share": round(100 * p["weight"] / total_w),
        }
        for k, p in parts.items()
    ]
    coverage = sum(p["weight"] for p in parts.values())  # 0..1 arası: ne kadar kaynak var
    if coverage >= 0.7 and (imdb_votes or 0) >= 10000:
        confidence = "Yüksek"
    elif coverage >= 0.45:
        confidence = "Orta"
    else:
        confidence = "Düşük"
    return {"score": round(score, 1), "components": components, "confidence": confidence,
            "coverage": round(coverage, 2)}


def verdict(score: float | None) -> str:
    if score is None:
        return "Puanlamak için yeterli veri yok; özetine ve temalarına göre karar ver."
    if score >= 8.3:
        return "Kaçırma derim — listenin en üstüne yaz."
    if score >= 7.5:
        return "Gönül rahatlığıyla açabilirsin."
    if score >= 6.7:
        return "Temalar sana uyuyorsa keyifli bir seçim."
    if score >= 5.8:
        return "Beklentiyi biraz düşük tutarak izle."
    return "Şansını başka bir filmle denemek isteyebilirsin."


def _short(n: int | None) -> str:
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} mn".replace(".", ",")
    if n >= 1_000:
        return f"{n / 1_000:.1f} bin".replace(".", ",").replace(",0 bin", " bin")
    return str(n)
