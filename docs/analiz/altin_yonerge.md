# Altın sekmesi yönergesi (referans)

Repo: github.com/hechecik/bist-panel
Dosyalar: `scripts/altin_cek.py` → `data/altin.json` → `index.html` (`renderAltin`), workflow `.github/workflows/altin-cek.yml`

## Değişmez ilkeler
- **Anti-halüsinasyon korunur:** Her sayı gerçek bir veri kaynağından gelir. Metinler sayılardan deterministik üretilir. Elle olasılık uydurmak YASAK. Olasılık gösterilecekse piyasa fiyatlamasından (fed funds vadelileri) türetilir. Türetilemiyorsa "veri yok" yazılır.
- API anahtarı gerektiren kaynak yok. Ücretsiz ve anahtarsız kaynaklar kullanılır: yfinance, FRED CSV (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERI`), gold-api.com, doviz.com, federalreserve.gov.
- Her yeni veri bloğu bağımsız try/except içinde çalışır. Biri düşerse diğerleri yazılmaya devam eder ve JSON'da `"durum": "veri yok"` alanı olur.
- "Yatırım tavsiyesi değildir" notu kalır.

---

## A) HATA DÜZELTMELERİ (önce bunlar)

1. **Gün adı kayması** (`kritik_gunler`): `gunler = ['Paz','Pzt',...]` listesi `weekday()` ile indeksleniyor. Ama `weekday()` için Pazartesi=0. Sonuç olarak tüm günler bir gün geriden gösteriliyor (12.11 Perşembe "Çar" görünüyor).
   → `gunler = ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz']`

2. **Haber tarihi hiç görünmüyor:** `renderAltin` içinde `n.tarih` okunuyor ama JSON alanı `yayin_tarihi`.
   → `yayin_tarihi` alanını parse et ve TR saatiyle "11.11 07:40" formatında göster.

3. **Takvim penceresi en kritik olayı kaçırıyor:** Pencere 21 gün ve kayıt sayısı `[:14]` ile sınırlı. Bu yüzden 9 Aralık FOMC kararı listede yok. Liste Euro Bölgesi istihdamı ve iki kez yazılmış Çin LPR ile dolmuş.
   → Önce önem derecesine (high > mid), sonra tarihe göre sırala. Pencereyi 45 güne çıkar, sınırı uygula ama FOMC kararlarını her zaman göster (bkz. B3).

4. **Yinelenen kayıtlar:** "ADP 15:15 + 16:15" ve "Çin LPR 1Y 04:00 + 04:15" aynı olayın tekrarı.
   → Tekilleştirme anahtarı `(iso, normalize(olay))` olsun, saat anahtara dahil edilmesin.

5. **ÜFE/PPI listeye girmiyor:** `SURUCU` sözlüğünde 'üretici fiyat', 'üfe', 'ppi' kelimeleri yok. Bu hafta Cuma açıklanacak ÜFE bu yüzden listede değil.
   → Bu kelimeleri ekle. Fed konuşmacıları için de 'fomc üyesi', 'fed üyesi' ekle.

6. **Gram altın vadeli fiyatla hesaplanıyor:** `gram_tl` vadeli kontrat GC=F fiyatıyla hesaplanıyor. Bu kontrat spotun ~5–20$ üstünde işlem görür ve kontrat devirlerinde fiyat sıçrar.
   → Manşet ons ve gram için SPOT kullan: `gram = spot / 31.1034768 * usdtry`. GC=F'yi sadece tarihsel seri (MA/RSI/ATR) için kullan. Spot yoksa GC=F'ye düş ve UI'da "vadeli" rozeti göster.

7. **UTC/TR saat karışıklığı:** `uretildi` alanı runner saatiyle (UTC) ve saat dilimi bilgisi olmadan yazılıyor.
   → `dt.datetime.now(dt.timezone.utc).isoformat()` kullan. UI'da TR saatine çevirip göster.

8. **Tazelik rozeti sahte:** Rozet her zaman "ok" sınıfında.
   → Hafta içi `uretildi` 90 dakikadan eskiyse "bayat" uyarısı ver.

9. **Metin–kod uyuşmazlıkları:**
   - Senaryo metninde "hacimle kırıp" yazıyor ama kodda hacim kontrolü yok. Ya hacim filtresi ekle ya da kelimeyi kaldır.
   - Alt nottaki "trend eğimi" ifadesi yanlış, kod aslında 1 aylık performansı kullanıyor. Notu kodla eşleştir.

---

## B) YENİ VERİ KATMANI — makro sürücüler (`altin.json` → `makro` bloğu)

### B1. Piyasa sürücüleri (günlük)

| Alan | Kaynak | Kullanım |
|---|---|---|
| DXY | yfinance `DX-Y.NYB` | dolar gücü |
| ABD 10Y nominal | FRED `DGS10` | fırsat maliyeti |
| ABD 10Y reel (TIPS) | FRED `DFII10` | **altının 1 numaralı makro sürücüsü** |
| 10Y başabaş enflasyon | FRED `T10YIE` | enflasyon beklentisi |
| ABD 2Y | FRED `DGS2` | Fed beklentisinin en hızlı göstergesi |
| Brent | yfinance `BZ=F` | jeopolitik/enflasyon kanalı (WTI ile KARIŞTIRMA, ikisi ayrı alan olsun) |
| Fed faiz bandı | FRED `DFEDTARU` / `DFEDTARL` | mevcut politika faizi |

Her biri için şunları hesapla: son değer, 5 günlük ve 20 günlük değişim, ve ons ile 60 günlük rolling korelasyon. Korelasyon UI'da "bu sürücü şu an altını ne kadar açıklıyor" sorusuna cevap verir.

### B2. DOT PLOT bloğu (`makro.dot_plot`)
- FRED `FEDTARMD` serisini çek (FOMC SEP medyan fed funds projeksiyonu, yıl bazında). Mümkünse `FEDTARRH`/`FEDTARRL` (aralık) da çek.
- **Piyasa ima eden patika:** yfinance ile fed funds vadelileri (`ZQ=F` ve ilgili kontrat ayları). İma edilen faiz = 100 − fiyat. Kontrat çekilemezse proxy olarak 2Y getiri − mevcut faiz farkını kullan ve "proxy" diye etiketle.
- Çıktı:
  ```
  dot_plot: {
    son_sep_tarihi, medyan: {2026: x, 2027: y, 2028: z, uzun_vade: w},
    onceki_sep_medyan: {...},          # bir önceki SEP (değişim için)
    piyasa_ima: {2026_sonu: a, 2027_sonu: b},
    makas_bp: (piyasa − dot) * 100,     # + ise piyasa Fed'den şahin
    yorum: deterministik metin
  }
  ```
- Yorum kuralı (örnek):
  - makas > +25 bp → "Piyasa Fed'in kendi projeksiyonundan şahin. Güvercin bir SEP altına pozitif sürpriz olur."
  - makas < −25 bp → tersi.
  - Aradaysa → "Uyumlu, sürpriz potansiyeli düşük."
- **SEP sonrası otomatik karşılaştırma:** Yeni SEP yayınlandığında (Mart/Haziran/Eylül/Aralık toplantıları) 2027 medyanının bir önceki SEP'e göre değişimini hesapla. Değişim ≥ +25 bp ise "şahin revizyon", ≤ −25 bp ise "güvercin revizyon" olarak işaretle ve sonucu senaryo motoruna aktar.

### B3. FOMC takvimi (`scripts/fomc_tarihleri.json`)
- Tarihleri federalreserve.gov/monetarypolicy/fomccalendars.htm sayfasından parse et. Parse başarısız olursa elle doldurulmuş JSON'a düş. **2027 tarihlerini tahmin etme**, sadece resmi sayfadan al.
- Alanlar: `tarih`, `karar_saati_tr` (yaz/kış saatine göre 21:00/22:00 TSİ, bunu hesapla, sabit yazma), `sep: true/false`, `tutanak_tarihi`.
- UI'da her zaman görünen bir sayaç: "Sonraki FOMC: 9 Aralık 22:00 TSİ · 28 gün · SEP/dot plot VAR".
- Kritik veri günlerine "FOMC'den önceki son veri" etiketi ekle. Toplantıdan SONRA gelen veriyi de ayrıca işaretle (örnek: Kasım TÜFE 10 Aralık'ta, karardan bir gün sonra).

### B4. Kurum hedefleri (`scripts/kurum_hedefleri.json`, elle güncellenir)
- Alanlar: `kurum`, `hedef`, `vade`, `revizyon_tarihi`, `onceki_hedef`, `kaynak_url`.
- UI'da 60 günden eski revizyonları "⚠️ eski" diye işaretle.
- Bu verinin otomatik çekilmesi gerekmez. Ama tarihsiz hedef gösterilmez.

---

## C) SENARYO MOTORU v2 (`senaryo` bloğunu genişlet)

> ⚠️ **Not (derin analizden sonra):** Aşağıdaki makro skor eşikleri (±10 bp, ±%1, ±%10) doğrulanmamış başlangıç değerleridir. Hisse skorundaki sorunun aynısı burada da geçerli. Bu eşikler ürüne alınmadan önce Bölüm 1 §6'daki log + IC denetiminden geçirilmeli.

### C1. Skoru ikiye ayır
- `teknik_skor` (mevcut, −5..+5): Trend, konum ve 1 aylık performans aynı şeyi (momentum) üç kez sayıyor. Ağırlıkları düşür veya 52 haftalık konumu kaldır.
- `makro_skor` (yeni, −4..+4), her bileşen ±1:
  - Reel 10Y 20 günde ↓ ≥ 10 bp → +1, ↑ ≥ 10 bp → −1
  - DXY 20 günde ↓ ≥ %1 → +1, ↑ ≥ %1 → −1
  - Dot plot makası (B2): piyasa Fed'den şahin → +1 (geri çekilme potansiyeli), güvercin → −1
  - Brent 20 günde ↑ ≥ %10 → +1 (jeopolitik prim), ↓ ≥ %10 → −1
- UI'da iki skor yan yana gösterilsin. Çeliştiklerinde (örnek: teknik AYI, makro BOĞA) uyarı versin: "⚠️ Teknik ve makro ayrışıyor, kırılım riski yüksek."

### C2. Seviye seçimi
- Mevcut durumda en yakın seviyeler 50$'lık yuvarlak sayılar oluyor ve hepsi 1 ATR'nin içinde kalıyor (günlük ATR ~87$). Örnek: tetik %0,7 uzakta, hedef sadece 50$ ötede. Bu bir senaryo değil, gürültü.
- Kural: Tetik ≥ 0,5×ATR uzakta olmalı, hedef tetikten ≥ 1×ATR ötede olmalı.
- Seviye tipleri için öncelik sırası: salınım pivotu > MA200/MA50 > 52 haftalık uç > 100'lük yuvarlak (50'likleri kaldır).
- Her senaryoya bir **geçersizlik seviyesi** ekle (senaryonun bozulduğu yer).

### C3. Makro koşullu senaryolar (dot plot ile)
Sabit olasılık YOK. Her senaryo bir "EĞER → GÖZLENEBİLİR TETİK → ETKİ" zinciri olarak yazılır:

| Senaryo | Koşul (gözlenebilir) | Ons bandı | Kaynak |
|---|---|---|---|
| Fiyatlanmış | FOMC piyasa beklentisi kadar artırır ve dot plot medyanı piyasa ima patikasına ±25 bp yakın | mevcut ± 1×(ATR×√5) | ATR'den türet |
| Şahin sürpriz | Beklentiden büyük artırım VEYA 2027 dot medyanı +25 bp ve üstü yukarı revize | aşağı 1–2×(ATR×√5) | ATR'den türet |
| Güvercin sürpriz | Artırım beklentinin altında VEYA 2027 dot medyanı ≥ 25 bp aşağı revize | yukarı 1–2×(ATR×√5) | ATR'den türet |
| Jeopolitik şok | Brent 5 günde +%15 VE reel faiz düşüyor | yukarı 2×(ATR×√5) | ATR'den türet |

- Olasılık sütunu sadece fed funds vadelilerinden türetilebiliyorsa gösterilsin ("piyasa fiyatlaması: %88 25bp / %12 50bp"). Türetilemiyorsa sütun gizlensin.
- Senaryolar birbirini dışlamıyorsa (örnek: şahin Fed + jeopolitik şok aynı anda) bunu ayrı bir "çakışma" satırı olarak göster. Birleştirip tek senaryoya sıkıştırma.
- FOMC günü (karar saatinden sonraki ilk çalıştırmada) gerçekleşen senaryoyu `senaryo_sonuc` alanına yaz.

### C4. Gram/TL katmanı (Türk yatırımcı için asıl görünüm)
- `gram_ayrisim`: 1 gün, 1 hafta ve 1 ay için Δgram% ≈ Δons% + ΔUSDTRY%. UI'da "gram altındaki değişimin ne kadarı ons, ne kadarı kur" şeklinde bar olarak göster.
- `kur_trend`: Son 63 günün USDTRY ortalama aylık değer kaybı. Gram bantlarını üretirken kuru bu trendle ileri taşı ve varsayımı UI'da açıkça yaz: "kur varsayımı: aylık %X".
- Gram destek/direnç seviyeleri = ons seviyeleri × projekte edilen kur. Ayrı ve elle sabitlenmiş TL seviyesi tutma.

### C5. Senaryo karnesi (hisse karnesine benzer)
- `data/altin_gecmis.json`: Her gün TR saatiyle 23:00'teki çalıştırmada `{tarih, ons, teknik_skor, makro_skor, bias, yukari_tetik, asagi_tetik}` kaydını ekle (en fazla 400 kayıt tut).
- 5 ve 20 gün sonra bias'ın doğru çıkıp çıkmadığını hesapla. UI'da "bias isabeti: son 60 sinyalde %X" olarak göster.

---

## D) UI (`renderAltin`) sırası
1. Ons (spot) + gram + tazelik rozeti (TR saati)
2. **FOMC sayacı + dot plot kartı** (dot medyan vs piyasa ima, makas bp, yorum)
3. Teknik skor | Makro skor (yan yana, ayrışma uyarısı)
4. Makro sürücüler tablosu (reel faiz, DXY, 2Y, Brent: değer, 20 günlük değişim, korelasyon)
5. Senaryolar (C3 tablosu + geçersizlik seviyeleri)
6. Gram ayrışımı (ons vs kur)
7. Destek/direnç (ons ve gram)
8. Kritik günler (düzeltilmiş)
9. Kurum hedefleri (revizyon tarihiyle)
10. Haberler (tarihli)
11. Karne

## E) Kabul kriterleri
- [ ] `python scripts/altin_cek.py` yerelde hatasız çalışıyor. FRED veya yfinance kapalıyken de JSON üretiyor, eksik bloklarda "veri yok" yazıyor.
- [ ] 12.11.2026 "Per" olarak görünüyor.
- [ ] 9 Aralık FOMC hem kritik günlerde hem sayaçta görünüyor.
- [ ] Gram fiyatı spot × kur ile hesaplanıyor ve Kapalıçarşı/bankalar arası fiyata ±%0,5 yakın.
- [ ] Hiçbir senaryo tetiği fiyattan 0,5×ATR'den daha yakın değil.
- [ ] Kodda elle yazılmış olasılık yüzdesi yok (`grep -n "%6\|%2\|olasilik" scripts/` ile kontrol et).
- [ ] Haber tarihleri görünüyor.
- [ ] Workflow süresi 12 dakikanın altında.
