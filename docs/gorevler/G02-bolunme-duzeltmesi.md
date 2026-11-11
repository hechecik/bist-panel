# G02 — Bedelsiz bölünme (split) düzeltmesi

**Önkoşul:** G00
**Dokunulacak dosyalar:** `scripts/veri_cek.py` (`cek_borsapy`, `cek_yfinance`, `veri_saglik_kontrolu`, `test_senaryolari`), `tests/`

## Neden
- Fiyatlar bölünmeye göre düzeltilmemiş. Backtest'te RALYH 273,5 → 5,02 TL (−%98) görünüyor.
- Git geçmişinde 3 bölünme tespit edildi: RALYH −%40, REEDR −%33, KLRHO −%46.
- Bu kırılmalar backtest ortalamalarını, MA/RSI/ATR hesaplarını ve stop-loss sonuçlarını bozuyor.

## Adımlar
1. **Düzeltilmiş seri:**
   - yfinance yolunda `auto_adjust=True` kullan.
   - borsapy/TradingView sağlayıcısında düzeltme parametresi var mı kontrol et: `python3 -c "from borsapy._providers.tradingview import get_tradingview_provider as g; import inspect; print(inspect.signature(g().get_history))"`. Varsa aç.
2. **Sıçrama dedektörü:** `bolunme_tespit(rows) -> list[dict]` adında saf bir fonksiyon yaz.
   - Bir günün kapanışı önceki güne göre ≤ −%30 ise **ve** BIST ±%10 fiyat marjını aşıyorsa bu fiziksel olarak mümkün değildir, yani düzeltilmemiş bir bölünmedir.
   - Oran = önceki kapanış / bugünkü açılış. Bu orandan önceki tüm barları (OHLC ÷ oran, hacim × oran) geriye dönük düzelt.
   - Her düzeltmeyi `saglik.bolunme_duzeltme: [{sembol, tarih, oran}]` alanına yaz.
3. **Uygulama yeri:** Düzeltme, veri çekildikten hemen sonra ve `sinyalleri_hesapla`, `test_senaryolari`, `ict_tara` çağrılmadan önce uygulanmalı.
4. **UI:** Düzeltme uygulanmış hisse kartında küçük bir "⚙️ bölünme düzeltildi (tarih, oran)" notu göster. `grep -n "renderPiyasa" index.html` ile yeri bul.

## Kabul kriterleri
- [ ] `tests/test_bolunme.py`: sentetik seride 1:20 bölünme → düzeltme sonrası maksimum günlük düşüş < %11.
- [ ] Gerçek çalıştırmada `test_senaryolari.ertesi_gun_acilis.en_kotu.getiri_yuzde` > −%60 (ya da düzeltme listesinde gerekçesi var).
- [ ] `pytest` testlerinin tamamı geçiyor.

## Yapma
- Bölünme oranını elle girme.
- %30 eşiğinin altındaki gerçek düşüşleri "düzeltme". BIST'te günlük marj ±%10, bu yüzden −%10 ile −%30 arası düşüşler gerçek olabilir.
