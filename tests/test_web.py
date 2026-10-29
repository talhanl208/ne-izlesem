import gzip

from neizlesem import create_app
from neizlesem.imdb_dataset import import_file
from tests.fakes import FakeSession


def test_index_renders_themes(client):
    html = client.get("/").get_data(as_text=True)
    assert "Bu akşam ne izleyelim?" in html
    assert 'data-key="intikam"' in html and "Ruh haline göre başla" in html
    assert "Netflix" in html  # platform filtresi


def test_index_prefills_selection(client):
    html = client.get("/?k=intikam&x=hayalet&k=t9001").get_data(as_text=True)
    assert 'data-key="intikam" data-label="İntikam"\n        data-state="1"' in html
    assert 'data-key="hayalet" data-label="Hayalet &amp; perili ev"\n        data-state="2"' in html
    assert "chess" in html


def test_results_page(client):
    resp = client.get("/sonuclar?k=intikam&k=soygun&g=28")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "İntikam Soygunu" in html
    assert "Uygunluk %100" in html
    assert "Sürpriz yap" in html


def test_results_empty_state(client):
    html = client.get("/sonuclar?k=intikam&dil=hi&donem=-1989").get_data(as_text=True)
    assert "Bu kombinasyona uyan film çıkmadı" in html


def test_detail_page(client):
    resp = client.get("/film/1?k=intikam&k=zaman-yolculugu")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "İntikam Soygunu" in html
    assert "Kısaca" in html and "Pusula Puanı" in html
    assert "Seçtiğin temalardan intikam bu filmde var." in html
    assert "Zaman yolculuğu ise filmde belirgin değil." in html
    assert "Oyuncu 1" in html and "Ayrıca:" in html
    assert "Nerede izlenir?" in html and "Netflix" in html
    assert "Övülenler" in html
    assert "Won 1 Oscar" in html
    assert 'data-yt="abcDEF12345"' in html


def test_detail_404(client):
    assert client.get("/film/999999").status_code == 404


def test_surprise_redirects_to_a_film(client):
    resp = client.get("/surpriz?k=intikam")
    assert resp.status_code == 302
    assert "/film/" in resp.headers["Location"] and "k=intikam" in resp.headers["Location"]


def test_keyword_suggest(client):
    data = client.get("/api/anahtar-kelime?q=intik").get_json()
    assert data[0]["key"] == "intikam"
    data = client.get("/api/anahtar-kelime?q=chess").get_json()
    assert any(d["key"] == "t9001" for d in data)


def test_movie_search(client):
    html = client.get("/ara?q=intikam").get_data(as_text=True)
    assert "İntikam Soygunu" in html


def test_missing_api_key_shows_setup(tmp_path):
    app = create_app({"TESTING": True, "TMDB_API_KEY": "", "DATABASE_PATH": str(tmp_path / "x.db")},
                     session=FakeSession())
    c = app.test_client()
    assert c.get("/").status_code == 200
    resp = c.get("/sonuclar?k=intikam")
    assert resp.status_code == 503
    assert "TMDB anahtarını ekleyelim" in resp.get_data(as_text=True)


def test_invalid_api_key_shows_error(tmp_path):
    app = create_app({"TESTING": True, "TMDB_API_KEY": "yanlis", "DATABASE_PATH": str(tmp_path / "y.db")},
                     session=FakeSession(fail_auth=True))
    resp = app.test_client().get("/sonuclar?k=intikam")
    assert resp.status_code == 502
    assert "geçersiz" in resp.get_data(as_text=True)


def test_about_page(client):
    assert "Bayes" in client.get("/nasil-calisir").get_data(as_text=True)


def test_imdb_dataset_import(tmp_path, services):
    path = tmp_path / "title.ratings.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("tconst\taverageRating\tnumVotes\n")
        fh.write("tt0000001\t8.6\t2500000\n")
        fh.write("tt0000002\t7.1\t50\n")       # az oylu: alınmaz
        fh.write("bozuk satır\n")
    n = import_file(services["store"], str(path), min_votes=100)
    assert n == 1
    assert services["store"].imdb_get("tt0000001") == {"rating": 8.6, "votes": 2500000}
    assert services["store"].imdb_get("tt0000002") is None
    assert services["store"].meta_get("imdb_updated")


def test_cli_imdb_update_from_file(app, tmp_path):
    path = tmp_path / "r.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("tconst\taverageRating\tnumVotes\ntt0000005\t7.7\t9000\n")
    result = app.test_cli_runner().invoke(args=["imdb-guncelle", "--dosya", str(path)])
    assert "1 yapımın IMDb puanı kaydedildi" in result.output


def test_cli_resolve_concepts(app):
    result = app.test_cli_runner().invoke(args=["temalari-esle"])
    assert "Tüm temalar eşleşti." in result.output


def test_security_headers(client):
    resp = client.get("/")
    csp = resp.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "strict-origin" in resp.headers["Referrer-Policy"]


def test_api_key_never_reaches_the_browser(client):
    for url in ("/", "/sonuclar?k=intikam", "/film/1", "/api/anahtar-kelime?q=chess"):
        assert "test-anahtar" not in client.get(url).get_data(as_text=True)


def test_no_inline_scripts(client):
    import re
    for url in ("/", "/sonuclar?k=intikam", "/film/1"):
        html = client.get(url).get_data(as_text=True)
        assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>", html)
        assert "javascript:" not in html


def test_rate_limit(app):
    from neizlesem.security import LIMITS
    c = app.test_client()
    limit = LIMITS["main.keyword_suggest"][0]
    codes = [c.get("/api/anahtar-kelime?q=in").status_code for _ in range(limit + 1)]
    assert codes[-1] == 429 and codes[0] == 200


def test_404_page(client):
    resp = client.get("/boyle-bir-sayfa-yok")
    assert resp.status_code == 404
    assert "Bu salon boş" in resp.get_data(as_text=True)


def test_tmdb_logo_used_when_present(app, client):
    from pathlib import Path
    logo = Path(app.static_folder) / "img" / "tmdb-logo.svg"
    existed = logo.exists()
    if not existed:
        logo.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    try:
        assert "img/tmdb-logo.svg" in client.get("/").get_data(as_text=True)
    finally:
        if not existed:
            logo.unlink()


def test_imdb_attribution_on_every_page(client):
    required = "Information courtesy of IMDb (<a href=\"https://www.imdb.com\""
    for url in ("/", "/sonuclar?k=intikam", "/film/1", "/nasil-calisir"):
        html = client.get(url).get_data(as_text=True)
        assert required in html and "Used with permission." in html
        assert "bu ürün tmdb api'sini kullanır" in html.lower()


def test_site_is_hidden_from_search_engines(client):
    resp = client.get("/")
    assert resp.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert '<meta name="robots" content="noindex, nofollow">' in resp.get_data(as_text=True)
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and "Disallow: /" in robots.get_data(as_text=True)
