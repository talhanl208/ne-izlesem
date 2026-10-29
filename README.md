# Ne İzlesem? 🎬

Canın film izlemek istiyor ama aklına bir şey gelmiyor mu? Tür seçmek yetmiyor; bazen “içinde **intikam** geçen bir **soygun** filmi, ama **korku olmasın**” istersin. Ne İzlesem? tam bunu yapıyor:

- **Tema seçerek arama** — 70'e yakın Türkçe tema (intikam, soygun, zaman yolculuğu, ters köşe final, seri katil…) ve TMDB'deki binlerce etiket arasında serbest arama.
- **Çoklu seçim + hariç tutma** — temaya bir dokunuş “olsun”, iki dokunuş “olmasın”. Türler için de aynısı.
- **Uygunluk yüzdesi** — her film, seçtiğin temaların kaçını gerçekten taşıyor? Hepsini tutturanlar öne çıkar.
- **Ruh hali kısayolları** — “Beyin yakan”, “Gerilim gecesi”, “Romantik akşam”…
- **İnce ayar** — dönem, en az puan, en fazla süre, dil, Türkiye'deki platformlar (Netflix, Prime…), az bilinen cevherler.
- **Orijinal IMDb puanı** + Rotten Tomatoes, Metacritic ve TMDB puanları.
- **Pusula Puanı** — tüm kaynakları ve izleyici yorumlarını birleştiren, dökümüyle şeffaf kendi puanımız.
- **Yorum analizi** — izleyici yorumlarından “övülenler / eleştirilenler” (oyunculuk, senaryo, tempo, final…).
- **Film sayfası** — sohbet havasında Türkçe özet, konu, fragman, nerede izlenir, oyuncular ve bilinen diğer filmleri, temalar, benzer filmler.
- **Sürpriz yap** — en uygun filmlerden birini rastgele açar.
- **Gala gecesi tasarımı** — sinema bileti şeklinde kartlar; seçince zımbalanan temalar, “Film bul” deyince koparılan bilet koçanı, kapanan kadife perde ve film geri sayımı, sonuçlarda açılan perde ve sırayla gelen biletler, afişten film sayfasına akan geçiş. Hareket azaltma ayarı açık cihazlarda animasyonlar kendiliğinden kapanır.
- Telefonda ana ekrana eklenebilir.

## Veri nereden geliyor?

| Kaynak | Ne için | Neden |
|---|---|---|
| **TMDB API** (ücretsiz) | Temalar/etiketler, filmler, Türkçe özet, oyuncular, yorumlar, fragman, platformlar | IMDb'nin herkese açık bir API'si yok. TMDB filmleri en ayrıntılı şekilde etiketleyen ücretsiz kaynak ve Türkçe içerik veriyor. |
| **IMDb resmi veri seti** | Orijinal IMDb puanı ve oy sayısı | IMDb'nin kişisel/ticari olmayan kullanım için her gün yayımladığı `title.ratings.tsv.gz`. Limit yok. |
| **OMDb API** (isteğe bağlı) | Rotten Tomatoes + Metacritic | Ücretsiz anahtar, günde 1000 istek. Yoksa uygulama bunlarsız çalışır. |

## Kurulum

```bash
git clone https://github.com/<kullanici-adin>/ne-izlesem.git
cd ne-izlesem
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
```

1. [themoviedb.org](https://www.themoviedb.org/signup) üzerinde hesap aç → Ayarlar → API → geliştirici anahtarı iste (kişisel kullanım). **API Read Access Token** değerini `.env` içindeki `TMDB_API_KEY` satırına yapıştır (v3 “API Key” de çalışır ama token adres çubuğunda görünmediği için daha güvenli). `SECRET_KEY` için de rastgele bir değer üret: `python -c "import secrets; print(secrets.token_hex(32))"`.
2. (İsteğe bağlı) [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx) üzerinden ücretsiz anahtar al, `OMDB_API_KEY` satırına yaz.
3. IMDb puanlarını indir (yaklaşık 1–2 dakika):
   ```bash
   flask --app wsgi imdb-guncelle
   ```
4. Temaların TMDB'de karşılığını bulduğunu kontrol et:
   ```bash
   flask --app wsgi temalari-esle
   ```
   Eşleşmeyen bir tema çıkarsa `neizlesem/catalog.py` içinde o temanın İngilizce karşılıklarına başka bir eş anlamlı ekleyebilirsin.
5. **TMDB logosunu ekle** (TMDB'nin ücretsiz kullanım şartı): [themoviedb.org/about/logos-attribution](https://www.themoviedb.org/about/logos-attribution) sayfasından onaylı logolardan birini (ör. kısa mavi SVG) indir ve `neizlesem/static/img/tmdb-logo.svg` adıyla kaydet. Site onu kendiliğinden alt bilgide ve “Nasıl çalışır?” sayfasında gösterir. Logo yokken yerine “The Movie Database (TMDB)” yazısı çıkar.
6. Çalıştır:
   ```bash
   flask --app wsgi run
   ```
   Tarayıcıda http://127.0.0.1:5000

> İlk aramalar birkaç saniye sürebilir (yüzlerce film taranıyor). Her şey SQLite'ta önbelleğe alındığı için sonraki aramalar çok hızlı.

## PythonAnywhere'de yayınlama (ücretsiz hesap)

Önce ücretsiz hesabın kısıtlarını bil:

- **Bir hesapta yalnızca 1 web uygulaması** çalışır. Lezzet Pusulası zaten o hesaptaysa bu siteyi ayrı bir ücretsiz hesapla yayınlaman gerekir (adres `<yeni-kullanici>.pythonanywhere.com` olur) ya da ücretli plana geçersin.
- **Kullanılmayan web uygulaması 1 ay sonra durur.** Ayda bir giriş yapıp Web sekmesindeki süre uzatma düğmesine bas.
- **Ocak 2026'dan sonra açılan ücretsiz hesaplarda zamanlanmış görev (Tasks) yok.** IMDb puanlarını ayda bir konsoldan elle güncellemen yeterli (puanlar yavaş değişir). Eski hesabında Tasks sekmesi varsa günlük görev ekleyebilirsin.
- Dışarıya yalnızca izinli sitelere istek atılabiliyor: `api.themoviedb.org` ve `datasets.imdbws.com` listede, `omdbapi.com` değil. Yani orada Rotten Tomatoes/Metacritic görünmez (hata da vermez). Görseller ve yazı tipleri ziyaretçinin tarayıcısından yüklendiği için etkilenmez.

Kurulum:

1. Bash konsolunda:
   ```bash
   git clone https://github.com/<kullanici-adin>/ne-izlesem.git
   mkvirtualenv ne-izlesem --python=python3.11
   cd ne-izlesem && pip install -r requirements.txt
   cp .env.example .env && nano .env      # TMDB_API_KEY, SECRET_KEY yaz; TRUST_PROXY=1 yap
   flask --app wsgi imdb-guncelle
   ```
2. **Web** sekmesi → Add a new web app → Manual configuration → Python 3.11.
3. Virtualenv yolu: `/home/<kullanici-adin>/.virtualenvs/ne-izlesem`
4. WSGI dosyasının içeriğini şununla değiştir:
   ```python
   import sys
   path = "/home/<kullanici-adin>/ne-izlesem"
   if path not in sys.path:
       sys.path.insert(0, path)
   from wsgi import app as application
   ```
5. Static files: URL `/static/` → Directory `/home/<kullanici-adin>/ne-izlesem/neizlesem/static`
6. Web sekmesinde **Force HTTPS** seçeneğini aç ve Reload'a bas.
7. IMDb puanlarını güncellemek için (ayda bir):
   ```bash
   cd ~/ne-izlesem && workon ne-izlesem && flask --app wsgi imdb-guncelle
   ```

## Maliyet

Kişisel ve ticari olmayan kullanımda hiçbir ücret çıkmaz: TMDB, IMDb veri seti, OMDb'nin ücretsiz anahtarı ve PythonAnywhere ücretsiz hesabı yeterli. Yapay zekâ API'si kullanılmıyor; yorum analizi kural tabanlı. Siteye reklam koyar ya da para kazanmaya başlarsan TMDB ticari lisans ister.

## Güvenlik

- API anahtarları yalnızca sunucuda, `.env` dosyasında durur; tarayıcıya hiç gönderilmez (testlerle kontrol ediliyor). `.env` ve veritabanı `.gitignore` içinde.
- Sıkı **Content-Security-Policy**: yalnızca kendi betiklerimiz çalışır, satır içi betik yok; görseller sadece TMDB/YouTube'dan, çerçeve sadece YouTube'un çerezsiz alanından.
- Tıklama tuzağı (`X-Frame-Options`), MIME koklama ve gereksiz tarayıcı izinleri kapalı; HTTPS'te HSTS açık.
- **İstek sınırlama:** aynı IP'den dakikada 30 arama. Biri sayfayı durmadan yenileyip API kotanı tüketemez.
- Tüm kullanıcı girdileri doğrulanır (izinli tema/tür/filtre değerleri, uzunluk sınırları), sayfadaki her metin otomatik kaçışlanır.
- Hata sayfalarında iç ayrıntı gösterilmez; hata ayıklama modu yalnızca `FLASK_DEBUG=1` ile açılır.
- IMDb, Rotten Tomatoes ve Metacritic logoları kullanılmaz; adları yalnızca puanın kaynağını belirtmek için yazıyla geçer. Platform logoları TMDB/JustWatch'tan kaynak belirtilerek gösterilir.

## Pusula Puanı nasıl hesaplanıyor?

| Kaynak | Ağırlık |
|---|---|
| IMDb puanı (Bayes düzeltmeli) | %35 |
| İzleyici yorum analizi | %25 |
| TMDB puanı (Bayes düzeltmeli) | %15 |
| Rotten Tomatoes | %15 |
| Metacritic | %10 |

- **Bayes düzeltmesi:** 3 kişinin verdiği 9,5 ile 2 milyon kişinin verdiği 9,0 aynı değildir. Oy sayısı azaldıkça puan genel ortalamaya çekilir (IMDb Top 250'nin de kullandığı yöntem).
- Eksik kaynakların ağırlığı diğerlerine dağıtılır; yorum sayısı azsa yorumların ağırlığı da düşer.
- **“En uygun” sıralama** = %60 uygunluk yüzdesi + %40 Pusula Puanı.

## Öneri motoru nasıl çalışıyor?

1. Seçilen Türkçe temalar TMDB etiket kimliklerine çevrilir (her tema birkaç eş anlamlı etikete bağlı).
2. TMDB *discover* ile aday toplanır: hepsini içerenler (VE), herhangi birini içerenler (VEYA), en yüksek puanlılar ve her tema için ayrı en iyiler.
3. Adayların gerçek etiketleri çekilip kaç temayı tuttuğu hesaplanır; “olmasın” denenler elenir.
4. En iyi adaylar IMDb puanı, eleştirmen puanları ve yorum analiziyle zenginleştirilir.
5. Seçtiğin ölçüte göre sıralanır. Sonuçlar 6 saat önbellekte kalır.

Yorum analizi kural tabanlıdır (olumlu/olumsuz kelime sözlüğü, olumsuzlama “not good”, pekiştirme “very”, “but” sonrası vurgu); hiçbir yapay zekâ servisine veri gönderilmez.

## Proje yapısı

```
ne-izlesem/
├── wsgi.py                  # giriş noktası
├── neizlesem/
│   ├── __init__.py          # uygulama fabrikası + CLI komutları
│   ├── config.py            # .env ayarları
│   ├── catalog.py           # Türkçe temalar, türler, ruh halleri
│   ├── tmdb.py              # TMDB istemcisi (önbellekli, paralel)
│   ├── omdb.py              # OMDb istemcisi
│   ├── imdb_dataset.py      # IMDb resmi puan veri seti
│   ├── recommender.py       # öneri motoru
│   ├── movie.py             # film kartı ve detay verisi
│   ├── reviews.py           # yorum analizi
│   ├── scoring.py           # Pusula Puanı
│   ├── narrative.py         # Türkçe film anlatımı
│   ├── db.py                # SQLite önbellek
│   ├── routes.py            # sayfalar
│   ├── security.py          # güvenlik başlıkları + istek sınırlama
│   ├── templates/  static/
└── tests/                   # sahte API ile uçtan uca testler
```

## Testler

```bash
pip install -r requirements-dev.txt
pytest
```

Testler gerçek API'ye gitmez; `tests/fakes.py` içindeki sahte TMDB/OMDb sunucusuyla tüm akışı (arama, eleme, sıralama, detay sayfası, CLI) çalıştırır.

## Yasal not

Bu ürün TMDB API'sini kullanır ancak TMDB tarafından onaylanmış veya sertifikalandırılmış değildir. IMDb verileri IMDb'nin [kişisel ve ticari olmayan kullanım](https://developer.imdb.com/non-commercial-datasets/) koşullarıyla kullanılır. Proje ticari amaçla kullanılmamalıdır.
