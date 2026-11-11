"""tetik_tanim.py — ag baglantisi gerektirmez."""
import importlib.util, json, time, hmac, hashlib
from pathlib import Path

YOL = Path(__file__).resolve().parent.parent / "scripts" / "tetik_tanim.py"
spec = importlib.util.spec_from_file_location("tetik_tanim", YOL)
tt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tt)


def test_dort_is_ve_tipler():
    t = tt.tanimlar("s3cret")
    assert set(t) == {"veri-cek", "altin-cek", "kripto-cek", "ek-veri-cek"}
    assert [x["tip"] for x in t.values()] == ["veri", "altin", "kripto", "ek"]
    assert all(x["url"].endswith("/repos/hechecik/bist-panel/dispatches") for x in t.values())


def test_govde_imzali_ve_token_yok():
    ts = 1700000000
    g = tt.govde("kripto", "s3cret", ts)
    assert g["event_type"] == "harici-kripto"  # tetik-giris.yml bu tipi dinler
    assert g["client_payload"]["ts"] == ts
    beklenen = hmac.new(b"s3cret", b"1700000000", hashlib.sha256).hexdigest()
    assert g["client_payload"]["sign"] == beklenen
    ham = json.dumps(g)
    assert "ghp_" not in ham and "github_pat_" not in ham


def test_farkli_secret_farkli_imza():
    assert tt.govde("veri", "a", 1)["client_payload"]["sign"] != tt.govde("veri", "b", 1)["client_payload"]["sign"]


def test_dakika_listesi():
    assert tt._dakika("*/10 * * * *") == [0, 10, 20, 30, 40, 50]
    assert tt._dakika("17,47 * * * *") == [17, 47]


def test_payload_json_icinde_tirnak_kacisi_yok():
    t = tt.tanimlar("s3cret")["veri-cek"]
    assert json.loads(t["body"])["event_type"] == "harici-veri"
