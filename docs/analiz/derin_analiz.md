# Derin analiz — sinyal denetimi (11 Kasım 2026)

*11 Kasım 2026 · Bu bir yatırım tavsiyesi değildir, sistemin kendi çıktılarının ölçümüdür.*

Önceki iki yönergede yaptığım şey, kodu okuyup hata ve eksik listesi çıkarmaktı. Bu belgede **sistemin kendi geçmiş çıktılarını ölçtüm**. Sorduğum soru şu: "AL dediği hisseler, SAT dediklerinden gerçekten daha iyi gitti mi?"

---

## 1. Yöntem

- **Veri:** `data/piyasa.json`'un git geçmişindeki **135 snapshot** (23 Ağustos – 10 Kasım 2026, 41 işlem günü).
- **Fiyat paneli:** Her snapshot'taki hisse başına 30 kapanış (spark) BIST takvimine hizalandı. 100 hisse için günlük kapanış paneli yeniden kuruldu: 101.985 nokta tutarlı, 1.481 nokta çakışık (%1,4). Çakışmaların kaynağı gün içi snapshot'ların kapanıştan farklı olması; her gün için son değer esas alındı.
- **Bölünme filtresi:** Günlük ±%30'dan büyük sıçramalar dışlandı. 3 vaka çıktı: RALYH −%40, REEDR −%33, KLRHO −%46.
- **Hedef değişken:** 1, 5 ve 10 iş günü sonraki getiri, **piyasaya göre fazla getiri** olarak (aynı günün eşit ağırlıklı evren ortalaması). XU100 ile de kontrol edildi.
- **İstatistik:**
  - Gün bazında kesitsel ortalama ve Spearman IC (özellik sırası ile ileri getiri sırası arasındaki korelasyon).
  - t-istatistiği **örtüşmesiz** pencerelerle hesaplandı (5 günlük ufukta her 5. gün). Örtüşen pencereler t değerini yapay olarak şişirir.
- **Araç:** `scripts/sinyal_denetim.py` (yamada var). Ağ bağlantısı gerektirmez, `--git .` veya `--log data/log` ile çalışır.

### Sınırlar (önemli)
- Sadece 41 gün var. 5 günlük ufukta bu **~8 bağımsız gözlem** demek. Hiçbir bulgu istatistiksel kanıt düzeyinde değil, sadece **yön** gösteriyor.
- Geçmişte sadece listelenen hisseler (al/tut/sat, ~27 tane) kaydedilmiş. Kesit kırpılmış.
- Dönem çoğunlukla düşen bir piyasa. Momentum/mean-reversion dengesi rejime göre değişebilir.
- Bu yüzden ilk iş ölçüm altyapısını kurmak (§6).

---

## 2. Bulgular

### 2.1 Skor, AL'ı SAT'tan ayırmıyor
| Ufuk | AL (skor ≥ 2) − SAT (skor ≤ −2), günlük ort. | t (örtüşmesiz) |
|---|---|---|
| 1 gün | +%0,46 | +1,61 |
| 5 gün | +%0,26 | −0,21 |
| 10 gün | +%2,06 | +1,85 |

XU100'e göre 5 günlük sonuç: **AL tarafı −%2,35, SAT tarafı −%2,24**. İkisi pratikte aynı. Sistemin asıl iddiası olan "AL dediğim SAT dediğimden iyi" bu örneklemde görülmüyor.

### 2.2 Skor monoton değil
5 günlük fazla getiri: skor 1 → **+%1,79**, skor 2 → +%0,26, skor 3 → +%0,93, skor −2 → −%0,24. İyi çalışan bir skorda getiri skorla birlikte düzenli artmalı. Burada skor 1, skor 3'ten iyi. Bu da puanlamanın sıralama yapmadığını gösteriyor.

### 2.3 Sistem kendi verisiyle çelişiyor: RSI kuralı ters çalışıyor
| Özellik | IC 5 gün | IC 10 gün | Sistemdeki kural |
|---|---|---|---|
| RSI | **+0,085** | **+0,155** | RSI < 30 → **+1**, RSI > 70 → **−1** (dipten al) |
| MACD hist / fiyat | +0,071 | +0,104 | MACD > sinyal → +1 |
| 1 aylık getiri | +0,077 | +0,100 | (skorda yok) |
| MFI | −0,032 | +0,019 | MFI > 55 → +1 |
| **Toplam skor** | **+0,039** | +0,071 | — |

- Pozitif IC şu demek: **RSI'ı yüksek olan hisseler sonra daha iyi gitti** (momentum). Sistem ise tersini varsayıyor (mean reversion).
- RSI < 30 olan hisselerin piyasaya göre fazla getirisi: 5 günde **−%4,7**, 10 günde **−%9,9**. Sistem bu hisselere "dip fırsatı" diyerek +1 puan veriyor.
- **Asıl sorun bileşenlerin birbirini götürmesi.**
  - Momentum bileşenleri: trend ±2, MACD ±1, Stoch ±1.
  - Mean-reversion bileşenleri: RSI uçları ±1, Bollinger alt/üst bant ±1.
  - Bu iki grup birbirine zıt sinyal veriyor. Sonuç olarak toplam skorun IC'si (0,039), **tek başına RSI'ın (0,085) ve MACD'nin (0,071) yarısı kadar**. Skor, en iyi bileşeninden daha kötü bilgi taşıyor.

### 2.4 Sinyal gürültülü ve vadesi tutarsız
- Ardışık günlerde sinyal değişimi **%34** (440/1301). AL ↔ SAT arasında doğrudan dönüş 59 kez.
- Aynı gün içinde sinyalin değişme oranı **%8**. Sebep: 15 dakikalık çalışmalar gün içindeki yarım barı tamamlanmış günlük bar gibi işliyor. Kapanış seansında (18:00–18:10) fiyat değişince sinyal de değişiyor.
- Ortalama sinyal ömrü ~3 gün. Ama stop (2×ATR) ve hedef (3×ATR) ~10–20 günlük harekete göre kurulu. Vadeler birbiriyle uyuşmuyor. Gidiş-dönüş ~%0,2 maliyetle bu kadar sık değişen bir sinyal kârı yer.

### 2.5 Operasyonel boşluk
- **10 Ekim – 4 Kasım arasında hisse verisi hiç güncellenmemiş** (25 gün, 0 commit). Altın ve kripto görevleri çalışırken hisse görevi durmuş.
- `sinyal_gecmisi` 45 günlük pencere tutuyor. Bu boşluk karnenin yarısını boş bırakmış.
- Sistemde bu kesintiyi fark edecek bir alarm yok.

---

## 3. Neden böyle? Tasarım eleştirisi

1. **Ağırlıklar ve eşikler doğrulanmadan seçilmiş.** "RSI < 30 al" ders kitabı kuralı. Ama BIST'te bu dönemde momentum baskındı. Doğrulanmamış her kural bir hipotezdir, ve sistem bu hipotezleri karne kurmadan ürüne koymuş.
2. **Mutlak sinyal, göreli karar.**
   - Yatırımcının asıl sorusu "bu hisse yükselir mi" değil, "bu hisse alternatiflerinden iyi gider mi".
   - Düşen piyasada AL listesinin tamamı XU100'ün altında kaldı.
   - Hedef değişken **endekse göre fazla getiri** olmalı. Sinyal de kesitsel sıralama olmalı.
3. **Enflasyon kayması.**
   - Yıllık TÜFE %29,8, yani TL fiyatlarda ayda ~%2,2 nominal kayma var.
   - MA ve trend göstergeleri bunun bir kısmını "trend" diye ölçüyor. Nominal TL bazında "fiyat MA50 üstünde" sinyali kısmen sadece enflasyonu yakalıyor.
   - Göreli güç (hisse/XU100) bu kaymayı otomatik olarak temizler.
4. **Korelasyonlu göstergeler fazla oy kullanıyor.** MACD, Stoch RSI ve trend aynı şeyi (momentum) ölçüyor ve toplam 4 puan taşıyor. Hacim ve volatilite gibi bağımsız boyutlar skorda hiç yok.
5. **Gün içi veriyle günlük sinyal üretiliyor.** Kapanmamış barla hesaplanan RSI, MACD ve Bollinger değerleri geçici. Ama UI bunları kesin sinyal gibi gösteriyor.

---

## 4. BIST mikro yapısı — sistemin hiç hesaba katmadığı noktalar

| Konu | Neden önemli | Öneri |
|---|---|---|
| **±%10 fiyat marjı (tavan/taban)** | Ardışık tavan serisinde "ertesi gün açılıştan al" fiilen gerçekleşmez (alıcı kuyruğu). Backtest bu işlemleri dolmuş sayıyor. | Tavan/taban kilitli günleri tespit et (kapanış = gün yükseği/düşüğü ve ±%9,5 üstü). Bu günlerde giriş/çıkış yok say. |
| **VBTS tedbirleri** (brüt takas, kredili işlem yasağı, açığa satış yasağı, tek fiyat, emir paketi) | Tedbirli hissede likidite ve fiyat oluşumu bozuk. Teknik sinyal anlamsız. | Tedbir listesini KAP/BIST duyurularından çek. Tedbirli hisseye sinyal üretme, ⚠️ rozeti göster. |
| **Kapanış seansı (tek fiyat)** | Gün içi sinyalin %8'i kapanışta değişiyor (ölçüldü). | Sinyaller kapanış sonrasında "kesin", seans içinde "geçici" rozetiyle gösterilsin. Karneye sadece kesin sinyaller yazılsın. |
| **Survivorship** | `bist100.txt` bugünkü bileşim. Bu listeyle 1 yıl geriye backtest yapınca, endekse yükselerek giren hisseler geriye dönük de evrende sayılıyor. Sonuçlar iyimser çıkar. | Tarihli bileşen listesi tut (`bilesen/2026Q4.txt`). Backtest her tarih için o tarihteki listeyi kullansın. |
| **Bedelsiz/temettü** | Örneklemde 3 bölünme, 100 hissede 3 ay içinde. BIST'te bu sık. | Düzeltilmiş seri kullan + sıçrama dedektörü + KAP'tan bedelsiz oranıyla çapraz kontrol. |
| **Likidite** | Düşük hacimli hissede kayma maliyeti sinyal getirisini aşar. | 20 günlük ortalama TL hacmi eşiğin altındaki hisselere sinyal üretme. Eşiği karneyle kalibre et. |
| **Halka arz sonrası ilk ~60 gün** | Fiyat oluşumu farklı (tavan serileri, kilit açılışları). | Ayrı etiketle ve skor istatistiğine katma. |
| **Endeks dönem değişimleri** | BIST100'e giriş/çıkış dönemlerinde zorunlu fon akışı oluşur. | Takvime ekle. Dahil/çıkar adaylarını işaretle. |

---

## 5. Yeniden tasarım önerisi: kesitsel sıralama modeli

**Hedef:** 10 iş günü sonraki XU100'e göre fazla getiri.

**Özellikler:** Her gün 100 hisse içinde **yüzdelik sıraya** çevrilir. Bu sayede ölçek, enflasyon ve rejim farkları normalize olur.

| Özellik | Tanım | Bu örneklemdeki işaret |
|---|---|---|
| RS20, RS60 | hisse/XU100 oranının 20/60 günlük değişimi | 1 aylık getiri IC +0,08…+0,10 |
| Trend uzaklığı | (fiyat − MA50) / ATR | — |
| Momentum | MACD hist / ATR | +0,07…+0,10 |
| RSI (sürekli değer, uç kuralı değil) | RSI14 | +0,09…+0,16 |
| Hacim oranı | hacim / 20 günlük medyan | (log'la ölçülecek) |
| Volatilite | 20 günlük günlük getiri std (düşük vol anomalisi) | (log'la ölçülecek) |
| 52 haftalık zirveye uzaklık | fiyat / 52h zirve | (log'la ölçülecek) |

**Birleştirme:**
- Başlangıçta **eşit ağırlıklı sıra ortalaması** kullanılır.
- Bir özellik ancak 120 günlük kayan pencerede IC işareti tutarlıysa modele girer.
- Ağırlıklar otomatik optimize edilmez, 6 ayda bir elle gözden geçirilir. Az veriyle optimizasyon aşırı uyum (overfit) demektir.

**Sinyal:**
- Sıralamada üst %20 → "güçlü", alt %20 → "zayıf".
- **Haftalık yeniden sıralama** (Cuma kapanışı). Günlük %34'lük değişim ~%10'a iner, maliyet düşer.

**Rejim filtresi:** XU100 MA50'nin altındaysa "güçlü" listesi gösterilir ama "piyasa rejimi zayıf" uyarısı eklenir. Sermaye simülasyonunda nakit ağırlığı artar.

**Doğrulama protokolü (karne):**
- Walk-forward: 6 ay geçmiş → 1 ay test → bir ay kaydır.
- Maliyet: gidiş-dönüş %0,2. Tavan/taban ve tedbir filtreleri açık.
- Metrikler: ortalama IC, **IC_IR** (IC ort / IC std), üst-alt %20 getiri farkı, isabet, max drawdown, devir oranı.
- **Kabul eşiği:** ≥ 6 test ayında IC_IR > 0,3 ve üst-alt farkı > 2× maliyet. Bu eşik geçilmeden "AL/SAT" yerine "izleme listesi" ifadesi kullanılsın.

**Mevcut skoru hemen değiştirmeyin.** Bu örneklem (41 gün) RSI kuralını tersine çevirmek için yeterli değil. Doğru adım: önce §6'daki log'la ≥ 120 gün tam kesit veri biriktirmek, sonra aynı aracı tekrar çalıştırmak. Bu süre boyunca eski skor ile yeni sıralama modeli **yan yana** hesaplanır, karne ikisini karşılaştırır.

---

## 6. Ölçüm altyapısı (yamada uygulandı)

- `data/log/YYYY-MM.jsonl`: Her işlem günü için **tek satırda 100 hissenin tamamı** (fiyat, skor, sinyal, RSI, MFI, MACD, squeeze, 1 aylık getiri, stop, hedef).
  - Gün içi çalışmalar aynı günün satırının üzerine yazar, böylece günün son satırı kapanış durumu olur.
  - Boyut ~12 KB/gün, ~3 MB/yıl.
- `scripts/sinyal_denetim.py --log data/log --ufuk 5 10 20`: IC, AL−SAT farkı, RSI kuralı testi ve kararlılık raporu üretir. Bu çıktı karne sekmesine bağlanmalı.
- **Kesinti alarmı (önerilir):** Ücretsiz healthchecks.io'ya her başarılı çalışmanın sonunda ping at. 1 iş günü ping gelmezse e-posta gelir. 25 günlük boşluk böyle fark edilir. UI'da da `uretildi` alanı 1 iş gününden eskiyse kırmızı bant gösterilsin.

---

## 7. Önceki yönergelerimdeki hatalar ve eksikler
- **Altın yönergesindeki makro skor eşikleri** (reel faiz ±10 bp, DXY ±%1, Brent ±%10) da doğrulanmamış keyfi eşiklerdi. Hisse skorundaki sorunun aynısı. Altın skoru da aynı log + IC denetiminden geçmeli.
- **Genel yönergede "tüm workflow'lar tek concurrency grubunda" önerisi hatalıydı.** GitHub bir grupta sadece bir bekleyen çalışma tutar, bu yüzden görevler birbirini iptal ederdi. Yamada her workflow kendi grubunda.
- **"Skor bağımsızlığı" önerisi** veri olmadan yapılmıştı. Ölçüm, sorunun sadece korelasyon değil **yön çelişkisi** olduğunu gösterdi (§2.3).
- **Survivorship, tavan/taban, VBTS ve kapanış seansı** konularına hiç değinmemiştim. Bunlar BIST'e özgü ve backtest sonuçlarını doğrudan değiştiren konular.

---

## 8. Yama: `bist-panel-p0.patch`

Uygulama: `git am bist-panel-p0.patch` · Test: `python -m pytest tests -q` (6/6 geçiyor, ağ bağlantısı gerekmez)

| Değişiklik | Dosya |
|---|---|
| Veri dönemi 6 ay → 1 yıl (SMA200 dolar). SMA200 yoksa kısa trend kullanılır ve `trend_kaynak` alanında etiketlenir | veri_cek.py, indikatorler.py |
| `OBV_EGIM` artık hesaplanıyor | indikatorler.py |
| Kelime sınırlı duygu etiketi ("karar" ≠ "kar", "partisi" ≠ "artış"). Bağlamlı ifadeler eklendi ("faiz artışı" → negatif, "faiz indirdi" → pozitif) | veri_cek.py |
| Sektör, gece analizi ve karne güncel fiyatları **tam kesitten** hesaplanıyor | veri_cek.py |
| Tam kesit günlük log | veri_cek.py |
| UTC-aware zaman damgası. UI eski veriyi de doğru yorumluyor ve saatleri İstanbul saatiyle gösteriyor | veri_cek.py, altin_cek.py, index.html |
| Altın takviminde gün adı kayması düzeltildi, ÜFE eklendi, ADP/LPR tekrarı giderildi | altin_cek.py |
| Haber tarihleri görünür hale geldi (`yayin_tarihi`) | index.html |
| Workflow başına concurrency | .github/workflows/* |
| Sinyal denetim aracı + ağsız testler | scripts/sinyal_denetim.py, tests/ |

**Yamada olmayanlar** (sonraki adımlar):
- Dış cron tetikleyici. PAT gerektirdiği için bunu senin kurman gerekiyor.
- borsapy serisinde bölünme düzeltmesi. Yamadaki dönem değişikliği bunu çözmez.
- Backtest'in yeniden yazılması (§5).
- Tavan/taban ve VBTS filtreleri.
- Bileşen geçmişi (survivorship).

**İlk çalıştırmada kontrol et:** borsapy TradingView sağlayıcısının `period='1y'` parametresini kabul ettiği log'da görülmeli. Kabul etmezse kod otomatik olarak yfinance'a düşer (o da `1y` destekliyor). Log'da `kaynak=` satırına bak.
