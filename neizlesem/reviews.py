"""Kural tabanlı izleyici yorumu analizi (yapay zekâ API'si gerektirmez).

TMDB yorumları çoğunlukla İngilizcedir. Her yorumu cümlelere ayırıp:
  * cümlenin duygu puanını (olumlu/olumsuz kelime sözlüğü + olumsuzlama + pekiştirme),
  * cümlenin hangi konudan bahsettiğini (oyunculuk, senaryo, tempo...)
çıkarıyoruz. Konu başına "kaç yorum övmüş / eleştirmiş" sayılır; böylece tek bir
uzun yorum sonucu domine edemez.
"""
from __future__ import annotations

import math
import re

POSITIVE = {
    "great": 1.0, "excellent": 1.5, "brilliant": 1.5, "masterpiece": 2.0, "amazing": 1.3, "awesome": 1.2,
    "superb": 1.5, "superbly": 1.4, "fantastic": 1.4, "wonderful": 1.3, "beautiful": 1.0, "beautifully": 1.0,
    "stunning": 1.3, "gorgeous": 1.1, "compelling": 1.1, "gripping": 1.2, "captivating": 1.2, "engaging": 1.0,
    "memorable": 1.0, "perfect": 1.4, "perfectly": 1.2, "best": 1.0, "loved": 1.2, "love": 0.8, "enjoyed": 1.0,
    "enjoyable": 1.0, "fun": 0.8, "entertaining": 1.0, "good": 0.7, "solid": 0.7, "strong": 0.7,
    "impressive": 1.0, "powerful": 1.1, "moving": 1.0, "touching": 1.0, "hilarious": 1.2, "funny": 0.8,
    "clever": 1.0, "smart": 0.8, "intelligent": 1.0, "thrilling": 1.1, "exciting": 1.0, "terrific": 1.3,
    "outstanding": 1.5, "phenomenal": 1.5, "incredible": 1.3, "remarkable": 1.2, "refreshing": 1.0,
    "original": 0.7, "unique": 0.7, "recommend": 1.0, "recommended": 1.0, "worth": 0.8, "nice": 0.6,
    "favorite": 1.1, "favourite": 1.1, "gem": 1.2, "epic": 1.0, "breathtaking": 1.4, "flawless": 1.5,
    "riveting": 1.3, "satisfying": 1.0, "heartfelt": 1.0, "charming": 1.0, "delightful": 1.2,
    "spectacular": 1.3, "immersive": 1.1, "nuanced": 1.0, "authentic": 0.9, "believable": 0.8,
    "iconic": 1.1, "classic": 0.8, "underrated": 0.8, "fascinating": 1.1, "intense": 0.6, "tense": 0.5,
}
NEGATIVE = {
    "bad": 1.0, "terrible": 1.5, "awful": 1.5, "horrible": 1.4, "boring": 1.3, "bored": 1.1, "dull": 1.2,
    "weak": 1.0, "poor": 1.0, "poorly": 1.1, "mediocre": 1.0, "predictable": 1.0, "cliche": 1.0,
    "cliché": 1.0, "cliched": 1.0, "clichéd": 1.0, "mess": 1.1, "messy": 1.0, "waste": 1.4, "wasted": 1.2,
    "worst": 1.6, "disappointing": 1.2, "disappointed": 1.2, "disappointment": 1.2, "forgettable": 1.1,
    "slow": 0.7, "tedious": 1.2, "pointless": 1.2, "stupid": 1.2, "dumb": 1.1, "silly": 0.8,
    "annoying": 1.0, "unnecessary": 0.8, "flat": 0.8, "bland": 1.0, "lazy": 1.1, "overrated": 1.0,
    "confusing": 0.9, "convoluted": 1.0, "shallow": 1.0, "cheesy": 0.8, "cringe": 1.1, "cringey": 1.1,
    "cringeworthy": 1.2, "meh": 0.8, "uninspired": 1.1, "lacks": 0.7, "lacking": 0.8, "unconvincing": 1.0,
    "nonsense": 1.1, "ridiculous": 0.9, "drags": 1.0, "dragged": 1.0, "overlong": 1.0, "bloated": 1.0,
    "generic": 1.0, "forced": 0.8, "wooden": 1.0, "hollow": 1.0, "underwhelming": 1.2, "garbage": 1.6,
    "trash": 1.5, "unwatchable": 1.8, "painful": 1.0, "sloppy": 1.1, "incoherent": 1.2, "fails": 1.0,
    "failed": 1.0, "failure": 1.1, "formulaic": 1.0,
}
BIGRAMS = {
    "well done": 1.0, "well written": 1.1, "well acted": 1.1, "well made": 1.0, "must see": 1.4,
    "too long": -1.0, "plot holes": -1.1, "plot hole": -1.1, "fell flat": -1.1, "falls flat": -1.1,
}
NEGATORS = {
    "not", "no", "never", "n't", "hardly", "barely", "isn't", "wasn't", "doesn't", "didn't", "don't",
    "aren't", "weren't", "cannot", "can't", "couldn't", "won't", "nothing", "without", "neither", "nor",
}
INTENSIFIERS = {
    "very": 1.3, "really": 1.25, "extremely": 1.5, "incredibly": 1.5, "so": 1.2, "truly": 1.3,
    "absolutely": 1.5, "quite": 1.1, "super": 1.3, "highly": 1.3, "too": 1.2, "pretty": 1.1,
}

ASPECTS: list[tuple[str, str, re.Pattern]] = [
    ("oyunculuk", "Oyunculuk", re.compile(r"\b(acting|performances?|cast|actors?|actress(es)?|portrayal|portrays?|chemistry)\b")),
    ("senaryo", "Senaryo", re.compile(r"\b(story|stories|plot|script|screenplay|writing|written|narrative|storyline|dialogues?)\b")),
    ("karakter", "Karakterler", re.compile(r"\b(characters?|protagonist|villain|antagonist)\b")),
    ("gorsel", "Görsellik", re.compile(r"\b(visuals?|visually|cinematography|shots?|camera|photography|cgi|vfx|effects|production design|scenery|imagery)\b")),
    ("muzik", "Müzik", re.compile(r"\b(music|score|soundtrack|songs?|sound design|composer)\b")),
    ("yonetmen", "Yönetmenlik", re.compile(r"\b(direction|directed|director|directing|filmmaking)\b")),
    ("tempo", "Tempo", re.compile(r"\b(pacing|paced|pace|slow|drags?|dragged|runtime|too long|overlong|fast-paced)\b")),
    ("aksiyon", "Aksiyon sahneleri", re.compile(r"\b(action|fights?|fighting|fight scenes?|choreograph\w*|stunts?|set pieces?|chase)\b")),
    ("final", "Final", re.compile(r"\b(ending|endings|finale|climax|third act|last act|conclusion|twists?)\b")),
    ("duygu", "Duygusal etki", re.compile(r"\b(emotional(ly)?|heart|tears?|cried|moving|touching)\b")),
    ("mizah", "Mizah", re.compile(r"\b(humou?r|funny|jokes?|laugh(s|ed|ing)?|comedic|hilarious)\b")),
    ("gerilim", "Atmosfer", re.compile(r"\b(tension|tense|suspense|suspenseful|atmosphere|atmospheric|dread|creepy|scary|scares?)\b")),
]

FLAGS_POS = [
    ("masterpiece", "Başyapıt diyenler var", re.compile(r"\bmasterpiece\b")),
    ("must", "“Mutlaka izlenmeli” diyenler çok", re.compile(r"\b(must[- ]see|must[- ]watch)\b")),
    ("rewatch", "Tekrar izlenesi bulunmuş", re.compile(r"\b(re-?watch(ed|ing)?|watch(ed)? it (again|twice)|multiple times)\b")),
    ("seat", "Koltuğa çivileyen cinsten", re.compile(r"\bedge of (my|your|the) seat\b")),
    ("gem", "Hak ettiği ilgiyi görmemiş bir cevher deniyor", re.compile(r"\b(underrated|hidden gem)\b")),
]
FLAGS_NEG = [
    ("predictable", "Tahmin edilebilir bulunmuş", re.compile(r"\bpredictable\b")),
    ("long", "Fazla uzun / yer yer sarkıyor", re.compile(r"\b(too long|overlong|bloated|drags|dragged)\b")),
    ("cliche", "Klişe bulunmuş", re.compile(r"\b(clich[eé]s?|clich[eé]d|generic|formulaic)\b")),
    ("holes", "Senaryo boşlukları eleştirilmiş", re.compile(r"\bplot holes?\b")),
    ("confusing", "Kafa karıştırıcı bulanlar var", re.compile(r"\b(confusing|convoluted|incoherent)\b")),
    ("boring", "Sıkıcı bulanlar var", re.compile(r"\b(boring|dull|tedious)\b")),
]

_TOKEN = re.compile(r"[a-zà-ÿ]+(?:'[a-z]+)?|n't")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_TAGS = re.compile(r"<[^>]+>")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def clean_text(text: str) -> str:
    text = _MD_LINK.sub(r"\1", text or "")
    text = _URL.sub("", text)
    text = _TAGS.sub(" ", text)
    text = re.sub(r"[*_#>`~]+", "", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 2]


def _clause_score(tokens: list[str]) -> tuple[float, float]:
    pos = neg = 0.0
    for i, tok in enumerate(tokens):
        weight = 0.0
        if tok in POSITIVE:
            weight = POSITIVE[tok]
        elif tok in NEGATIVE:
            weight = -NEGATIVE[tok]
        if i > 0:
            bigram = tokens[i - 1] + " " + tok
            if bigram in BIGRAMS and BIGRAMS[bigram]:
                weight = BIGRAMS[bigram]
        if not weight:
            continue
        if i > 0 and tokens[i - 1] in INTENSIFIERS:
            weight *= INTENSIFIERS[tokens[i - 1]]
        window = tokens[max(0, i - 3):i]
        if any(w in NEGATORS or w.endswith("n't") for w in window):
            weight = -weight * 0.8
        if weight > 0:
            pos += weight
        else:
            neg += -weight
    return pos, neg


def sentence_sentiment(sentence: str) -> tuple[float, float]:
    """(olumlu, olumsuz) ağırlık toplamı. 'but/however' sonrası kısım daha ağır basar."""
    low = sentence.lower().replace("’", "'")
    parts = re.split(r"\b(?:but|however|although|though|yet)\b", low, maxsplit=1)
    if len(parts) == 2:
        p1, n1 = _clause_score(_TOKEN.findall(parts[0]))
        p2, n2 = _clause_score(_TOKEN.findall(parts[1]))
        return p1 * 0.7 + p2 * 1.3, n1 * 0.7 + n2 * 1.3
    return _clause_score(_TOKEN.findall(low))


def _polarity(pos: float, neg: float) -> float:
    return (pos - neg) / (pos + neg + 1.0)


def _review_lexicon_score(pos: float, neg: float) -> float:
    raw = 5.0 + 5.0 * (pos - neg) / (pos + neg + 3.0)
    return max(1.0, min(9.5, raw))


def analyze_reviews(reviews: list[dict]) -> dict:
    """TMDB yorum listesini özetler."""
    result = {
        "count": 0, "rated_count": 0, "score": None, "positive_share": None,
        "pros": [], "cons": [], "mixed": [], "flags_pos": [], "flags_neg": [], "quotes": [],
    }
    items = []
    for r in reviews or []:
        text = clean_text(r.get("content", ""))
        if len(text) < 40:
            continue
        rating = (r.get("author_details") or {}).get("rating")
        items.append({
            "author": r.get("author") or (r.get("author_details") or {}).get("username") or "Anonim",
            "text": text,
            "rating": float(rating) if isinstance(rating, (int, float)) else None,
            "url": r.get("url"),
        })
    n = len(items)
    result["count"] = n
    if n == 0:
        return result

    aspect_votes = {key: [0, 0] for key, _, _ in ASPECTS}
    flag_counts: dict[str, int] = {}
    scores, weights = [], []
    review_tones = []

    for item in items:
        sentences = split_sentences(item["text"])
        low_text = item["text"].lower()
        total_pos = total_neg = 0.0
        per_aspect = {key: 0.0 for key, _, _ in ASPECTS}
        best_sentence, best_val = None, 0.0
        worst_sentence, worst_val = None, 0.0
        for s in sentences:
            pos, neg = sentence_sentiment(s)
            total_pos += pos
            total_neg += neg
            pol = _polarity(pos, neg)
            low = s.lower()
            for key, _, pattern in ASPECTS:
                if pattern.search(low):
                    per_aspect[key] += pol
            if 40 <= len(s) <= 260:
                if pol > best_val:
                    best_sentence, best_val = s, pol
                if pol < worst_val:
                    worst_sentence, worst_val = s, pol
        for key, val in per_aspect.items():
            if val > 0.15:
                aspect_votes[key][0] += 1
            elif val < -0.15:
                aspect_votes[key][1] += 1
        for key, _, pattern in FLAGS_POS + FLAGS_NEG:
            if pattern.search(low_text):
                flag_counts[key] = flag_counts.get(key, 0) + 1

        lex = _review_lexicon_score(total_pos, total_neg)
        if item["rating"] is not None:
            result["rated_count"] += 1
            score, weight = item["rating"], 1.0
        else:
            score, weight = lex, 0.6
        scores.append(score)
        weights.append(weight)
        review_tones.append((score, item, best_sentence, worst_sentence))

    result["score"] = round(sum(s * w for s, w in zip(scores, weights)) / sum(weights), 1)
    result["positive_share"] = round(100 * sum(1 for s in scores if s >= 6.5) / n)

    threshold = 1 if n <= 3 else 2
    for key, label, _ in ASPECTS:
        p, q = aspect_votes[key]
        if p >= threshold and p >= 2 * q:
            result["pros"].append({"key": key, "label": label, "count": p, "text": f"{label} övülüyor"})
        elif q >= threshold and q >= 2 * p:
            result["cons"].append({"key": key, "label": label, "count": q, "text": f"{label} eleştiriliyor"})
        elif p >= threshold and q >= threshold:
            result["mixed"].append({"key": key, "label": label, "count": p + q,
                                    "text": f"{label} konusunda görüşler bölünmüş"})
    for lst in ("pros", "cons", "mixed"):
        result[lst].sort(key=lambda x: -x["count"])

    flag_threshold = 1 if n <= 3 else max(2, math.ceil(0.12 * n))
    for key, text, _ in FLAGS_POS:
        if flag_counts.get(key, 0) >= flag_threshold:
            result["flags_pos"].append({"text": text, "count": flag_counts[key]})
    for key, text, _ in FLAGS_NEG:
        if flag_counts.get(key, 0) >= flag_threshold:
            result["flags_neg"].append({"text": text, "count": flag_counts[key]})

    # Alıntı: en beğenen ve (varsa) en eleştiren yorumdan birer cümle.
    ordered = sorted(review_tones, key=lambda x: x[0], reverse=True)
    top = ordered[0]
    if top[2]:
        result["quotes"].append(_quote(top[1], top[2], "olumlu"))
    low_review = ordered[-1]
    if len(ordered) > 1 and low_review[0] < 5.5 and low_review[3]:
        result["quotes"].append(_quote(low_review[1], low_review[3], "olumsuz"))
    return result


def _quote(item: dict, sentence: str, tone: str) -> dict:
    return {"author": item["author"], "text": sentence, "rating": item["rating"], "url": item["url"], "tone": tone}
