# G11 Raporu — Gram ayrışımı pencereleri + tek yön bant gösterimi

> AGENTS.md'den taşındı (bakım işi, c3161c0 sonrası). G11 görevinin düzeltme raporu.

**Hata (bulundu ve düzeltildi):** `donem_degisimleri()` çağrıları yanlış iş günü pencereleriyle
yapılıyordu: `1h = 21` bar (~1 ay), `1a = 252` bar (~356 takvim günü ≈ **1 yıl**). Bu yüzden
1a kur değişimi %18,62 çıkıyordu — aylık varsayım %1,65 iken imkânsız (≈11 aylık birikim).
Hizalama da index bazlıydı; USDTRY serisinde boşluk olduğunda ons ile aynı tarihe denk gelmiyordu.

**Düzeltmeler:**
1. `DONEM_BAR = {'1g': 1, '1h': 5, '1a': 21}` — pencereler iş günü bazında tanımlandı.
2. `_tarih_key()`, `_seri_eslestir()` — ons ve kur serileri **TARİHE** göre hizalanır; bir seride
   tarih yoksa en yakın **önceki** tarih kullanılır, `HIZALAMA_TOLERANS_GUN = 5` günden eskiyse
   "veri yok" döner (uydurma yok).
3. `gram_serisi()` — ons ve kurdan **BAĞIMSIZ** gram serisi üretir; `gram_gercek_kontrol()` gerçek
   gram değişimini bu seriden alır, böylece aynı pencere hatası tekrarlanmaz.
   Sapma paydası: `tolerans = 0.2 + |Δons%·Δkur%|/100` (yaklaşık formülün karesel çapraz terimi).
4. `kur_tutarlilik_uyarisi()` — pencere kur değişimi, aylık varsayımın `KUR_UYARI_KAT = 3`
   katından büyükse `⚠️` uyarı üretir (eşik %4,953); ayrışma çıktısına `tutarlilik` alanı eklendi.
5. Jeopolitik şok satırı yönü "yukarı" iken artık tek yön gösterilir: `bant_gosterim = [üst, üst]`
   → arayüzde "≈ 4406$ (tek yön)"; şahin (alt) / güvercin (üst) satırlarıyla tutarlı.

**Düzeltilmiş canlı değerler (2026-11-11, ons 4007,00 $ · USDTRY 50,2282):**
- **1g** (1 bar, 2026-11-10 → 11-11): ons 4030,20→4007,00 (−%0,56) · kur 50,2157→50,2282 (+%0,02) · gram 6506,65→6470,80 (**−%0,54**)
- **1h** (5 bar, 2026-11-04 → 11-11): ons 4073,00→4007,00 (−%1,61) · kur 50,0102→50,2282 (+%0,43) · gram 6548,84→6470,80 (**−%1,18**)
- **1a** (21 bar, 2026-10-13 → 11-11): ons 4177,30→4007,00 (−%4,07) · kur 49,3385→50,2282 (**+%1,80**) · gram 6626,32→6470,80 (**−%2,27**)

1a penceresi 29 takvim günü · kur +%1,80 ↔ aylık varsayım %1,65 → tutarlı, uyarı yok.
Kontrol: gerçek gram −%2,338 vs yaklaşık −%2,264 → sapma %0,073 (tolerans %0,2) → **kabul**.
Önceki hatalı çıktı (kur +%18,62, gram +%14,61) tamamen gitti.

**Test:** 256/256 passed (211 önceki + 45 yeni/regresyon). Yeni testler: pencere sabitleri,
tarihe göre hizalama + boşluk/5 gün kuralı, bağımsız gram serisi kontrolü, kur tutarlılık uyarısı
(aylık varsayımın 3 katı), jeopolitik tek yön gösterimi, `seri_degisim` sıfır baz davranışı.
