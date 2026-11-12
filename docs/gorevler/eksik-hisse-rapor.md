# Eksik Hisse Raporu — gorev/eksik-hisse

Durum: TAMAMLANDI
Tarih: 2026-11-13
Dal: `gorev/eksik-hisse` (main'den türedi)

> Not: Son commit'lerden `466c879` mesajı "G14" ile etiketlenmişti ama bu commit G14 görevi değil,
> harici tetik bakımıdır. G14 (`docs/gorevler/G14-kap-ve-yabanci-payi.md`) **YAPILMADI**.

---

## 1. Eksik hisse — sorun ve neden

### Tespit
`bist100.txt` 100 hisse içeriyor; `data/log/2026-11.jsonl` son satırında **91 hisse** vardı.

Eksik 9 hisse:
`TRALT, THYAO, GARAN, HALKB, ISCTR, TSKB, TURSG, VESTL, ZOREN`

Fazla hisse yok — yani sorun liste uyuşmazlığı değil, çekim sırasında düşme.

### Kök neden
Canlı teşhis (`borsapy` tam tarama): **100/100 hisse, 43 saniye, hata yok.**
Yani borsapy kalıcı olarak sorunlu değil. Düşmeler çalışma zamanındaki geçici durumlardan
(zaman aşımı, boş yanıt, kısa bar serisi) kaynaklanıyor.

Asıl kusur **görünürlük** eksikliğiydi:
- Hangi hissenin neden düştüğü hiçbir yere yazılmıyordu.
- Sağlık kontrolünün eşiği 80 hisseydi → 91 hisse "OK" görünüyordu, eksiklik sessizce geçiyordu.
- GitHub Actions log'u indirilemedi (`curl` exit 9), bu yüzden CI çalışmasındaki düşme anı
  doğrudan incelenemedi. Bu boşluk artık kod tarafında kapatıldı.

Ek bulgu: 1. kademe kaynak İş Yatırım erişilemez durumda
(`HTTPSConnectionPool(host='public.finance.isyatirim.com.tr')`, 0.3 sn'de vazgeçiyor),
bu yüzden zincir fiilen borsapy'ye kalıyor.

### Düzeltmeler (md. 1)

**a) Düşme nedeni loglanıyor** — `scripts/veri_cek.py`
- `cek_borsapy(bist_list, nedenler=None)` imzası; hisse başına 2 deneme (1 sn arayla).
- Neden sabitleri: `LOG_NEDEN_BOS_YANIT`, `LOG_NEDEN_AZ_BAR`, `LOG_NEDEN_SEMBOL`.
- Log satırı: `EKSİK n hisse: GARAN=az bar (12 bar); THYAO=boş yanıt; ...`

**b) Hisse bazlı yfinance tamamlama** — `cek_yfinance_tek()` + `tamamla_yfinance()`
- Yalnızca borsapy'den gelmeyen hisseler `.IS` ekiyle tek tek çekilir (toplu çağrı yok).
- Her tamamlanan bar satırına `kaynak='yfinance'` yazılır → kaynak izlenebilirliği.
- `hisse_verisi_cek` artık `(hisse_veri, kaynak, eksik_hisseler, nedenler)` döndürür;
  kaynak `borsapy-tv+yfinance` olarak birleşir.
- Mevcut hisselerin verisine dokunulmaz (`kaynak` alanı eklenmez).

**c) Sağlık + UI görünürlüğü**
- `saglik` bloğuna `eksik_hisseler`, `eksik_nedenler`, `kaynak_dagilim` eklendi.
- Eşik düzeltildi: **100 hissenin altı artık `UYARI`** (eskiden 80 altı sorun sayılıyordu).
- `sorunlar` listesine `"3 hisse çekilemedi: GARAN(az bar (12 bar)), ..."` satırı düşer.
- UI: `js/bolum/piyasa.js` → sarı sol çizgili `.notbanner`:
  `⚠️ X hisse çekilemedi: ...` + altında `Kaynak dağılımı: bilinmiyor 97 · yfinance 3`
  (`css/app.css` → `.altnot`, `.notbanner`).

**d) Test** — `tests/test_eksik_hisse.py` (9 test, ağsız)
- 3 hisse zorla düşürülür → UYARI + isim/neden listesi doğrulanır.
- `tamamla_yfinance` yalnızca eksikleri çağırır, `kaynak` alanını yazar, mevcut veriyi bozmaz.
- Sağlık eşikleri (100 OK / 99 UYARI / <50 KRİTİK) ve `kaynak_dagilim` sayımı.

## 2. AL listesi notu (md. 2)

`js/bolum/piyasa.js` → `alNotu(d)`: değerler **`test_senaryolari.metrik`'ten okunur, elle yazılmaz**.
Alfa ≤ 0 veya PF < 1 ise "endeksi geçmiyor" uyarısı basılır.

Canlı çıktı (2026-11-12 verisi):

> Backtest (XU100'e göre): ort. alfa -0,2%, isabet 47,5%, PF 0,98 — skor henüz endeksi geçmiyor; izleme listesi olarak kullanın.

`tabloBolum(baslik, ikon, liste, altNot)` imzasına 4. parametre eklendi
(`js/bolum/piyasa-tablo.js`), yalnızca AL ADAYLARI bölümünde dolu geçiliyor.

`sw.js`: CACHE `bist-panel-v6` → **`bist-panel-v7`** (`js/` ve `css/` değişti).

## 3. Doğrulama

| Kontrol | Sonuç |
|---|---|
| `py_compile scripts/*.py` | OK |
| `pytest tests -q` | **297/297 geçti** |
| Zorla 3 hisse düşürme (canlı borsapy) | neden loglandı, yfinance 3/3 tamamladı, `kaynak=yfinance`, sağlık OK |
| Tam çalıştırma `scripts/veri_cek.py` | `SAĞLIK: OK · hisse=100 · sorunlar=[]` |
| `tam_kesit_log` | `2026-11.jsonl · 2026-11-12 · **100 hisse**` (öncesi 91) |
| `piyasa.json` | 195.590 byte, 17 üst anahtar |
| UI banner (tarayıcı) | `.notbanner` render edildi, sol çizgi `rgb(240,185,11)`, metin doğru |
| UI AL notu (tarayıcı) | `.altnot` sınıfı, metin `test_senaryolari` ile birebir |

## 4. Düzeltme sonrası hisse sayısı

**91 → 100.** Eksik kalan yok.

## 5. Değişen dosyalar

- `scripts/veri_cek.py` — neden logu, 2 deneme, `cek_yfinance_tek`, `tamamla_yfinance`,
  `hisse_verisi_cek` dönüşü, `veri_saglik_kontrolu` (eksik listesi + kaynak dağılımı + eşik)
- `js/bolum/piyasa.js` — `alNotu()`, eksik hisse banner'ı
- `js/bolum/piyasa-tablo.js` — `tabloBolum` alt not parametresi
- `css/app.css` — `.altnot`, `.notbanner`
- `sw.js` — CACHE v7
- `tests/test_eksik_hisse.py` — yeni (9 test)

## 6. Bilinen sınırlar

- İş Yatırım kaynağı erişilemez; 1. kademe fiilen devre dışı.
- GitHub Actions log indirme başarısız (`curl` exit 9) → CI düşme anı incelenemedi;
  artık neden kod tarafında loglanıyor, bir sonraki CI çalışmasında görülecek.
- Backtest alfası negatif (alfa -0,2, PF 0,98) — sinyal kalitesi ayrı bir iş.
