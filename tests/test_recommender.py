from werkzeug.datastructures import MultiDict

from neizlesem.recommender import SearchParams, resolve_terms, run_search, sort_results
from tests.fakes import HEIST, KEYWORDS, REVENGE


def params(**kw):
    md = MultiDict()
    for k, v in kw.items():
        for item in (v if isinstance(v, list) else [v]):
            md.add(k, item)
    return SearchParams.from_args(md)


def _run(services, p):
    return run_search(p, services["tmdb"], services["omdb"], services["store"], workers=4)


def test_params_validation():
    p = params(k=["intikam", "yok-boyle-tema", "t123"], x=["intikam", "soygun"], g=["28", "999"], puan="7", sirala="hack")
    assert p.include == ["intikam", "t123"]
    assert p.exclude == ["soygun"]          # hem olsun hem olmasın denirse "olsun" kazanır
    assert p.genres == [28]
    assert p.min_rating == "7" and p.sort == "uygun"


def test_resolve_concepts_to_keyword_ids(services):
    terms = resolve_terms(["intikam", "soygun", "t9001"], services["tmdb"])
    assert REVENGE in terms[0].ids
    assert HEIST in terms[1].ids
    assert terms[2].ids == [9001] and terms[2].label == "chess"


def test_movies_matching_all_themes_rank_first(services):
    res = _run(services, params(k=["intikam", "soygun"]))
    top = res["results"][0]
    assert top["match"]["pct"] == 100
    assert set(top["match"]["matched"]) == {"İntikam", "Soygun"}
    ids = [r["id"] for r in res["results"]]
    assert 1 in ids and 3 in ids
    # Tüm temaları tutanlar, tek tema tutanların önünde
    pcts = [r["match"]["pct"] for r in res["results"]]
    assert pcts.index(100) == 0
    assert all(r["match"]["terms_hit"] >= 1 for r in res["results"])


def test_excluded_theme_and_genre_are_removed(services):
    res = _run(services, params(k=["intikam", "soygun"], x=["hayalet"], xg=["27"]))
    ids = [r["id"] for r in res["results"]]
    assert 3 not in ids                     # hayaletli ve korku türündeki film elendi
    for r in res["results"]:
        assert "Korku" not in r["genres"]


def test_cards_have_ratings_and_pusula(services):
    res = _run(services, params(k=["intikam"]))
    card = next(r for r in res["results"] if r["id"] == 1)
    assert card["ratings"]["imdb"] is not None and card["ratings"]["imdb_source"] == "OMDb"
    assert card["ratings"]["rt"] is not None
    assert card["pusula"]["score"] is not None
    assert card["review_count"] >= 1


def test_imdb_dataset_takes_priority(services):
    store = services["store"]
    store.imdb_replace([("tt0000001", 9.4, 1_500_000)])
    res = _run(services, params(k=["intikam"], sirala="imdb"))
    card = next(r for r in res["results"] if r["id"] == 1)
    assert card["ratings"]["imdb"] == 9.4 and card["ratings"]["imdb_source"] == "IMDb veri seti"
    assert res["results"][0]["id"] == 1     # IMDb'ye göre sıralamada en üstte


def test_search_is_cached(services, fake_session):
    p = params(k=["intikam", "soygun"])
    _run(services, p)
    before = len(fake_session.calls)
    again = _run(services, params(k=["intikam", "soygun"], sirala="yeni"))
    assert len(fake_session.calls) == before  # ikinci arama tamamen önbellekten
    dates = [r["release_date"] for r in again["results"]]
    assert dates == sorted(dates, reverse=True)


def test_min_rating_filter(services):
    res = _run(services, params(g=["28"], puan="8"))
    for r in res["results"]:
        rating = r["ratings"]["imdb"] if r["ratings"]["imdb"] is not None else r["ratings"]["tmdb"]
        assert rating >= 8


def test_empty_search_returns_popular_good_films(services):
    res = _run(services, params())
    assert res["results"]
    assert all(r["match"]["pct"] is None for r in res["results"])


def test_sort_results_helper():
    rows = [{"rank": 0.5, "pusula": {"score": 9}, "ratings": {"imdb": 7}, "release_date": "2001", "popularity": 3},
            {"rank": 0.9, "pusula": {"score": 6}, "ratings": {"imdb": 8}, "release_date": "2020", "popularity": 1}]
    assert sort_results(rows, "puan")[0]["pusula"]["score"] == 9
    assert sort_results(rows, "uygun")[0]["rank"] == 0.9
    assert sort_results(rows, "yeni")[0]["release_date"] == "2020"
