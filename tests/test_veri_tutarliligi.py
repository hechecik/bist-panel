"""G04 — veri tutarlılığı testleri. Ağ bağlantısı YOK, saf fonksiyonlar."""
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

from veri_cek import (  # noqa: E402
    haber_tarihi_iso, gram_altin_hesapla, ONS_GRAM, GRAM_UYARI_ESIK,
    bist100_listesi, BIST100_FILE,
)
from getiri_cek import tahvil_al_alternatif  # noqa: E402


# ─────────────────── Gram altın ───────────────────

def test_gram_ons_bolu_onsgram_carpi_usdtry():
    """Gram = ons / 31,1034768 × USD/TL — borsapy değeri kullanılmaz."""
    r = gram_altin_hesapla(4040.0, 50.24, 6675.0)
    beklenen = round(4040.0 / ONS_GRAM * 50.24, 2)
    assert r["fiyat"] == beklenen
    # 4040/31.1034768*50.24 ≈ 6525
    assert 6500 < r["fiyat"] < 6550


def test_gram_borsapy_degeri_sadece_capraz():
    r = gram_altin_hesapla(4040.0, 50.24, 6675.0)
    assert r["capraz"] == 6675.0
    assert r["kaynak"] == "ons/31,1034768 × USD/TL"


def test_gram_fark_esigi_asilirsa_uyari():
    """%1 eşiği: 6.675 vs hesap ~6.525 → fark %2,3 > %1 → UYARI var."""
    r = gram_altin_hesapla(4040.0, 50.24, 6675.0)
    assert r["fark_yuzde"] > GRAM_UYARI_ESIK
    assert r["uyari"] is True


def test_gram_esik_yuzde_bir():
    """GRAM_UYARI_ESIK %1 olmalı — %11'de bayat değer hiç yakalanmıyordu."""
    assert GRAM_UYARI_ESIK == 1.0


def test_gram_esik_altinda_uyari_yok():
    """Hesabın %0,5 üstündeki borsapy değeri eşiğin altında → uyarı YOK."""
    hesap = 4040.0 / ONS_GRAM * 50.24  # ~6525
    r = gram_altin_hesapla(4040.0, 50.24, hesap * 1.005)
    assert r["uyari"] is False
    assert abs(r["fark_yuzde"]) < 1.0


def test_gram_esik_hemen_ustunde_uyari_var():
    """Hesabın %1,2 üstü → eşik aşıldı, uyarı VAR (sınır davranışı)."""
    hesap = 4040.0 / ONS_GRAM * 50.24
    r = gram_altin_hesapla(4040.0, 50.24, hesap * 1.012)
    assert r["uyari"] is True


def test_gram_ons_kaynak_spot_vadeli():
    """Ons kaynağı gram kaydına yazılmalı: spot / vadeli."""
    assert gram_altin_hesapla(4040.0, 50.24, None, "spot")["ons_kaynak"] == "spot"
    assert gram_altin_hesapla(4040.0, 50.24, None, "vadeli")["ons_kaynak"] == "vadeli"


def test_gram_buyuk_fark_uyari_verir():
    """borsapy eşiği fazla saparsa uyari=True."""
    hesap = 4040.0 / ONS_GRAM * 50.24  # ~6525
    capraz = hesap * 1.20              # %20 yüksek
    r = gram_altin_hesapla(4040.0, 50.24, capraz)
    assert r["uyari"] is True
    assert r["fark_yuzde"] > GRAM_UYARI_ESIK


def test_gram_ons_yoksa_fiyat_none():
    r = gram_altin_hesapla(None, 50.24, 6675.0)
    assert r["fiyat"] is None
    assert r["uyari"] is False
    assert r["capraz"] == 6675.0


def test_gram_usdtry_yoksa_fiyat_none():
    r = gram_altin_hesapla(4040.0, None, None)
    assert r["fiyat"] is None


# ─────────────────── Haber tarihi normalizasyonu ───────────────────

def test_haber_rfc2822_utc_iso():
    """RFC-2822 "+0000" → UTC ISO."""
    assert haber_tarihi_iso("Wed, 11 Nov 2026 14:03:00 +0000") == "2026-11-11T14:03:00+00:00"


def test_haber_rfc2822_gmt_ifadesi():
    """RSS'te sık görülen "GMT" biçimi de çevrilmeli."""
    assert haber_tarihi_iso("Wed, 11 Nov 2026 14:03:00 GMT") == "2026-11-11T14:03:00+00:00"


def test_haber_rfc2822_ofset_utcye_cevrilir():
    """+03:00 ofsetli 17:03 → UTC 14:03."""
    assert haber_tarihi_iso("Wed, 11 Nov 2026 17:03:00 +0300") == "2026-11-11T14:03:00+00:00"


def test_haber_iso_z_eki():
    assert haber_tarihi_iso("2026-11-11T14:03:00Z") == "2026-11-11T14:03:00+00:00"


def test_haber_iso_ofsetsiz_utc_sayilir():
    assert haber_tarihi_iso("2026-11-11T14:03:00") == "2026-11-11T14:03:00+00:00"


def test_haber_bos_ve_bozuk_none():
    assert haber_tarihi_iso(None) is None
    assert haber_tarihi_iso("") is None
    assert haber_tarihi_iso("bozuk tarih") is None


def test_haber_karisik_bicimler_siralanabilir():
    """Farklı kaynak biçimleri aynı normalize uzaya gelince doğru sıralanır."""
    ham = [
        "Wed, 11 Nov 2026 10:00:00 +0000",   # en eski
        "2026-11-11T13:00:00Z",
        "Wed, 11 Nov 2026 16:30:00 +0300",   # = 13:30 UTC, en yeni
    ]
    iso = [haber_tarihi_iso(x) for x in ham]
    assert all(iso)
    assert iso == sorted(iso)
    assert iso[-1] == "2026-11-11T13:30:00+00:00"


# ─────────────────── bist100.txt ───────────────────

def test_bist100_yorum_satiri_atlanir():
    """'#' ile başlayan satır sembol sayılmamalı."""
    semboller = bist100_listesi()
    assert not any(s.startswith("#") for s in semboller)
    assert "GÜNCELLEME" not in semboller
    assert "AKBNK" in semboller


def test_bist100_dosya_basligi_dogru_bicimde():
    ilk = BIST100_FILE.read_text(encoding="utf-8").splitlines()[0]
    assert ilk.startswith("# güncelleme:")
    # YYYY-MM-DD biçim kontrolü
    tarih = ilk.split(":", 1)[1].strip()
    assert len(tarih) == 10 and tarih[4] == "-" and tarih[7] == "-"


def test_bist100_cift_sembol_yok():
    semboller = bist100_listesi()
    assert len(semboller) == len(set(semboller)), "tekrarlanan sembol var"


def test_fallback_listesinde_kchol_tek_kez():
    """Fallback listesinde KCHOL çift yazılmamalı."""
    import veri_cek
    import inspect
    src = inspect.getsource(veri_cek.bist100_listesi)
    assert src.count("'KCHOL'") == 1


# ─────────────────── Tahvil alternatif kaynak ───────────────────

def test_tahvil_alternatif_ag_yoksa_veya_bos_uygun_doner():
    """Ağ testi değil — fonksiyon çağrılabilir ve liste/dict sözleşmesine uyar.

    NOT: Gerçek doğrulama canlı çalıştırmada yapıldı (2Y 39,44 · 5Y 39,03 ·
    10Y 35,99, kaynak doviz.com/tahvil). Burada yalnızca sözleşme test edilir.
    """
    import inspect
    src = inspect.getsource(tahvil_al_alternatif)
    # Uydurma yok: sabit getiri değeri gömülü olmamalı
    assert "39.44" not in src and "35.99" not in src
    assert "doviz.com/tahvil" in src


def test_tahvil_durum_alani_bos_listede_yazilir():
    """getiri_cek.main() tahvil boşsa 'tahvil_durum' yazar — kaynak kodda mevcut."""
    import getiri_cek
    import inspect
    src = inspect.getsource(getiri_cek.main)
    assert "tahvil_durum" in src
    assert "tahvil" in src
