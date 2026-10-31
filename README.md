# Ne İzlesem? 🎬

Canın film izlemek istiyor ama aklına bir şey gelmiyor mu? Tür seçmek yetmiyor; bazen “içinde **intikam** geçen bir **soygun** filmi, ama **korku olmasın**” istersin. Ne İzlesem? tam bunu yapıyor:

- **Tema seçerek arama** — 85'i aşkın Türkçe tema (intikam, soygun, zaman döngüsü, ters köşe final, yavaş yanan gerilim, güvenilmez anlatıcı, kedi-fare oyunu, neo-noir, folk korku…) ve TMDB'deki binlerce etiket arasında serbest arama.
- **Çoklu seçim + hariç tutma** — temaya bir dokunuş “olsun”, iki dokunuş “olmasın”. Türler için de aynısı.
- **Uygunluk yüzdesi** — her film, seçtiğin temaları gerçekten taşıyor mu, yoksa yüzlerce etiketinden biri mi? Temayı konusunun merkezinde taşıyan filmler öne çıkar.
- **Öneri tarzı** — *Bilinenler* (çok izlenmiş filmler), *Dengeli* (tema uyumu ve kalite önde) ya da *Keşif* (az bilinen, gözden kaçmış filmler).
- **Hep aynı filmler yok** — benzer filmler (devam filmleri, aynı kalıptan yapımlar) art arda gelmez; **Karıştır** aynı aramadan farklı bir sıralama çıkarır; **Daha fazla göster** listenin devamını getirir; gördüğün filmi **gizle**, bir daha karşına çıkmasın (yalnızca senin tarayıcında tutulur).
- **Ruh hali kısayolları** — “Beyin yakan”, “Gerilim gecesi”, “Romantik akşam”…
- **İnce ayar** — dönem, en az puan, en fazla süre, dil, Türkiye'deki platformlar (Netflix, Prime…).
- **Orijinal IMDb puanı** + Rotten Tomatoes, Metacritic ve TMDB puanları.
- **Pusula Puanı** — tüm kaynakları ve izleyici yorumlarını birleştiren, dökümüyle şeffaf kendi puanımız.
- **Yorum analizi** — izleyici yorumlarından “övülenler / eleştirilenler” (oyunculuk, senaryo, tempo, final…).
- **Film sayfası** — sohbet havasında Türkçe özet, konu, fragman, nerede izlenir, oyuncular ve bilinen diğer filmleri, temalar, benzer filmler.
- **Sürpriz yap** — en uygun filmlerden birini rastgele açar.
- **Gala gecesi tasarımı, sade hâli** — bu haftanın popüler afişlerinden akan bir duvar ve projektör ışığı; seçtiğin tema altın bir jeton olup alttaki seçim çubuğuna uçar; “Film bul” deyince salonun ışıkları kararır, sonuçlarda yeniden yanar; kartlar kaydırdıkça sırayla gelir ve fareyle hafifçe eğilir; afişten film sayfasına akan geçiş (Chrome, Edge, Safari 18.2+). Hareket azaltma ayarı açık cihazlarda animasyonlar kendiliğinden kapanır.
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
- **Ocak 2026'dan sonra açılan ücretsiz hesaplarda zamanlanmış görev (Tasks) yok.** Sorun değil: site bakımını kendisi yapıyor (aşağıdaki “Kendi kendine bakım” bölümü).
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
7. Güncelleme yayınlamak için (GitHub'a gönderdikten sonra):
   ```bash
   cd ~/ne-izlesem && git pull
   ```
   ve Web sekmesinde **Reload**.

## Kendi kendine bakım

Elle yapman gereken bir şey yok; site, bir ziyaretçinin isteğine **yanıt verdikten sonra** arada bir kendi bakımını yapar (en sık 10 dakikada bir kontrol eder, kimse beklemez):

| İş | Ne zaman | Ayar (`.env`) |
|---|---|---|
| Süresi dolan önbelleği silmek, boşalan yeri diske geri vermek | 6 saatte bir | `CLEANUP_INTERVAL_HOURS` |
| Önbellek sınırı aşılırsa en eski kayıtları budamak | aynı anda | `CACHE_MAX_MB` (varsayılan 150) |
| IMDb puanlarını resmi veri setinden yenilemek | 30 günde bir | `IMDB_AUTO_UPDATE_DAYS` (0 = kapalı) |

IMDb indirmesi başarısız olursa eski puanlar korunur ve ertesi gün yeniden denenir. Durumu görmek ya da bakımı hemen çalıştırmak istersen:

```bash
cd ~/ne-izlesem && workon ne-izlesem && flask --app wsgi bakim
```

Tek elle yapılacak iş PythonAnywhere'in kendisiyle ilgili: ücretsiz hesapta web uygulamasının süresini ayda bir Web sekmesinden uzatmak.

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
- “En uygun” sıralamada Pusula Puanı, tema uyumunun yanında ikinci ölçüttür (ayrıntısı aşağıda).

## Öneri motoru nasıl çalışıyor?

1. Seçilen Türkçe temalar TMDB etiket kimliklerine çevrilir (her tema birkaç eş anlamlı etikete bağlı).
2. **Geniş aday havuzu:** TMDB *discover* ile tek bir “en popüler” listesi yerine birçok açıdan aday toplanır: hepsini içerenler (VE), herhangi birini içerenler (VEYA), en çok oylananlar, en yüksek puanlılar, her tema için ayrı en iyiler, farklı on yıllardan filmler ve az bilinen iyi filmler. Az sonuç çıkarsa oy eşiği kademeli düşürülür.
3. Adayların gerçek etiketleri çekilir; “olmasın” denenler elenir.
4. **Uygunluk puanı** üç şeye bakar:
   - *Nadirlik (IDF):* “intikam” gibi binlerce filmde geçen bir temayı tutturmak, nadir bir temayı tutturmaktan daha az değerlidir.
   - *Merkezilik (BM25 uzunluk düzeltmesi):* 40 etiketli bir gişe filminin “intikam” etiketi taşıması ile 8 etiketli bir filmin konusunun intikam olması aynı şey değildir. Az ve odaklı etiketli film daha yüksek puan alır.
   - *Konu metni:* TMDB'deki Türkçe özetinde temanın kendisi geçiyorsa (ör. “öcünü almak”) tema konunun merkezinde sayılır.
5. **Sıralama** öneri tarzına göre değişir:

   | Tarz | Ağırlıklar |
   |---|---|
   | Bilinenler | %50 uygunluk + %30 Pusula + %20 ünlülük |
   | Dengeli (varsayılan) | %60 uygunluk + %40 Pusula, çok ünlü filmlere küçük ceza |
   | Keşif | %62 uygunluk + %30 Pusula, ünlülük arttıkça ceza |

6. **Çeşitlilik (MMR):** Sıralama yapılırken her yeni film, listede zaten olan filmlere ne kadar benzediğine göre (ortak etiketler, türler) geri itilir. Böylece bir devam filmi serisi ya da aynı kalıptan beş film art arda gelmez.
7. **Karıştır** uygun filmlerin sırasına küçük ve kontrollü bir rastgelelik katar (Gumbel gürültüsü): en uygunlar yine üstte kalır ama her seferinde aynı ilk 16 gelmez.
8. Sonuçlar sayfa sayfa gelir (**Daha fazla göster**), en iyi adaylar IMDb puanı, eleştirmen puanları ve yorum analiziyle zenginleştirilir. Aday havuzu 6 saat önbellekte kalır; karıştırmak ve sayfalamak havuzu baştan toplamaz, yalnızca yeni gelen filmlerin ayrıntıları çekilir.

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
│   ├── maintenance.py       # kendi kendine bakım (önbellek, IMDb güncellemesi)
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

- **TMDB:** Bu ürün TMDB API'sini kullanır ancak TMDB tarafından onaylanmış veya sertifikalandırılmış değildir. TMDB'nin onaylı logosu (`static/img/tmdb-logo.svg`) değiştirilmeden, yalnızca kaynak göstermek için kullanılır.
- **IMDb:** Puanlar IMDb'nin [kişisel ve ticari olmayan kullanım](https://developer.imdb.com/non-commercial-datasets/) için yayımladığı veri setinden gelir. Sitede zorunlu atıf cümlesi yer alır: *Information courtesy of IMDb (https://www.imdb.com). Used with permission.* Veri seti repoya eklenmez (`.gitignore`), değiştirilmez ve yeniden dağıtılmaz. Site kişisel kullanım içindir; bu yüzden arama motorlarına kapalıdır (`robots.txt`, `noindex`).
- **JustWatch:** Türkiye'deki yayın platformu bilgisi JustWatch kaynaklıdır ve sayfada belirtilir.
- **Markalar:** IMDb, Rotten Tomatoes, Metacritic ve platform adları sahiplerinin markalarıdır; logoları kullanılmaz, adları yalnızca kaynağı belirtmek için yazıyla geçer.
- **Ticari kullanım yok:** Reklam koymak, ücret almak ya da veriyi satmak TMDB ve IMDb'den ayrı lisans gerektirir.
