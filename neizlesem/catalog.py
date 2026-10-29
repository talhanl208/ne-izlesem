"""Türkçe tema kataloğu, türler, ruh hali hazır ayarları.

Her tema, TMDB'deki bir veya birden fazla İngilizce anahtar kelimeye bağlanır
(eş anlamlılar isabeti artırır). Kimlikler çalışma anında TMDB'den çözülür ve
önbelleğe alınır; bu yüzden kimlikleri koda gömmüyoruz.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    slug: str
    label: str
    emoji: str
    group: str
    en: tuple[str, ...]


GROUPS: list[tuple[str, str]] = [
    ("hikaye", "Hikâye & olay"),
    ("duygu", "Duygu & ilişkiler"),
    ("bilimkurgu", "Bilim kurgu & fantastik"),
    ("gerilim", "Gerilim & korku"),
    ("dunya", "Dünya & ortam"),
]

_C = Concept
CONCEPTS: dict[str, Concept] = {c.slug: c for c in [
    # Hikâye & olay
    _C("intikam", "İntikam", "🗡️", "hikaye", ("revenge", "vengeance")),
    _C("soygun", "Soygun", "💰", "hikaye", ("heist", "robbery", "bank robbery")),
    _C("kacis", "Kaçış / firar", "🏃", "hikaye", ("prison escape", "escape")),
    _C("hayatta-kalma", "Hayatta kalma", "🔥", "hikaye", ("survival",)),
    _C("kacirilma", "Kaçırılma & rehine", "🎯", "hikaye", ("kidnapping", "hostage")),
    _C("ihanet", "İhanet", "🐍", "hikaye", ("betrayal", "double cross")),
    _C("komplo", "Komplo", "🕸️", "hikaye", ("conspiracy",)),
    _C("gizli-gorev", "Gizli görev", "🕶️", "hikaye", ("undercover", "undercover cop")),
    _C("kiralik-katil", "Kiralık katil", "🔫", "hikaye", ("hitman", "assassin", "contract killer")),
    _C("seri-katil", "Seri katil", "🔪", "hikaye", ("serial killer",)),
    _C("dedektif", "Dedektif & cinayet", "🔍", "hikaye", ("detective", "murder investigation", "whodunit")),
    _C("mahkeme", "Mahkeme", "⚖️", "hikaye", ("courtroom", "trial", "lawyer")),
    _C("yolculuk", "Yol hikâyesi", "🚗", "hikaye", ("road trip", "road movie")),
    _C("gercek-hikaye", "Gerçek hikâye", "📰", "hikaye", ("based on true story", "biography")),
    _C("kitap", "Kitap uyarlaması", "📚", "hikaye", ("based on novel or book",)),
    _C("ters-kose", "Ters köşe final", "🌀", "hikaye", ("twist ending", "plot twist")),
    _C("underdog", "Ezilenin zaferi", "🏆", "hikaye", ("underdog",)),
    _C("ikinci-sans", "İkinci şans", "🌱", "hikaye", ("second chance", "redemption")),
    # Duygu & ilişkiler
    _C("dostluk", "Dostluk", "🤝", "duygu", ("friendship", "best friend")),
    _C("ilk-ask", "İlk aşk", "💌", "duygu", ("first love",)),
    _C("imkansiz-ask", "İmkânsız aşk", "💔", "duygu", ("forbidden love", "star crossed lovers")),
    _C("aile", "Aile bağları", "🏠", "duygu", ("family relationships", "dysfunctional family")),
    _C("baba-cocuk", "Baba-çocuk", "👨‍👧", "duygu", ("father son relationship", "father daughter relationship")),
    _C("anne-cocuk", "Anne-çocuk", "👩‍👦", "duygu", ("mother son relationship", "mother daughter relationship")),
    _C("buyume", "Büyüme hikâyesi", "🎒", "duygu", ("coming of age",)),
    _C("yas", "Kayıp & yas", "🕯️", "duygu", ("grief", "loss of loved one")),
    _C("yalnizlik", "Yalnızlık", "🌧️", "duygu", ("loneliness",)),
    _C("fedakarlik", "Fedakârlık", "🫶", "duygu", ("sacrifice", "self sacrifice")),
    # Bilim kurgu & fantastik
    _C("zaman-yolculugu", "Zaman yolculuğu", "⏳", "bilimkurgu", ("time travel",)),
    _C("zaman-dongusu", "Zaman döngüsü", "🔁", "bilimkurgu", ("time loop",)),
    _C("paralel-evren", "Paralel evren", "🪐", "bilimkurgu", ("parallel world", "multiverse", "alternate reality")),
    _C("yapay-zeka", "Yapay zekâ", "🤖", "bilimkurgu", ("artificial intelligence (a.i.)", "artificial intelligence", "android")),
    _C("uzay", "Uzay", "🚀", "bilimkurgu", ("space travel", "outer space", "astronaut")),
    _C("uzayli", "Uzaylı", "👽", "bilimkurgu", ("alien", "alien invasion", "extraterrestrial")),
    _C("distopya", "Distopya", "🏙️", "bilimkurgu", ("dystopia",)),
    _C("kiyamet", "Kıyamet sonrası", "☢️", "bilimkurgu", ("post-apocalyptic future", "apocalypse")),
    _C("simulasyon", "Simülasyon", "🧩", "bilimkurgu", ("simulated reality", "virtual reality")),
    _C("super-kahraman", "Süper kahraman", "🦸", "bilimkurgu", ("superhero",)),
    _C("buyu", "Büyü", "🪄", "bilimkurgu", ("magic", "wizard", "sorcery")),
    _C("ejderha", "Ejderha", "🐉", "bilimkurgu", ("dragon",)),
    _C("hafiza", "Hafıza & rüya", "🧠", "bilimkurgu", ("amnesia", "memory loss", "dream")),
    # Gerilim & korku
    _C("psikolojik", "Psikolojik gerilim", "🫥", "gerilim", ("psychological thriller",)),
    _C("hayalet", "Hayalet & perili ev", "👻", "gerilim", ("ghost", "haunted house")),
    _C("seytan", "Şeytan çıkarma", "😈", "gerilim", ("exorcism", "demonic possession", "possession")),
    _C("zombi", "Zombi", "🧟", "gerilim", ("zombie",)),
    _C("vampir", "Vampir", "🧛", "gerilim", ("vampire",)),
    _C("canavar", "Canavar", "🦖", "gerilim", ("monster", "kaiju", "creature")),
    _C("tek-mekan", "Tek mekân", "🚪", "gerilim", ("single location",)),
    _C("ev-istilasi", "Ev istilası", "🏚️", "gerilim", ("home invasion",)),
    _C("felaket", "Felaket", "🌋", "gerilim", ("disaster", "natural disaster")),
    _C("salgin", "Salgın", "🦠", "gerilim", ("pandemic", "epidemic", "virus")),
    # Dünya & ortam
    _C("savas", "Savaş", "🎖️", "dunya", ("war", "world war ii", "world war i", "vietnam war")),
    _C("mafya", "Mafya & gangster", "🎩", "dunya", ("mafia", "gangster", "organized crime")),
    _C("kartel", "Uyuşturucu kartelleri", "💊", "dunya", ("drug cartel", "drug trafficking", "drug dealer")),
    _C("casus", "Casusluk", "🕵️", "dunya", ("spy", "espionage", "secret agent")),
    _C("hacker", "Hacker & siber", "💻", "dunya", ("hacker", "hacking", "cyberpunk")),
    _C("dovus", "Dövüş sanatları", "🥋", "dunya", ("martial arts", "kung fu")),
    _C("araba", "Kovalamaca & yarış", "🏎️", "dunya", ("car chase", "car race", "street racing")),
    _C("spor", "Spor", "⚽", "dunya", ("sports", "boxing", "football (soccer)", "basketball")),
    _C("muzik", "Müzik & müzisyen", "🎸", "dunya", ("musician", "rock band", "singer")),
    _C("okul", "Okul & kampüs", "🏫", "dunya", ("high school", "college", "boarding school")),
    _C("yemek", "Yemek & şef", "🍝", "dunya", ("cooking", "chef", "restaurant")),
    _C("tarih", "Antik çağ & Orta Çağ", "🏛️", "dunya", ("ancient rome", "medieval", "ancient greece")),
    _C("korsan", "Korsanlar", "🏴‍☠️", "dunya", ("pirate",)),
    _C("ada", "Issız ada", "🏝️", "dunya", ("deserted island", "stranded", "island")),
    _C("yilbasi", "Yılbaşı", "🎄", "dunya", ("christmas",)),
    _C("turkiye", "Türkiye'de geçen", "🇹🇷", "dunya", ("istanbul, turkey", "turkey")),
    _C("kara-mizah", "Kara mizah", "🃏", "dunya", ("dark comedy", "black comedy")),
    _C("hayvan", "Hayvan dostlar", "🐾", "dunya", ("dog", "cat", "animal")),
]}

POPULAR = [
    "intikam", "soygun", "ters-kose", "zaman-yolculugu", "psikolojik", "gercek-hikaye",
    "hayatta-kalma", "seri-katil", "dostluk", "uzay", "mafya", "buyume",
]

# TMDB tür kimlikleri (sabittir).
GENRES: dict[int, str] = {
    28: "Aksiyon", 12: "Macera", 16: "Animasyon", 35: "Komedi", 80: "Suç",
    99: "Belgesel", 18: "Dram", 10751: "Aile", 14: "Fantastik", 36: "Tarih",
    27: "Korku", 10402: "Müzik", 9648: "Gizem", 10749: "Romantik",
    878: "Bilim kurgu", 53: "Gerilim", 10752: "Savaş", 37: "Western",
}

# Ruh hali kartları yalnızca bir başlangıç noktasıdır: gizli puan filtresi koymazlar ve
# temaları sadece tanımın kendisi olduğunda ekler (ör. "Beyin yakan" = ters köşe/zaman oyunları).
MOODS: list[dict] = [
    {"slug": "kafa-dagit", "emoji": "😄", "label": "Kafa dağıtmalık",
     "desc": "Hafif, eğlenceli, düşündürmeyen", "include": [], "genres": [35, 12], "xgenres": [27]},
    {"slug": "adrenalin", "emoji": "🔥", "label": "Adrenalin",
     "desc": "Bol aksiyon, nefes kesen tempo", "include": [], "genres": [28], "xgenres": []},
    {"slug": "beyin-yakan", "emoji": "🤯", "label": "Beyin yakan",
     "desc": "Ters köşe, zaman oyunları", "include": ["ters-kose", "zaman-dongusu", "paralel-evren"], "genres": [], "xgenres": []},
    {"slug": "gerilim-gecesi", "emoji": "😱", "label": "Gerilim gecesi",
     "desc": "Diken üstünde oturtan gerilim ve gizem", "include": [], "genres": [53, 9648], "xgenres": []},
    {"slug": "aglamalik", "emoji": "🥲", "label": "İçimi dökeyim",
     "desc": "Duygusal, yürek burkan", "include": ["yas", "fedakarlik"], "genres": [18], "xgenres": [27]},
    {"slug": "romantik", "emoji": "💕", "label": "Romantik akşam",
     "desc": "Sevgiliyle izlemelik", "include": [], "genres": [10749], "xgenres": [27]},
    {"slug": "ilham", "emoji": "✨", "label": "İlham verici",
     "desc": "Gerçek hikâyeler, ezilenin zaferi", "include": ["gercek-hikaye", "underdog"], "genres": [], "xgenres": []},
    {"slug": "ailecek", "emoji": "🍿", "label": "Ailecek",
     "desc": "Her yaşa uygun", "include": [], "genres": [10751, 16], "xgenres": [27, 53]},
]

PERIODS: list[tuple[str, str]] = [
    ("", "Fark etmez"), ("2020-", "2020 ve sonrası"), ("son10", "Son 10 yıl"),
    ("2010-2019", "2010'lar"), ("2000-2009", "2000'ler"), ("1990-1999", "90'lar"), ("-1989", "1990 öncesi"),
]
RATINGS: list[tuple[str, str]] = [("", "Fark etmez"), ("6", "6+"), ("6.5", "6.5+"), ("7", "7+"), ("7.5", "7.5+"), ("8", "8+")]
RUNTIMES: list[tuple[str, str]] = [("", "Fark etmez"), ("90", "≤ 1,5 saat"), ("120", "≤ 2 saat"), ("150", "≤ 2,5 saat")]
LANGUAGES: list[tuple[str, str]] = [
    ("", "Fark etmez"), ("tr", "Türk filmleri"), ("en", "İngilizce"), ("ko", "Kore"),
    ("ja", "Japon"), ("fr", "Fransız"), ("es", "İspanyol"), ("it", "İtalyan"), ("hi", "Hint"),
]
SORTS: list[tuple[str, str]] = [
    ("uygun", "En uygun"), ("puan", "Pusula puanı"), ("imdb", "IMDb puanı"),
    ("yeni", "En yeni"), ("populer", "En popüler"),
]

# Platform filtresinde öne çıkarılacak Türkiye servisleri (TMDB'deki adlarıyla).
PREFERRED_PROVIDERS = [
    "netflix", "amazon prime video", "disney plus", "hbo max", "max", "blutv", "mubi",
    "apple tv plus", "apple tv+", "tod", "exxen", "tabii", "gain", "puhutv",
]

# Detay sayfasında TMDB anahtar kelimelerini Türkçeleştirmek için ek sözlük.
_EXTRA_TRANSLATIONS = {
    "based on comic": "Çizgi roman uyarlaması", "sequel": "Devam filmi", "remake": "Yeniden çevrim",
    "duringcreditsstinger": "Jenerik arasında sahne var", "aftercreditsstinger": "Jenerik sonrası sahne var",
    "murder": "Cinayet", "police": "Polis", "love": "Aşk", "family": "Aile", "suspense": "Gerilim",
    "violence": "Şiddet", "satire": "Hiciv", "parody": "Parodi", "musical": "Müzikal", "anime": "Anime",
    "film noir": "Kara film", "neo-noir": "Neo-noir", "found footage": "Kamera kaydı (found footage)",
    "nonlinear timeline": "Doğrusal olmayan anlatım", "flashback": "Geriye dönüşler",
    "anti hero": "Anti-kahraman", "teenager": "Gençlik", "wedding": "Düğün", "small town": "Küçük kasaba",
    "prison": "Hapishane", "drugs": "Uyuşturucu", "corruption": "Yolsuzluk", "investigation": "Soruşturma",
    "terrorism": "Terörizm", "robot": "Robot", "future": "Gelecek", "space": "Uzay",
    "new york city": "New York", "los angeles, california": "Los Angeles", "london, england": "Londra",
    "paris, france": "Paris", "tokyo, japan": "Tokyo", "dark fantasy": "Karanlık fantastik",
    "post-apocalyptic future": "Kıyamet sonrası", "mystery": "Gizem", "thriller": "Gerilim",
    "biography": "Biyografi", "historical": "Tarihî", "period drama": "Dönem draması",
    "female protagonist": "Kadın başkarakter", "friends": "Arkadaşlar", "high school": "Lise",
}


def keyword_translation(name: str) -> str | None:
    key = (name or "").strip().lower()
    if key in _EXTRA_TRANSLATIONS:
        return _EXTRA_TRANSLATIONS[key]
    for c in CONCEPTS.values():
        if key in c.en:
            return c.label
    return None


def grouped_concepts() -> list[tuple[str, str, list[Concept]]]:
    return [(g, title, [c for c in CONCEPTS.values() if c.group == g]) for g, title in GROUPS]
