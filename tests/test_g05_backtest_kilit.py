"""G05 — Backtest kilit kuralı (md.2 + md.6).

Kilitli (tavan/taban) günde giriş VE çıkış yapılamaz; ilk kilitsiz güne kayar.
Gerçek `test_senaryolari` üzerinden çalışır, ağ YOK (deterministik sentetik seri).
"""
import datetime as dt
import random
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import veri_cek as v  # noqa: E402


def _seri(seed=7, gun=200, kilit=()):
    """Deterministik rastgele yürüyüş; `kilit` indekslerinde TABAN kilidi (kapanış == gün düşüğü)."""
    random.seed(seed)
    rows, f, d, i = [], 100.0, dt.date(2025, 9, 1), 0
    while len(rows) < gun:
        if d.weekday() < 5:
            hacim = int(random.uniform(3e6, 2e7))
            if i in kilit:
                f = round(f * 0.90, 2)
                rows.append({"tarih": d.strftime("%Y-%m-%d"), "kapanis": f,
                             "acilis": round(f / 0.90, 2), "min": f, "max": round(f / 0.90, 2),
                             "hacim": hacim})
            else:
                f = round(max(5.0, f * (1 + random.gauss(0.0015, 0.012))), 2)
                rows.append({"tarih": d.strftime("%Y-%m-%d"), "kapanis": f,
                             "acilis": round(f * (1 + random.gauss(0, 0.004)), 2),
                             "min": round(f * 0.99, 2), "max": round(f * 1.01, 2),
                             "hacim": hacim})
            i += 1
        d += dt.timedelta(days=1)
    return rows


def _islemler(hv):
    return (v.test_senaryolari(hv).get("ertesi_gun_acilis") or {}).get("islemler") or []


def _idx(rows):
    return {r["tarih"]: i for i, r in enumerate(rows)}


# temel seri: sinyal/giriş günlerini öğren, sonra o giriş günlerine kilit koy
_TEMEL = {"TEST": _seri()}
_TEMEL_IDX = _idx(_TEMEL["TEST"])
_GIRISLER = [i for i in (_TEMEL_IDX.get(x["giris_tarih"]) for x in _islemler(_TEMEL)) if i]
KILIT_GUNLERI = tuple(sorted({g for g in _GIRISLER if g in (61, 62, 67, 68)}))


def test_senaryo_islem_uretiyor():
    """Test verisi geçerli mi — aksi halde aşağıdaki testler boş küme üzerinde geçer."""
    assert len(_islemler(_TEMEL)) >= 10


def test_backtest_kilitli_gunde_giris_yok():
    hv = {"TEST": _seri(kilit=KILIT_GUNLERI)}
    kilitli = set(v.kilitli_gunler(hv["TEST"]))
    assert kilitli, "kilit üretilmedi — test verisi geçersiz"
    for isl in _islemler(hv):
        assert isl["giris_tarih"] not in kilitli, f"kilitli günde giriş: {isl}"
        assert isl.get("kilit") is None, f"giriş günü kilitli: {isl}"


def test_backtest_kaydirma_ilk_kilitsiz_gune():
    hv = {"TEST": _seri(kilit=KILIT_GUNLERI)}
    idx = _idx(hv["TEST"])
    kilitli = set(v.kilitli_gunler(hv["TEST"]))
    kaydirilan = [x for x in _islemler(hv) if x.get("kaydirildi")]
    assert kaydirilan, "kaydırma hiç tetiklenmedi — senaryo kilit gününe denk gelmemiş"
    for isl in kaydirilan:
        gi = idx[isl["giris_tarih"]]
        si = idx[isl["sinyal_tarih"]]
        assert gi > si + 1, f"kaydırma yok ama işaretli: {isl}"
        # aradaki tüm günler kilitli olmalı
        for k in range(si + 1, gi):
            assert hv["TEST"][k]["tarih"] in kilitli, f"kilitsiz gün atlanmış: {isl}"


def test_backtest_stop_kilitli_gunde_calismaz():
    """Stop taban kilidinde tetiklenmez; çıkış ilk kilitsiz güne kayar (G08: ATR stop)."""
    hv = {"TEST": _seri(kilit=KILIT_GUNLERI)}
    kilitli = set(v.kilitli_gunler(hv["TEST"]))
    for isl in _islemler(hv):
        assert isl["giris_tarih"] not in kilitli
        # G08 — stop artık 2×ATR; getiri ATR'ye bağlı, sabit -%5 değil.
        # Değişmez kural: stop kilitli günde tetiklenemez → çıkış tarihi kilitli olamaz.
        assert isl["cikis_tarih"] not in kilitli, f"kilitli günde çıkış: {isl}"
        if isl["stop_calismis"]:
            assert isl["stop_getiri_yuzde"] <= 0, f"stop pozitif getiri üretti: {isl}"
