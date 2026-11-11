"""Tetikleyici teshisi testleri — ag baglantisi gerektirmez (sahte API)."""
import datetime as dt
import importlib.util
from pathlib import Path

YOL = Path(__file__).resolve().parent.parent / "scripts" / "tetik_kontrol.py"
spec = importlib.util.spec_from_file_location("tetik_kontrol", YOL)
tk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tk)


def _cevap(akislar, kosular):
    """(yol -> json) donen sahte _get."""
    def sahte_get(yol, token):
        if yol.endswith("/workflows"):
            return 200, {"workflows": akislar}
        for wid, runs in kosular.items():
            if f"/workflows/{wid}/runs" in yol:
                return 200, {"workflow_runs": runs}
        raise AssertionError(yol)
    return sahte_get


def _kosu(olay, ts, sha="abc1234"):
    return {"event": olay, "created_at": ts, "head_sha": sha, "conclusion": "success"}


def test_schedule_yoksa_uyari(monkeypatch):
    simdi = dt.datetime.now(dt.timezone.utc)
    dun = (simdi - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    eski = (simdi - dt.timedelta(days=593)).strftime("%Y-%m-%dT%H:%M:%SZ")
    akislar = [{"id": 1, "name": "kripto-cek", "state": "active"},
               {"id": 9, "name": "pages", "state": "active"}]
    monkeypatch.setattr(tk, "_get", _cevap(akislar, {1: [_kosu("workflow_dispatch", dun),
                                                      _kosu("schedule", eski)]}))
    s = tk.teshis("tok", gun=14)
    k = s["akislar"]["kripto-cek"]
    assert k["schedule_calisiyor"] is False          # pencerede schedule yok
    assert k["olay_dagilimi"] == {"workflow_dispatch": 1}
    assert k["pencere_calisma"] == 1
    assert k["gecen_dk"] <= 1500
    assert "pages" not in s["akislar"]               # ilgisiz akislar disarida


def test_schedule_varsa_temiz(monkeypatch):
    simdi = dt.datetime.now(dt.timezone.utc)
    t1 = (simdi - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    akislar = [{"id": 2, "name": "altin-cek", "state": "active"}]
    monkeypatch.setattr(tk, "_get", _cevap(akislar, {2: [_kosu("schedule", t1)]}))
    s = tk.teshis("tok", gun=14)
    a = s["akislar"]["altin-cek"]
    assert a["schedule_calisiyor"] is True
    assert 19 <= a["gecen_dk"] <= 21
    assert a["son_calisma_olay_bazli"]["schedule"] == t1


def test_token_yoksa_veri_yok(monkeypatch, tmp_path):
    monkeypatch.setattr(tk, "CIKTI", tmp_path / "tetik_kontrol.json")
    monkeypatch.setattr(tk, "DATA", tmp_path)
    monkeypatch.setattr(tk, "_token", lambda arg: None)
    monkeypatch.setattr("sys.argv", ["tetik_kontrol.py"])
    tk.main()
    import json
    d = json.loads((tmp_path / "tetik_kontrol.json").read_text())
    assert d["durum"] == "veri yok"


def test_token_dosyadan(monkeypatch, tmp_path):
    p = tmp_path / ".git-credentials"
    p.write_text("https://hechecik:ghp_gizli123@github.com\n")
    monkeypatch.setattr(tk.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert tk._token(None) == "ghp_gizli123"
    assert tk._token(" elle ") == "elle"
