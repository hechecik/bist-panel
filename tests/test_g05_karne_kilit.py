"""G05 — karne (sinyal_gecmisi) kesinlik kuralı + kilit kaydırma + RISKLI.

Ağ YOK. Dosya yazımı geçici dizine yönlendirilir.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import veri_cek as v  # noqa: E402


# ── 1) Karneye sadece KESİN sinyaller yazılır ──────────────────────────────
def _karne_dizini(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "DATA_DIR", tmp_path)
    return tmp_path / "sinyal_gecmisi.json"


def _ornek_sinyaller(durum):
    return {
        "durum": durum,
        "al": [{"sembol": "THYAO", "sinyal": "AL", "skor": 5, "fiyat": 300.0}],
        "tut": [{"sembol": "AKBNK", "sinyal": "TUT", "skor": 1, "fiyat": 70.0}],
        "sat": [],
    }


def test_karne_gecici_sinyalleri_yazmaz(tmp_path, monkeypatch):
    dosya = _karne_dizini(tmp_path, monkeypatch)
    v.sinyal_gecmisi_guncelle(_ornek_sinyaller("gecici"))
    assert not dosya.exists() or json.loads(dosya.read_text()) == {}


def test_karne_kesin_sinyalleri_yazar(tmp_path, monkeypatch):
    dosya = _karne_dizini(tmp_path, monkeypatch)
    v.sinyal_gecmisi_guncelle(_ornek_sinyaller("kesin"))
    gecmis = json.loads(dosya.read_text())
    bugun = dt.date.today().strftime("%Y-%m-%d")
    assert bugun in gecmis
    assert set(gecmis[bugun]) == {"THYAO", "AKBNK"}
    assert gecmis[bugun]["THYAO"]["sinyal"] == "AL"


def test_karne_gecici_mevcut_kaydi_bozmaz(tmp_path, monkeypatch):
    dosya = _karne_dizini(tmp_path, monkeypatch)
    v.sinyal_gecmisi_guncelle(_ornek_sinyaller("kesin"))
    once = dosya.read_text()
    v.sinyal_gecmisi_guncelle(_ornek_sinyaller("gecici"))
    assert dosya.read_text() == once   # geçici çağrı dosyaya dokunmadı


def test_sinyal_durumu_karne_kapisi_tutarli():
    """durum 'gecici' iken karne yazılmaz — entegre kontrol."""
    s = _ornek_sinyaller("gecici")
    assert s["durum"] != "kesin"


# ── 2) Kilitli günde giriş/çıkış kaydırma (saf yardımcılar) ────────────────
def _bar(tarih, kapanis, mn=None, mx=None, hacim=1_000_000):
    mn = kapanis if mn is None else mn
    mx = kapanis if mx is None else mx
    return {"tarih": tarih, "kapanis": kapanis, "min": mn, "max": mx, "hacim": hacim}


def test_ilk_kilitsiz_taban_serisini_atlar():
    kilitler = {3: "TABAN", 4: "TABAN", 5: "TABAN"}
    assert v.ilk_kilitsiz(range(3, 9), kilitler) == 6


def test_ilk_kilitsiz_tavan_kilidi_girise_engel_degil():
    """Tavan kilidi alışa engel değildir; sadece TABAN girişi engeller."""
    assert v.ilk_kilitsiz([0, 1], {}) == 0


def test_ilk_kilitsiz_hepsi_kilitliyse_none():
    assert v.ilk_kilitsiz([0, 1, 2], {0: "TABAN", 1: "TABAN", 2: "TABAN"}) is None


def test_gercek_taban_serisi_ralyh_deseninde_kilit_sayisi():
    """RALYH deseni: her gün -%10, kapanış == gün düşüğü → hepsi TABAN."""
    rows, fiyat = [], 19.61
    for i in range(14):
        fiyat = round(fiyat * 0.9, 2)
        rows.append(_bar(f"2026-10-{22+i:02d}", fiyat))
    assert v.taban_sayisi(rows, pencere=10) == 10


def test_kilitli_gunler_tarih_anahtarli_seri_uretiyor():
    rows = [_bar("2026-11-02", 10.0), _bar("2026-11-03", 9.0), _bar("2026-11-04", 10.0)]
    k = v.kilitli_gunler(rows)
    assert k.get("2026-11-03") == "TABAN"
    assert k.get("2026-11-04") == "TAVAN"     # +%11.1 ve kapanış == gün yükseği


# ── 3) RISKLI / sorunlu hisse ─────────────────────────────────────────────
def _taban_serisi(n=5, bas=100.0):
    """n ardışık -%10 bar; geçiş sayısı n-1 (ilk bar önceki kapanış olmadan geçiş saymaz)."""
    rows, f = [_bar("2026-10-01", bas)], bas
    for i in range(n - 1):
        f = round(f * 0.9, 2)
        rows.append(_bar(f"2026-10-{i+2:02d}", f))
    return rows


def test_riskli_tespit_uc_taban_esigi():
    assert v.riskli_tespit(_taban_serisi(4)) is not None   # 3 geçiş → RISKLI
    assert v.riskli_tespit(_taban_serisi(3)) is None       # 2 geçiş → eşik altı


def test_riskli_tespit_ruzgar_tersine_uymaz():
    rows = [_bar(f"2026-11-{i+1:02d}", 100.0 + i) for i in range(10)]
    assert v.riskli_tespit(rows) is None


def test_yip_konkordato_kaynagi_yoksa_none():
    """YİP/konkordato için güvenilir kaynak yok → uydurma liste yok, alan None."""
    rows = [_bar(f"2026-11-{i+1:02d}", 100.0 + i) for i in range(10)]
    assert v.riskli_tespit(rows) is None   # sadece ≥3 taban kuralı
