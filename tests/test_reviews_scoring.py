from neizlesem.reviews import analyze_reviews, sentence_sentiment
from neizlesem.scoring import bayes, pusula_score
from neizlesem.narrative import build_story
from neizlesem.textutil import join_tr, runtime_text, votes_text, lower_tr


def test_negation_flips_sentiment():
    pos, neg = sentence_sentiment("The movie was good.")
    assert pos > neg
    pos, neg = sentence_sentiment("The movie was not good at all.")
    assert neg > pos


def test_but_clause_weighs_more():
    pos, neg = sentence_sentiment("The visuals are great but the story is boring and weak.")
    assert neg > pos


def test_review_analysis_finds_pros_and_cons():
    reviews = [
        {"author": "a", "content": "The acting is brilliant and the cast is amazing. Stunning cinematography.", "author_details": {"rating": 9}},
        {"author": "b", "content": "Great performances by the whole cast. The visuals are gorgeous and beautiful.", "author_details": {}},
        {"author": "c", "content": "The pacing is slow and it drags. The plot is predictable and the script is weak.", "author_details": {"rating": 4}},
        {"author": "d", "content": "Terrible pacing, way too slow. Predictable story with boring dialogue throughout.", "author_details": {}},
    ]
    r = analyze_reviews(reviews)
    assert r["count"] == 4 and r["rated_count"] == 2
    pro_keys = {p["key"] for p in r["pros"]}
    con_keys = {c["key"] for c in r["cons"]}
    assert "oyunculuk" in pro_keys and "gorsel" in pro_keys
    assert "tempo" in con_keys
    assert any("Tahmin edilebilir" in f["text"] for f in r["flags_neg"])
    assert 1 <= r["score"] <= 10
    assert r["quotes"] and r["quotes"][0]["tone"] == "olumlu"


def test_empty_reviews():
    r = analyze_reviews([])
    assert r["count"] == 0 and r["score"] is None


def test_bayes_pulls_low_vote_counts_to_mean():
    few = bayes(9.5, 10, m=3000, c=6.4)
    many = bayes(9.0, 2_000_000, m=3000, c=6.4)
    assert few < 7 and many > 8.9


def test_pusula_renormalizes_missing_sources():
    only_imdb = pusula_score(imdb_rating=8.0, imdb_votes=500_000)
    assert only_imdb["score"] is not None and abs(only_imdb["score"] - 8.0) < 0.1
    assert [c["share"] for c in only_imdb["components"]] == [100]
    full = pusula_score(imdb_rating=8.0, imdb_votes=500_000, tmdb_avg=7.8, tmdb_votes=20000, rt=90,
                        metacritic=80, review_summary={"score": 8.5, "count": 10, "positive_share": 80})
    assert sum(c["share"] for c in full["components"]) in (99, 100, 101)
    assert full["confidence"] == "Yüksek"
    assert pusula_score()["score"] is None


def test_turkish_helpers():
    assert join_tr(["a", "b", "c"]) == "a, b ve c"
    assert runtime_text(148) == "2 sa 28 dk"
    assert votes_text(2_600_000) == "2,6 milyon"
    assert votes_text(45_200) == "45,2 bin"
    assert lower_tr("İntikam") == "intikam"


def test_story_has_no_awkward_suffixes():
    d = {"title": "Örnek", "year": "2010", "runtime_text": "2 sa", "genres": ["Aksiyon", "Bilim kurgu"],
         "directors": ["A Kişi"], "cast": [{"name": "X"}, {"name": "Y"}], "matched": ["İntikam"], "missed": [],
         "keywords": [], "reviews": {"count": 0}, "pusula": {"score": 8.0}, "verdict": "İzle.",
         "original_language": "en", "language": "İngilizce"}
    story = build_story(d)
    assert story[0].startswith("2010 yapımı Örnek, 2 sa süren bir aksiyon ve bilim kurgu filmi.")
    assert "Seçtiğin temalardan intikam bu filmde var." in story[1]
    assert story[-1] == "Pusula Puanı 8,0/10: İzle."
