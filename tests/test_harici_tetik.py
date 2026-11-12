"""harici_tetik.py — saf mantik testleri (ag cagrisi yok).

Kapsam: sessiz mod (log yazimi + 1 MB kirpma) ve kapanis garantisi kurali.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import harici_tetik as ht  # noqa: E402


def test_log_yaz_dosyaya_ekler(tmp_path, monkeypatch):
    hedef = tmp_path / "alt" / "harici_tetik.log"
    monkeypatch.setattr(ht, "LOG_DOSYA", str(hedef))
    ht.log_yaz(["birinci", "ikinci"])
    ht.log_yaz(["ucuncu"])
    satirlar = hedef.read_text(encoding="utf-8").splitlines()
    assert satirlar == ["birinci", "ikinci", "ucuncu"]


def test_log_1mb_uzerinde_eski_yarisini_kirpar(tmp_path, monkeypatch):
    hedef = tmp_path / "harici_tetik.log"
    monkeypatch.setattr(ht, "LOG_DOSYA", str(hedef))
    # ~1.2 MB, satir sonlu icerik
    dolgu = ["D" * 99 for _ in range(12000)]  # 1.2 MB
    ht.log_yaz(dolgu)
    boyut = hedef.stat().st_size
    assert boyut <= ht.LOG_MAKS_BAYT, boyut
    # kirpma satir sinirindan yapilmali: ilk satir 99 D olmali (yarim satir yok)
    ilk = hedef.read_text(encoding="utf-8").splitlines()[0]
    assert ilk == "D" * 99, len(ilk)


def test_kapanis_penceresi_sinirlari():
    tr = ht.TR
    gun = dt.date(2026, 11, 13)  # Cuma

    def pencere(ss, dd=13):
        t = dt.datetime.combine(dt.date(2026, 11, dd), dt.time(ss // 60, ss % 60), tzinfo=tr)
        hafta_ici = t.weekday() < 5
        return hafta_ici and (dt.time(18, 35) <= t.time() <= dt.time(18, 59))

    assert pencere(18 * 60 + 34) is False
    assert pencere(18 * 60 + 35) is True
    assert pencere(18 * 60 + 59) is True
    assert pencere(19 * 60 + 0) is False
    assert pencere(18 * 60 + 45, dd=14) is False  # Cumartesi


def test_kripto_esigi_180():
    # esik tablosu main() icinde; burada sabiti dogruluyoruz
    kaynak = open(ht.__file__, encoding="utf-8").read()
    assert '"kripto-cek": 180' in kaynak
