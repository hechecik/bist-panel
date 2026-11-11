# G09 — Teknik Eklemeler (Gölge Mod)

## Özet
6 yeni teknik gösterge ve piyasa genişliği verisi eklendi. Hepsi **gölge mod**: hesaplanıp log'a yazılıyor ve ekranda gösteriliyor, fakat **skor/sinyal hesabına girmiyor**.

## Değişen dosyalar

**`scripts/indikatorler.py`** (+115) — 7 yeni saf fonksiyon, ağa çıkmaz:
- `rs_serisi(close, endeks)` — hisse/endeks oran serisi
- `rs_degisim(close, endeks, n)` — RS-n: oranın n günlük % değişimi
- `hacim_orani(volume, n=20)` — hacim / 20g medyan
- `vol20(close, n=20)` — 20g günlük getiri std (%)
- `zirve_uzak(close, n=252)` — kapanış / 252g en yüksek − 1 (%)
- `trend_atr(close, sma50, atr14)` — (kapanış − SMA50) / ATR14
- `genislik_hesapla(seriler)` — piyasa genişliği

**`scripts/veri_cek.py`** (+82/−7):
- `endeks_verisi()` — `seri` (tam kapanış serisi) + `seri_son` (son 80 gün) eklendi. **Eski alanlar (`deger`/`degisim_yuzde`/`tarih`) aynen korundu.**
- `golge_gostergeler(df, endeks)` — yeni fonksiyon; RS için hisse/endeks serileri **tarih bazlı** hizalanır (tatil günü kayması olmaz)
- `sinyalleri_hesapla(hisse_veri, ipo=None, endeks=None)` — sadece opsiyonel parametre eklendi, **gövde değişmedi**
- `alanlar` tuple'ına 6 alan eklendi → `tam_kesit_log` satırlarına yazılıyor
- Satır dict'e `**golge_gostergeler(...)` — sinyal hesabından **sonra** spread edilir
- "5h2" bloğu: `piyasa.json` → `genislik` (bağımsız `try/except`; düşerse diğer bloklar yazılmaya devam eder)

**`scripts/sinyal_denetim.py`** (+7) — `ozellikler` dict'ine 6 gösterge; IC ölçümü buradan yapılır.

**`index.html`** (+36) — hisse tablosunda **RS20** ve **Hacim** kolonları (RS20 renkli, hacim oranı ≥2× yeşil / ≤0.6× soluk), kart detayında 6 göstergenin tamamı, piyasa sekmesinde **📐 Piyasa Genişliği** kartı, CSV export'a 6 kolon.

**`tests/test_g09_golge.py`** (yeni, +27 test) — her gösterge için sentetik veri testi, `golge_gostergeler` sarmalayıcısı, `genislik_hesapla`, ve skor/sinyal dokunulmazlık testleri.

## "Skor/sinyal kodunda değişiklik yok" — git diff doğrulaması

`git diff -U0 scripts/` çıktısındaki **silinen satırların tamamı**:

| Silinen | Yerine gelen |
|---|---|
| `def sinyalleri_hesapla(hisse_veri, ipo=None)` | `(..., endeks=None)` — opsiyonel parametre |
| `'squeeze', 'ay_oncesi', 'stop', 'hedef')` | aynı + 6 gölge alan |
| `endeks_verisi` docstring satırı | docstring genişletildi |
| `sinyalleri_hesapla(hisse_veri, ipo)` çağrısı | `(hisse_veri, ipo, endeks)` |

Silinen **hiçbir satır skor/sinyal mantığı içermiyor**. `sinyal_hesapla` ve `skor` hesaplayan gövde hiç değişmedi; `golge_gostergeler` çıktısında `skor`/`sinyal`/`stop`/`hedef` anahtarı yok — sızma yapısal olarak imkânsız (test ile de doğrulandı).

## Test durumu
- Baseline: 109 test geçiyordu
- Şimdi: **136 test geçiyor** (109 mevcut + 27 yeni), hiçbiri değiştirilmedi
- Komut: `.venv/bin/python -m pytest tests -q`

Test yazarken 2 hata çıktı, ikisi de **test verimden** kaynaklıydı (kod hatası değil): `range(100,121)` +%20'lik seri üretiyordu (+%10 bekliyordum) ve tamamen sabit seri kendi maksimumuna eşit olduğu için 52h zirve sayılıyordu — bu doğru davranış. Fixture'lar düzeltildi.

## Notlar
- Hesaplanamayan değerlerde `None` döner — uydurma yok. 252 bar altı geçmişi olan hissede 52h zirve/dip sayılmaz, 50 bar altında MA50 üstü hesabı yapılmaz.
- `data/*.json` commit'e katılmadı.
- Branch: `gorev/G09`. **main'e merge edilmedi** — onay bekleniyor.
