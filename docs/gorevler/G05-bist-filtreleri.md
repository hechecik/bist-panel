# G05 — BIST'e özgü filtreler: geçici/kesin sinyal, tavan/taban, likidite, halka arz

**Önkoşul:** G02
**Dokunulacak dosyalar:** `scripts/veri_cek.py`, `scripts/indikatorler.py`, `index.html` (sinyal kartları), `tests/`

## Neden (ölçüldü)
- Gün içinde sinyalin %8'i kapanışta değişiyor. 15 dakikalık çalışmalar, kapanmamış barı tamamlanmış günlük bar gibi işliyor.
- ±%10 tavan serilerinde "ertesi gün açılıştan al" fiilen gerçekleşmez, ama backtest bu işlemleri dolmuş sayıyor.

## Adımlar
1. **Geçici/kesin ayrımı:**
   - TR saatiyle 18:15'ten önce üretilen sinyallere `durum: "gecici"`, sonrasında üretilenlere `"kesin"` yaz.
   - UI'da geçici sinyaller soluk ve "⏳ geçici (seans sürüyor)" rozetiyle gösterilsin.
   - `sinyal_gecmisi_guncelle` sadece kesin sinyalleri kaydetsin.
2. **Tavan/taban kilidi:** `kilit_tespit(row, onceki_kapanis)` adında saf bir fonksiyon yaz.
   - Değişim ≥ +%9,5 ve kapanış == gün yükseği ise `TAVAN`.
   - Değişim ≤ −%9,5 ve kapanış == gün düşüğü ise `TABAN`.
   - Backtest'te kilitli günde giriş ve çıkış yapılmasın, bir sonraki kilitsiz güne kaydırılsın.
   - UI'da 🔒 rozeti göster.
3. **Likidite:**
   - 20 günlük ortalama TL hacmi = ortalama(kapanış × hacim).
   - `LIKIDITE_ESIK_TL = 50_000_000` (parametre olsun, kodun en üstünde tanımlı).
   - Eşiğin altındaki hisselere AL/SAT üretme, `sinyal: "IZLE"` yaz.
4. **Halka arz:** `data/takvim.json → halka_arz` içinde son 60 iş günü içinde işlem görmeye başlayan hisselere `ipo_yeni: true` ekle. Bunlar skor istatistiklerinden hariç tutulsun.
5. **VBTS tedbirleri (isteğe bağlı):**
   - Ağsız bir kaynak bulunabiliyorsa (KAP veya BIST duyuru sayfası) tedbirli hisse listesini çek, `tedbir` alanına yaz ve sinyal üretme.
   - Kaynak bulunamazsa uydurma. Raporda "VBTS kaynağı bulunamadı" yaz.
6. **Sorunlu hisse filtresi:** Yakın İzleme Pazarı'ndaki, konkordato/iflas bildirimi olan veya son 10 günde ≥3 taban kilidi yaşayan hisselere AL sinyali üretme, sinyal: 'RISKLI' yaz, UI'da ⛔ rozeti göster. Backtest'te taban kilitli günde çıkış yapılamaz; çıkış ilk kilitsiz güne kaydırılır (stop-loss dahil).

## Kabul kriterleri
- [ ] `tests/test_filtreler.py`: kilit tespiti ve likidite eşiği için en az 4 test.
- [ ] `piyasa.json` içindeki sinyal kayıtlarında `durum` alanı var.
- [ ] Backtest'te kilitli günde açılmış işlem yok (testle doğrula).
