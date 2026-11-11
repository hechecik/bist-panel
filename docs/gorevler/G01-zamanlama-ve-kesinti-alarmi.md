# G01 — Zamanlama güvenilirliği + kesinti alarmı

**Önkoşul:** G00 (yamalar uygulanmış olmalı)
**Dokunulacak dosyalar:** `.github/workflows/*.yml`, `index.html` (sadece tazelik bandı kısmı)

## Neden
- Hisse görevi 15 dakikada bir planlı ama gerçekte günde ~2 kez çalışıyor. Altın ve kripto görevleri günde 48 yerine 3–5 kez çalışıyor.
- 10 Ekim – 4 Kasım arasında hisse verisi **25 gün hiç güncellenmedi** ve kimse fark etmedi.

## Adımlar
1. **Push döngüsü:** Her workflow'un commit/push adımındaki tek `git push`'u 3 denemelik bir döngüyle değiştir:
   ```bash
   for i in 1 2 3; do
     git fetch origin && git rebase origin/main --autostash && git push && break
     git rebase --abort 2>/dev/null; sleep $((i*10))
   done
   ```
2. **Cron dakikalarını kaydır:** :00/:15/:30 gibi yoğun dakikalardan uzaklaştır. Örnek: `*/15` → `7,22,37,52`, `*/30` → `11,41`.
3. **Dış tetikleyiciye hazırlık:** Her workflow'da `workflow_dispatch:` olduğunu doğrula. Ayrıca `repository_dispatch: {types: [veri, altin, kripto]}` tetikleyicisini ekle.
4. **Kesinti alarmı:**
   - Her workflow'un sonuna ekle: `if: success()` → `curl -fsS -m 10 "${{ secrets.HC_URL_<GOREV> }}" || true`
   - Secret tanımlı değilse adım sessizce geçsin.
5. **UI bayat bandı:**
   - `index.html` içinde `utcTarih(d.uretildi)` ile hesaplanan yaş hafta içi 1 iş gününden büyükse sayfanın üstünde kırmızı bant göster: "⚠️ Veri X saattir güncellenmedi".
   - Altın verisi 2 saatten eskiyse aynı bandı göster.
6. **Site açıklaması:** `<meta name="description">` ve başlıktaki "15 dk gecikmeli, seans boyunca canlı" ifadesini "seans içinde periyodik güncellenir" olarak değiştir.

## Kabul kriterleri
- [ ] 4 workflow'un hepsinde yeniden denemeli push döngüsü var.
- [ ] YAML geçerli: `python3 -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]"`
- [ ] Bant, `uretildi` alanı 2 gün geriye alındığında görünüyor. Elle test et, sonra eski haline döndür.

## Kullanıcıya bildirilecek (rapora ekle)
- cron-job.org'da 15 dakikalık bir iş oluşturulmalı. İstek: `POST https://api.github.com/repos/hechecik/bist-panel/dispatches`, gövde: `{"event_type":"veri"}`. Header: fine-grained PAT (sadece bu repo, Actions: write + Contents: read).
- healthchecks.io'da her görev için bir check açılmalı ve URL'leri GitHub Secrets'a `HC_URL_VERI`, `HC_URL_ALTIN`, `HC_URL_KRIPTO` adlarıyla eklenmeli.
