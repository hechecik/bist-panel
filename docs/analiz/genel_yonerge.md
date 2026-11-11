# Genel yönerge (referans — görevler docs/gorevler/ altında)

Repo: github.com/hechecik/bist-panel · Canlı: hechecik.github.io/bist-panel
Kapsam: `scripts/*.py`, `data/*.json`, `index.html`, `.github/workflows/*.yml`
(Altın bölümünün detaylı yönergesi ayrı dosyada: `altin_bolumu_yonerge.md`)

## Değişmez ilkeler (CLAUDE.md'ye de yazılacak)
1. **LLM/ücretli API çağrısı YOK.** Bu panel çalışırken sıfır token harcar. Bu kural korunacak. Bütün yorum metinleri sayılardan deterministik şablonlarla üretilir.
2. **Anti-halüsinasyon:** Her sayının bir kaynağı vardır. Veri alınamazsa ekranda "veri yok" yazar, tahmini değer gösterilmez.
3. **Tüm zaman damgaları timezone-aware UTC ISO formatında yazılır** (`...+00:00`). UI bunları TR saatine çevirir.
4. **Bağımsız bloklar:** Bir kaynak düşerse diğerleri etkilenmeden yazılmaya devam eder.
5. **Yatırım tavsiyesi değildir** notu her bölümde kalır.

---

## P0 — VERİYLE DOĞRULANMIŞ KRİTİK HATALAR (önce bunlar)

### P0-1. Fiyatlar bölünmeye göre düzeltilmemiş → backtest ve indikatörler bozuk
- **Kanıt:** `test_senaryolari` içinde RALYH girişi 273,5 TL, "bugün" fiyatı 5,02 TL, getiri −%98,2. Bu bir bedelsiz bölünme. S1 ve S2 senaryolarının "ortalama −%23,5" sonucu büyük ölçüde bu yapay düşüşlerden geliyor. Aynı kırılma MA, RSI ve ATR hesaplarını da bozuyor.
- **Düzeltme:**
  - Bölünmeye göre düzeltilmiş seri kullan. yfinance'ta `auto_adjust=True` ile split ve temettü düzeltmesi var. borsapy/TradingView için düzeltme parametresini kontrol et.
  - Ek güvenlik: Önceki kapanışa göre ±%35'ten büyük gece boşluğu VE ertesi günlerde hacmin normal seyretmesi durumunda bunu `olasi_bolunme` olarak işaretle. O hisseyi o gün backtest ve sinyal hesabından çıkar, UI'da ⚠️ göster.
  - Bedelsiz bölünme oranını `takvim.json` içine (halkarz.com veya KAP) ekleyip bunu da çapraz kontrol olarak kullan.

### P0-2. SMA200 hiç hesaplanamıyor → "YUKARI trend" hiçbir zaman çıkmıyor
- **Kanıt:** Veri 6 aylık çekiliyor (~125 bar). Bu yüzden SMA200 her zaman NaN. `fiyat > SMA50 and SMA50 > SMA200` koşulu NaN ile hep False döner. Mevcut veride listelenen 27 hissenin 17'si ASAĞI, 10'u YATAY, YUKARI sıfır. Skor sistemi yapısal olarak ayı yönüne kaymış durumda.
- **Düzeltme:** `period='18mo'` kullan (en az 260 bar). SMA200 NaN ise trend hesabını SMA50/SMA20 ile yap ve bunu `trend_kaynak: "kısa"` olarak etiketle.

### P0-3. `OBV_EGIM` hiç hesaplanmıyor
- `sinyal_hesapla` fonksiyonu `son.get('OBV_EGIM', 0)` okuyor ama `tum_indikatorler` bu sütunu üretmiyor. Sonuç: OBV her zaman "ZAYIF".
- **Düzeltme:** `OBV_EGIM = OBV'nin son 10 bara lineer regresyon eğimi` hesapla ve skora ±1 olarak ekle. Ya da göstergeyi tamamen kaldır.

### P0-4. Sektör, gece analizi ve karne sadece listelenen ~27 hisseden hesaplanıyor
- Sinyal listeleri al:15, tut:10, sat:10 ile sınırlı. `sektor_list`, `gece_analizi` ve `guncel_fiyatlar` bu kırpılmış listelerden hesaplanıyor. Sektör tablosu 100 değil 27 hisseyi temsil ediyor. Karnede bugün listede olmayan hisselerin fiyatı yok, bu yüzden hesap dışı kalıyorlar (survivorship bias).
- **Düzeltme:** `sinyalleri_hesapla` fonksiyonu kırpılmamış `tum` listesini de döndürsün. Sektör, gece analizi ve karne bu tam listeden hesaplansın. UI kırpılmış listeyi göstermeye devam edebilir.

### P0-5. Zaman damgası 3 saat kayık ve tazelik hesabı yanlış
- `uretildi` alanı runner saatiyle (UTC) ve saat dilimi olmadan yazılıyor. `index.html:382` içinde `new Date(d.uretildi)` bu değeri TR yerel saati sanıyor. Sonuç: gösterilen saat ve "X dk önce" hesabı 3 saat kayık. Aynı sorun `altin_cek.py`, `getiri_cek.py` ve `takvim_cek.py` için de geçerli.
- **Düzeltme:** Python'da `dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')`, JS'de `new Date(iso)` kullan. TR saati için `toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})`.

### P0-6. Zamanlanmış görevler neredeyse hiç çalışmıyor → "15 dk gecikmeli, seans boyunca canlı" iddiası doğru değil
- **Kanıt (son 6 günün commit geçmişi):**
  - `veri-cek` 15 dakikada bir planlı (günde ~40 çalışma). Gerçekte günde ~2 commit var, bazıları 20:50 ve 23:43 UTC gibi planlanan pencerenin (06–15 UTC) tamamen dışında.
  - `altin-cek` ve `kripto-cek` 30 dakikada bir planlı (günde 48). Gerçekte günde 3–5.
  - GitHub'ın zamanlayıcısı yoğun dakikalarda çalışmaları geciktiriyor veya atlıyor.
- **Düzeltme (ücretsiz):**
  - Dış tetikleyici kur: **cron-job.org** (ücretsiz) veya **Cloudflare Workers Cron Trigger** (ücretsiz katman). Bunlar GitHub API'sindeki `workflow_dispatch` ya da `repository_dispatch` uç noktasını çağırır.
  - Yetki için sadece bu repoya ve sadece `actions: write` iznine sahip fine-grained PAT kullan. PAT dış serviste saklanır, repoya yazılmaz.
  - Cron dakikalarını :00/:15/:30 yerine :07/:22/:37 gibi kaydır (GitHub tarafında kalanlar için).
  - Her workflow'a **kendi** concurrency grubunu ekle: `concurrency: {group: ${{ github.workflow }}, cancel-in-progress: false}`. Tek ortak grup KULLANMA, GitHub bir grupta tek bekleyen çalışma tuttuğu için görevler birbirini iptal eder. Push adımına 3 denemelik `fetch → rebase → push` döngüsü ekle. *(Yamada uygulandı.)*
  - Site açıklamasını gerçek güncelleme sıklığına göre düzelt.

### P0-7. Haber duygu analizi alt-dize eşleşmesi yüzünden yanlış etiketliyor
- `'kar' in 'karar'` → pozitif, `'artis' in 'partisi'` → pozitif, `'kar' in 'karşı'` → pozitif. Bu yüzden faiz "kararı" haberleri pozitif etiket alıyor.
- **Düzeltme:** Kelime sınırlı regex kullan: `re.search(r'\b(kâr|kar)\b', ...)`. Türkçe ekler için kök + izinli ek listesi tanımla (`kârı`, `kârını`...). "faiz artışı" gibi bağlama bağlı ifadeleri tek kelimeden önce değerlendir. Haberlerin %77'si "nötr" çıkıyor; bu sorun değil, doğru davranış.

### P0-8. Gram altın değeri ons × kur ile tutarsız
- **Kanıt:** `piyasa.json` içinde gram 6.675,77 TL ve +%1,81 değişim görünüyor. Ama ons 4.036,5$ (−%1,9) ve USD/TL 50,18 ile hesaplanan değer ≈ 6.512 TL. Fark %2,5 ve yön de ters. borsapy'den gelen gram değeri bayat.
- **Düzeltme:** Gram = spot ons / 31,1035 × USD/TL olarak hesapla. borsapy değerini sadece çapraz kontrol için kullan ve fark %1'i aşarsa ⚠️ göster.

### P0-9. TR devlet tahvili verisi boş
- `getiri.json → "tahvil": []`. `bp.bonds()` boş dönüyor. UI eurobond tablosunu gösteriyor, tahvil kısmı sessizce kayboluyor.
- **Düzeltme:** Hata durumunu JSON'a `"tahvil_durum": "kaynak boş"` olarak yaz ve UI'da göster. Alternatif kaynak ekle (bkz. Kaynaklar). 2Y, 5Y ve 10Y TR getirisi ayrıca makro bölümünde de kullanılacak.

### P0-10. Küçük hatalar
- `bist100.txt` 99 satır. Endeks bileşimi çeyreklik değişiyor. Kaynaktan otomatik güncelle veya en azından son güncelleme tarihini dosyaya yaz.
- Fallback listesinde KCHOL iki kez geçiyor.
- `hisse_bazli.max_dusus` aslında "en kötü işlem getirisi". Pozitif değer alabiliyor (GARAN 7,2). Ya adını değiştir ya da gerçek max drawdown hesapla.
- Haber sıralaması string sıralamasıyla yapılıyor ve bazı tarihlerde saat dilimi var, bazılarında yok. Hepsini UTC ISO'ya çevirip öyle sırala.

---

## P1 — BACKTEST / KARNE YENİDEN TASARIMI
Mevcut test geçerli bir backtest değil:
- **Çıkış kuralı yok:** Her işlem "bugüne kadar" tutuluyor. 6 ay önceki sinyal ile dünkü sinyal aynı tabloya giriyor.
- **Çakışan işlemler:** Aynı hissenin ardışık günlerdeki sinyalleri ayrı işlem sayılıyor (ENERY 19 işlem).
- **Sermaye simülasyonunda seçim yanlılığı:** İlk 10 işlem dict sırasıyla (sembol sırası) seçiliyor, kronolojik değil.
- **Maliyet yok:** Komisyon, BSMV ve kayma hesaba katılmıyor.

**Yeni kurallar:**
- **Sabit vadeler:** 5, 10 ve 20 iş günü sonraki kapanışta çık. Ayrıca ATR stop (2×ATR) ve hedef (3×ATR) hangisi önce gelirse orada çık.
- **Aynı hissede açık pozisyon varken yeni sinyal açılmaz.**
- **Varsayılan maliyet:** Gidiş-dönüş %0,2 (parametrik).
- **Benchmark:** Aynı vadelerde XU100 getirisi. Rapor her zaman "sinyal getirisi − endeks getirisi" (alfa) olarak gösterilir.
- **Metrikler:** isabet oranı, ortalama kazanç/kayıp, profit factor, max drawdown, işlem sayısı. Ayrıca skor seviyesine göre (2, 3, ≥4) ayrı tablo.
- **Ağır hesaplar günde 1 kez çalışır** (kapanış sonrası), 15 dakikalık görevde değil.

## P1 — TEKNİK ANALİZ GELİŞTİRMELERİ
- **Göreli güç (RS):** hisse/XU100 oranının 20/60 günlük değişimi. BIST'te tek başına RSI'dan daha bilgilendirici.
- **Hacim anomalisi:** bugünkü hacim / 20 günlük medyan ≥ 2 ise "hacim patlaması". Tavan/taban serisi tespiti.
- **Piyasa genişliği:** XU100'de MA50 üstündeki hisse yüzdesi, yükselen/düşen oranı, 52 haftalık yeni zirve/dip sayısı.
- **Skor bağımsızlığı:** MACD, Stoch RSI ve RSI hepsi momentum ölçüyor; skora üçü ayrı ayrı ±1 ekleniyor. Momentum bileşenlerini tek bir ±1'de birleştir. Yerine trend + RS + hacim + volatilite koy.
- **Endeks rejimi filtresi:** XU100 MA50 altındaysa AL eşiği +1 artsın.
- **Pivotlar:** Günlük klasik pivot tek başına zayıf. Haftalık pivot ve swing seviyelerini ekle.

## P1 — TEMEL ANALİZ (şu an en zayıf alan)
- **Mevcut durum:** Yahoo `.info` ile F/K, PD/DD ve temettü alınıyor. Sadece listedeki ilk 30 hisse işleniyor (BIST30 değil, alfabetik). Her 15 dakikada 30 istek atılıyor, bu da rate-limit riski.
- **Sorunlar:**
  - Yahoo'nun BIST temel verisi sıklıkla eski veya hatalı.
  - TMS 29 enflasyon muhasebesi sonrası nominal F/K karşılaştırması yanıltıcı.
  - Banka F/K'sı ile sanayi F/K'sı aynı skalada puanlanıyor.
- **Yapılacaklar:**
  1. Kaynağı İş Yatırım mali tablolar veya KAP finansal raporları yap. Yahoo yedek olarak kalsın.
  2. Oranları **sektör medyanına göre** puanla, mutlak eşiklerle değil.
  3. Eklenecek metrikler: FAVÖK marjı, net borç/FAVÖK, ROE (reel, TÜFE düşülmüş), çeyreklik satış büyümesi (reel), serbest nakit akışı, temettü sürekliliği.
  4. **Bilanço takvimi:** Hangi şirket ne zaman açıklayacak? KAP verisinden takvime eklenecek.
  5. Haftada 1 kez çalışsın. Sonuçlar ayrı `temel.json` dosyasına yazılsın.

---

## P1 — TOKEN DOSTU MİMARİ (iki anlamda)

### A) Çalışma zamanı: sıfır LLM maliyeti
- Kodda LLM çağrısı yok, bu korunacak. "AI yorumu" istenirse yine şablon tabanlı yazılsın.
- Veri sağlayıcı kotasını korumak için iş yükünü sıklığına göre böl:
  | Görev | Sıklık | İçerik |
  |---|---|---|
  | `fiyat` | seans içi 15 dk | OHLCV, endeks, makro fiyatlar, sinyal |
  | `gunluk` | 18:30 TR | backtest, karne, ICT, gece analizi, genişlik |
  | `haftalik` | Cmt | temel analiz, sektör haritası, bist100 listesi |
  | `altin` / `kripto` | 30 dk | mevcut |
  | `ek` | 2×/gün | tahvil, takvim |
- **HTTP önbellek:** `ETag`/`If-Modified-Since` kullan. Kaynak aynıysa JSON'u yeniden yazma, böylece boş commit oluşmaz.

### B) Geliştirme: kod ajanının daha az token harcaması
Şu an `index.html` 91 KB (~30 bin token), `veri_cek.py` 53 KB, `piyasa.json` 121 KB. Ajan her küçük değişiklikte bunların hepsini okuyor.
- **Ön yüzü böl (build adımı yok, native ES module):**
  ```
  index.html            (sadece iskelet)
  css/app.css
  js/core.js            (fmt, tarih, fetch, sekme yönetimi)
  js/bolum/piyasa.js  grafik.js  altin.js  kripto.js  karne.js  haber.js  takvim.js  getiri.js  ict.js
  ```
- **Python'u paketle:**
  ```
  scripts/kaynak/   isyatirim.py borsapy_tv.py yahoo.py fred.py tcmb.py doviz.py rss.py kap.py
  scripts/analiz/   indikator.py sinyal.py backtest.py temel.py genislik.py ict.py
  scripts/gorev/    fiyat.py gunluk.py haftalik.py altin.py kripto.py ek.py
  scripts/ortak.py  (log, utc_now, json_yaz, HEADERS)
  ```
- **Veriyi böl:** `piyasa.json` → `fiyat.json`, `sinyal.json`, `haber.json`, `backtest.json`, `temel.json`. Hem sayfa daha hızlı açılır hem ajan sadece ilgili dosyayı okur.
- **Şema dosyaları:** `schema/*.json` (JSON Schema). Ajan 120 KB'lık veri dosyası yerine 2 KB'lık şemayı okur.
- **`CLAUDE.md` (repo kökü):** dosya haritası, veri sözleşmeleri, değişmez ilkeler, test komutları. Şu kural da yazılacak: "`data/*.json` dosyalarını tamamen okuma, `jq` ile alan seç".
- **`.claude/settings.json`:** `{"permissions":{"deny":["Read(./data/**)"]}}`. Ajan veri dosyalarını kazara bütün olarak okumaz.
- **Testler:** `tests/` altında ağ bağlantısız fixture'larla (`tests/fixtures/*.json`) pytest. Ajan değişikliği internete çıkmadan doğrular.
- **Veri commit'lerini ayrı dala al:** Veriyi `data` dalına veya Pages artifact'ına yaz. `main` dalının geçmişi kodla sınırlı kalır (şu an 133 "veri guncelle" commit'i var). Ajan `git log` okurken gürültü olmaz.

---

## P2 — SİTEDE OLMAYAN ALANLAR (öncelik sırasıyla)
1. **Dolar ve altın bazlı BIST:** XU100/USDTRY ve XU100/gram altın grafikleri. TR'de nominal endeks yanıltıcı, reel performans en kritik görünüm.
2. **Türkiye risk paneli:** 5Y CDS, TR 2Y/10Y getiri, TCMB brüt/net rezerv (haftalık), reel faiz (politika faizi − beklenen enflasyon), PPK takvimi ve geri sayım.
3. **Yabancı payı:** Hisse bazında yabancı takas oranı ve 20 günlük değişimi. BIST'te en güçlü akış göstergelerinden biri.
4. **KAP bildirim akışı:** Şu an Google News'te "KAP bildirim" araması yapılıyor, bu zayıf. Doğrudan KAP verisi lazım: özel durum açıklamaları, bedelsiz/temettü, geri alım, iş ilişkisi. Hisse kartlarına bağlanmalı.
5. **Küresel bağlam:** S&P 500, DAX, DXY, US10Y, EEM (gelişen piyasalar), VIX (var). Bunlar "gece analizi"ne ve ertesi gün açılış beklentisine bağlanabilir.
6. **İzleme listesi + portföy (localStorage, sunucusuz):** Kullanıcının kendi hisseleri, maliyeti, pozisyon büyüklüğü, işlem başına risk (%1 kuralı → ATR stop'tan lot hesabı), reel ve USD bazlı K/Z.
7. **Bildirim (ücretsiz, LLM yok):** ntfy.sh veya Telegram bot. Kırılım, hacim patlaması, PPK/FOMC, KAP özel durum bildirimleri. Bot token'ı GitHub Secrets'ta durur.
8. **Sektör ısı haritası:** 100 hissenin tamamı, günlük/haftalık getiri ve RS.
9. **VİOP:** XU030 vadeli bazı (prim/iskonto) ve açık pozisyon. Kaynak bulunabilirse eklenir.
10. **Karne şeffaflığı:** Her sinyal için "neden üretildi, sonra ne oldu" kayıt defteri (bunun temeli `sinyal_gecmisi`'nde zaten var).

---

## KAYNAKLAR (yerli / yabancı)
Ücret ve erişim sınıflandırması: 🟢 anahtarsız · 🟡 ücretsiz anahtar (GitHub Secrets'ta saklanır, maliyeti yok) · 🔴 ücretli.
**Uyarı:** Gayriresmi uç noktalar (⚠️) zamanla değişebilir. Kullanmadan önce yanıt yapısını doğrula ve her biri için fallback tanımla.

**Yerli**
- 🟢 İş Yatırım HisseTekil (mevcut, ABD IP'sinden engellenebilir) ve mali tablo uç noktası ⚠️
- 🟢 KAP (kap.org.tr): bildirimler, finansal raporlar, şirket kartı ⚠️ gayriresmi JSON uçları
- 🟡 **TCMB EVDS:** politika faizi, rezervler, TÜFE beklenti anketi, kur serileri. Ücretsiz anahtarla resmi API. Şu anki HTML parse yerine kullanılmalı.
- 🟢 TCMB HTML (mevcut, yedek), TÜİK bülten takvimi
- 🟢 TEFAS (borsapy üzerinden, mevcut), halkarz.com (mevcut), doviz.com (mevcut)
- 🟢 Borsa İstanbul: endeks bileşenleri, açığa satış ve kredili işlem bültenleri ⚠️
- 🟢 MKK / BIST: yabancı takas oranları ⚠️ (bulunamazsa İş Yatırım "yabancı oranı")
- 🔴 Matriks, Foreks, BIST Data Store: AKD/takas detayı ve gerçek zamanlı veri. Bunlar olmadan da panel çalışır.

**Yabancı**
- 🟢 **FRED CSV** (`fred.stlouisfed.org/graph/fredgraph.csv?id=…`): DGS2, DGS10, DFII10, T10YIE, DFEDTARU, FEDTARMD (dot plot), DTWEXBGS
- 🟢 yfinance (mevcut): endeksler, emtia, `XU100.IS`, `TRY=X`, `^GSPC`, `DX-Y.NYB`, `EEM`
- 🟢 **Stooq CSV:** yfinance düştüğünde endeks ve kur yedeği
- 🟢 CoinGecko ve alternative.me (mevcut), gold-api.com (mevcut)
- 🟢 CFTC COT raporu: altın ve emtia pozisyonlanması (haftalık)
- 🟢 World Gold Council: merkez bankası altın alımları (aylık) ⚠️
- 🟢 federalreserve.gov: FOMC takvimi, SEP

---

## UYGULAMA SIRASI ve KABUL KRİTERLERİ
1. **P0-6** (dış tetikleyici + concurrency) → 1 seans boyunca ≥ 30 `fiyat` çalışması commit'lenmiş olmalı.
2. **P0-1, P0-2, P0-3** → RALYH benzeri −%90+ işlem backtest'te yok. En az bir hisse "YUKARI" trend alabiliyor (SMA200 dolu).
3. **P0-4, P0-5, P0-7, P0-8, P0-9, P0-10** → Sektör tablosu ~100 hisseyi kapsıyor. Saat TR saatiyle doğru. "Faiz kararı" haberi pozitif etiket almıyor. Gram tutarlılık uyarısı çalışıyor.
4. **Mimari bölünme** (B) → Her bölüm dosyası < 15 KB. `CLAUDE.md` ve şemalar mevcut. `pytest` ağsız geçiyor.
5. **P1 backtest + teknik + temel**
6. **P2** sırayla.
- Her adım ayrı PR olsun. PR açıklamasında önce/sonra JSON örneği bulunsun.
- Hiçbir adımda LLM çağrısı veya elle girilmiş tahmini sayı eklenmeyecek.
