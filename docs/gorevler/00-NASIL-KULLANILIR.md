# Ajanla çalışma rehberi (Gor için — ajan bu dosyayı okumaz)

## Kurulum (bir kez)
1. `G00-manuel-hazirlik.md` adımlarını terminalde uygula: yamalar, Hermes zaman aşımı, yedek sağlayıcı.
2. Hermes'in çalışma dizininin repo kökü olduğundan emin ol. Böylece `AGENTS.md` her oturumda otomatik yüklenir.

## Her görev için Telegram akışı
```
/new
G03
```
Bu kadar. `AGENTS.md` ajana "G03 → docs/gorevler/G03-*.md dosyasını oku" demeyi zaten öğretiyor.

İstersen daha açık yazabilirsin:
```
/new
docs/gorevler/G03-altin-kalan-hatalar.md dosyasını oku ve uygula. Bitince AGENTS.md'deki rapor formatıyla yaz.
```

**Kurallar:**
- Her görev **yeni oturumda** (`/new`). Biriken bağlam hem yavaşlatır hem token yer.
- Ajan dalı push edince GitHub'da diff'e bak, sonra merge et (ya da ajana "merge et" de).
- Büyük görevlerde (G06, G07) ajan bölüm bölüm ilerler. Kaldığı yerden devam etmesi için `G06 devam` yaz.
- Ajan takılırsa `/new` ile yeni oturum aç ve aynı görevi tekrar ver. Görev dosyası adım adım olduğu için yarım kalan iş `git log` üzerinden anlaşılır.

## Önerilen sıra
| Sıra | Görev | Süre/zorluk | Not |
|---|---|---|---|
| 0 | G00 | 10 dk, manuel | Token harcamaz |
| 1 | G01 | Küçük | Sonra cron-job.org + healthchecks'i sen kuracaksın |
| 2 | G02 | Orta | Backtest'i düzeltir |
| 3 | G03 | Küçük | Altın hataları |
| 4 | G04 | Küçük | Veri tutarlılığı |
| 5 | G05 | Orta | BIST filtreleri |
| 6 | G09 | Orta | Gölge göstergeler, log birikmeye başlar |
| 7 | G10 → G11 | Orta | Altın makro + senaryo |
| 8 | G13 | Orta | Reel BIST + TR risk |
| 9 | G08 | Orta-büyük | Backtest yeniden |
| 10 | G06 → G07 | Büyük, çok oturum | Token tasarrufu. Erken yapmak istersen G01'den sonra da olur |
| 11 | G12, G14 | Orta | Kaynak doğrulama ağırlıklı |
| 12 | G15 | 120 işlem günü log birikince | Yaklaşık Mayıs 2027 |

## Görev dosyası boyutları
Her görev 2–4 KB, `AGENTS.md` ~5 KB. Ajan bir görevde ~10 KB talimat okur, eski 72 KB'lık birleşik dosya yerine.
