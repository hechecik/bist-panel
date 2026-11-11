# Bakım Raporu — 11.11.2026 (G13 öncesi)

Dal: `gorev/bakim` → main. Merge: `8ec131d`, veri commit'leri `1b0a6ab`, `87357bb`, `2047d05`, `2bf2e72`.

## 1. AGENTS.md temizliği

- `## G11 DÜZELTME` bölümü AGENTS.md'den **silindi**, içeriği `docs/gorevler/G11-rapor.md` dosyasına taşındı (başlık + "AGENTS.md'den taşındı" notu eklendi).
- AGENTS.md'ye kural eklendi (Raporlama kuralı bölümü): *"Raporlar AGENTS.md'ye YAZILMAZ; `docs/gorevler/GXX-rapor.md` dosyasına yazılır ve Telegram'a kısa özet gönderilir."*
- AGENTS.md boyutu: 9.100+ bayt → **4.724 bayt** (6 KB sınırının altında). `grep -c "G11 DÜZELTME" AGENTS.md` = 0.

## 2. Actions sağlık kontrolü

### a) Son çalışmalar (gh run list / API, limit 30, branch main)

| Workflow | Son planlı (schedule) çalışma | Son çalışma | Sonuç |
|---|---|---|---|
| veri-cek | 11.11 **13:24:56 UTC** | 11.11 17:23:44 (elle) | success |
| altin-cek | 11.11 **07:20:10 UTC** | 11.11 17:23:46 (elle) | success |
| kripto-cek | 11.11 **08:07:43 UTC** | 11.11 17:23:47 (elle) | success |
| ek-veri-cek | 11.11 **13:26:46 UTC** | 11.11 17:23:49 (elle) | success |

Geçmiş 30 çalışmanın tamamı `success` — **başarısız (failure) çalışma yok**, dolayısıyla `--log-failed` incelemesi için hata yok.

### b) Bulunan asıl hata: schedule fiilen duruyor (dosya hatası değil)

- Kripto 30 dakikada bir çalışmalıydı; son planlı çalışma **08:07 UTC** → 17:00 itibarıyla **~9 saat / 18 dilim boş**.
- Aynı gün 13:24'ten sonra hiçbir workflow schedule ile tetiklenmemiş; 14:16'daki "veri 14:16 UTC" commit'i **elle (workflow_dispatch)** çalıştırmadan gelmiş, schedule'dan değil.
- 14 günlük geçmişte `repository_dispatch` olayı sayısı **0** → G01'de planlanan cron-job.org harici tetikleyici hiç kurulmamış (repoda tanımlı **secret sayısı 0**).
- `gh run view --log-failed` boş döndü (kırmızı çalışma yok). Yani sorun YAML/script hatası değil, GitHub'ın schedule mekanizmasının bu repoda tetiklenmemesi.

### c) Düzeltme

1. **`tetik-cek.yml` (yeni)** — yedek zamanlayıcı: 10 dakikada bir (`3,13,23,33,43,53`) çalışır, 4 veri akışının son çalışmasına bakar, gecikme eşiği aşıldıysa hedef akışı **doğrudan `workflow_dispatch` ile** çağırır. `permissions: actions: write` yeterli (204 ile doğrulandı), secret gerekmiyor.
2. `repository_dispatch` yerine `workflow_dispatch` kullanıldı: repoda `veri` tipini dinleyen akış yok (ek-veri `[veri, ek]` dinliyor ama olay hiç gönderilmiyordu).
3. **HC ping guard**: 4 workflow'da `secrets.HC_URL_*` boş olduğu için curl boş URL'ye gidiyordu; `if [ -n "$HC" ] ... else "tanimli degil - atlandi"` koruması eklendi.
4. **Sessiz veri kaybı giderildi**: push döngüsü 3 denemede de düşerse artık `exit 1` (ek-veri-cek ve diğerleri eskiden yeşil kalıyordu).
5. Geçici teşhis akışı `af-kontrol.yml` **silindi**.

### d) Elle tetikleme doğrulaması (4/4 success, yeni veri commit'leri main'de)

- veri-cek → run `43067744659` success → **`2bf2e72` veri guncelle 11.11 17:27 UTC** (`data/piyasa.json`, `data/log/2026-11.jsonl`)
- altin-cek → run `43067748247` success → **`2047d05` altin veri guncelle 11.11 17:25 UTC** (`data/altin.json`)
- kripto-cek → run `43067752256` success → **`1b0a6ab` kripto veri guncelle 11.11 17:23 UTC** (`data/kripto.json`)
- ek-veri-cek → run `43067756025` success → **`87357bb` sabit getiri + takvim guncelle 11.11 17:24 UTC** (`data/getiri.json`, `data/takvim.json`)

`tetik-cek` ilk çalışması (run `43067543271`) 4 akışın hepsini "OK" (gecikme yok) raporladı — dispatch göndermedi, çünkü elle tetikleme az önce veriyi tazelemişti.

## Bilinen sınır

`tetik-cek` de GitHub schedule'a bağlı. GitHub schedule bu repoda hiç tetiklenmezse yedek tetikleyici de çalışmaz. O durumda tek çözüm harici bir tetikleyici (cron-job.org → PAT veya `/actions/workflows/tetik-cek.yml/dispatches` çağrısı). Repoda secret tanımlamak gerektiği için kullanıcı onayı bekliyor.

## Testler

`python3 -m py_compile scripts/*.py` ✅ · `python3 -m pytest tests -q` → **260 passed**
