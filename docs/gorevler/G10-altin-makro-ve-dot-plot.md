# G10 — Altın: makro sürücüler, FOMC takvimi ve dot plot

**Önkoşul:** G03
**Dokunulacak dosyalar:** `scripts/altin_cek.py`, `scripts/fomc_tarihleri.json`, `index.html` (`renderAltin` veya G06 sonrası `js/bolum/altin.js`)
**Ayrıntı:** `docs/analiz/altin_yonerge.md` → yalnızca "B) YENİ VERİ KATMANI" bölümü

## Veri (`altin.json → makro`), hepsi anahtarsız
- **FRED CSV** (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=SERI`) serileri: `DGS2`, `DGS10`, `DFII10` (reel 10Y), `T10YIE`, `DFEDTARU`, `DFEDTARL`, `FEDTARMD` (SEP medyanı = dot plot).
- **yfinance:** `DX-Y.NYB` (DXY), `BZ=F` (Brent). WTI ile karıştırma, ayrı alan olsun.
- Her seri için: son değer, 5/20 günlük değişim, ons ile 60 günlük rolling korelasyon.

## Dot plot kartı (`makro.dot_plot`)
- `FEDTARMD` son SEP medyanları (yıl bazında) ve bir önceki SEP ile fark.
- **Piyasa ima patikası:** fed funds vadelileri (`ZQ=F` ve ilgili kontrat ayları, ima faiz = 100 − fiyat). Çekilemezse proxy olarak 2Y − mevcut faiz kullan ve "proxy" etiketiyle göster.
- `makas_bp = (piyasa − dot) × 100`. Deterministik yorum:
  - +25 bp üstü → "piyasa Fed'den şahin"
  - −25 bp altı → "piyasa Fed'den güvercin"
  - arada → "uyumlu"
- **SEP karşılaştırması:** Yeni SEP yayınlandığında (Mart, Haziran, Eylül, Aralık) 2027 medyanının değişimi ≥ +25 bp ise "şahin revizyon", ≤ −25 bp ise "güvercin revizyon".

## FOMC sayacı
"Sonraki FOMC: tarih · saat TSİ · N gün · SEP var/yok".
- Karar saati: 14:00 ET → TSİ'ye çevirirken ABD yaz saatini hesaba kat. Sabit "22:00" yazma.

## Kabul kriterleri
- [ ] FRED erişilemezse makro bloğu `"durum":"veri yok"` yazıyor, diğer altın blokları etkilenmiyor.
- [ ] Kodda elle girilmiş faiz, olasılık veya hedef değeri yok.
- [ ] Sayaç 9 Aralık 2026 için doğru TSİ saatini gösteriyor.
