"""Film için kısa, sohbet havasında Türkçe anlatım üretir (kural tabanlı).

Türkçede isimlere ek getirmek (Nolan'ın, Inception'ı...) ses uyumu gerektirdiği için
cümleleri isimlerin eksiz kalacağı şekilde kurduk.
"""
from __future__ import annotations

from .textutil import join_tr, lower_tr


def build_story(d: dict) -> list[str]:
    paragraphs: list[str] = []

    # 1) Kimlik kartı
    bits = []
    genre_text = join_tr([lower_tr(g) for g in d.get("genres", [])[:3]])
    lead = f"{d['year']} yapımı " if d.get("year") else ""
    if d.get("runtime_text") and genre_text:
        bits.append(f"{lead}{d['title']}, {d['runtime_text']} süren bir {genre_text} filmi.")
    elif genre_text:
        bits.append(f"{lead}{d['title']}, bir {genre_text} filmi.")
    else:
        bits.append(f"{lead}{d['title']}.".strip())
    if d.get("directors"):
        bits.append(f"Yönetmen koltuğunda {join_tr(d['directors'])} oturuyor.")
    leads = [c["name"] for c in d.get("cast", [])[:3]]
    if len(leads) >= 2:
        bits.append(f"Başrolleri {join_tr(leads)} paylaşıyor.")
    elif leads:
        bits.append(f"Başrolde {leads[0]} var.")
    if d.get("original_language") not in (None, "", "en", "tr") and d.get("language"):
        bits.append(f"Orijinal dili {d['language']}.")
    paragraphs.append(" ".join(bits))

    # 2) Temalar
    theme_bits = []
    if d.get("matched"):
        theme_bits.append(f"Seçtiğin temalardan {join_tr([lower_tr(m) for m in d['matched']])} bu filmde var.")
    if d.get("missed"):
        theme_bits.append(f"{join_tr(d['missed'])} ise filmde belirgin değil.")
    other = [k["label"] for k in d.get("keywords", []) if k["translated"] and k["label"] not in d.get("matched", [])]
    if other:
        theme_bits.append(f"Öne çıkan temalar: {join_tr([lower_tr(o) for o in other[:5]])}.")
    if theme_bits:
        paragraphs.append(" ".join(theme_bits))

    # 3) İzleyiciler ne diyor
    r = d.get("reviews") or {}
    if r.get("count", 0) >= 2:
        sent = []
        pros = [lower_tr(p["label"]) for p in r.get("pros", [])[:3]]
        cons = [lower_tr(c["label"]) for c in r.get("cons", [])[:2]]
        mixed = [lower_tr(m["label"]) for m in r.get("mixed", [])[:2]]
        if pros and cons:
            sent.append(f"Yorumlarda en çok {join_tr(pros)} övülüyor; {join_tr(cons)} ise eleştirilerin odağında.")
        elif pros:
            sent.append(f"Yorumlarda en çok {join_tr(pros)} övülüyor.")
        elif cons:
            sent.append(f"Yorumlarda {join_tr(cons)} eleştiriliyor.")
        if mixed:
            sent.append(f"{join_tr(mixed).capitalize()} konusunda görüşler bölünmüş.")
        share = r.get("positive_share")
        if share is not None:
            sent.append(f"İncelenen {r['count']} yorumda olumlu oranı %{share}.")
        paragraphs.append(" ".join(sent))
    elif r.get("count") == 1:
        paragraphs.append("Bu film için şimdilik tek bir izleyici yorumu var; puanı daha çok IMDb ve TMDB oylarına dayanıyor.")
    else:
        paragraphs.append("Bu film için henüz izleyici yorumu yok; puanı IMDb ve TMDB oylarına dayanıyor.")

    # 4) Karar
    score = (d.get("pusula") or {}).get("score")
    if score is not None:
        score_text = f"{score:.1f}".replace(".", ",")
        paragraphs.append(f"Pusula Puanı {score_text}/10: {d.get('verdict', '')}")
    return paragraphs
