# G07 — Python kodunu paketleme ve veri dosyalarını bölme

**Önkoşul:** G06
**Dokunulacak dosyalar:** `scripts/`, `data/`, `.github/workflows/veri-cek.yml`, `js/bolum/*.js`

## Hedef yapı
```
scripts/ortak.py          log, utc_now_iso, json_yaz, HEADERS
scripts/kaynak/           isyatirim.py borsapy_tv.py yahoo.py tcmb.py doviz.py rss.py
scripts/analiz/           indikator.py sinyal.py backtest.py temel.py ict.py
scripts/gorev/fiyat.py    15 dk: OHLCV + endeks + makro + sinyal → data/fiyat.json, data/sinyal.json, log
scripts/gorev/gunluk.py   18:30 TR: backtest, karne, ICT, gece analizi → data/backtest.json, data/ict.json
scripts/gorev/haftalik.py Cumartesi: temel analiz, sektör haritası → data/temel.json
```

## Kurallar
- Eski `scripts/veri_cek.py` geçiş süresince kalsın, yeni modülleri import eden ince bir sarmalayıcıya dönüşsün.
- `data/piyasa.json` bir sürüm boyunca üretilmeye devam etsin (geriye uyumluluk). UI yeni dosyalara geçtikten sonra kaldırılsın.
- Workflow'ları sıklığa göre ayır: `veri-cek` (fiyat), `gunluk-cek`, `haftalik-cek`.
- Her yeni JSON için `schema/<ad>.json` (JSON Schema) yaz. Ajanlar veri dosyası yerine bu şemayı okur.

## Kabul kriterleri
- [ ] Hiçbir Python dosyası 20 KB'ı geçmiyor.
- [ ] `pytest` testlerinin tamamı geçiyor. `tests/` içindeki import'lar yeni yollara göre güncellendi.
- [ ] UI bütün sekmelerde aynı veriyi gösteriyor.
- [ ] `AGENTS.md` dosya haritası güncellendi.
