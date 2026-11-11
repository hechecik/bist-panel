#!/usr/bin/env python3
"""Tetikleyici teshisi — GitHub Actions schedule'in fiilen calisip calismadigini olcer.

GitHub Actions'ta planlanmis (schedule) calismalar sessizce durabilir: is akisi
dosyasi bozulmaz, API "active" der, ama calisma hic olusmaz. Bu betik son N gunun
API kayitlarindan olay tipi dagilimini cikarir; schedule payi sifirsa zamanlayici
olu oldugu kesinlesir.

Kullanim (AGENTS.md kurali: data/*_kontrol.json commit edilmez):
    GITHUB_TOKEN=$(cat ~/.git-credentials | ...) python3 scripts/tetik_kontrol.py
veya token'i argüman olarak:  python3 scripts/tetik_kontrol.py --token ghp_xxx
Cikti: data/tetik_kontrol.json (etiket: "kontrol" — veri commit'lerine girmez)

Aglar yoksa "durum": "veri yok" yazilir; uydurma deger uretilmez.
"""
import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

REPO = "hechecik/bist-panel"
API = "https://api.github.com"
DATA = Path(__file__).resolve().parent.parent / "data"
CIKTI = DATA / "tetik_kontrol.json"
IS_AKISLARI = ["veri-cek", "altin-cek", "kripto-cek", "ek-veri-cek"]


def _token(arg):
    if arg:
        return arg.strip()
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    p = Path.home() / ".git-credentials"
    if p.exists():
        for satir in p.read_text().splitlines():
            m = re.match(r"https://([^:]+):([^@]+)@", satir.strip())
            if m:
                return m.group(2)
    return None


def _get(yol, token):
    req = urllib.request.Request(API + yol)
    req.add_header("Authorization", "token " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "bist-panel-tetik-kontrol")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def teshis(token, gun=14):
    simdi = dt.datetime.now(dt.timezone.utc)
    bas = simdi - dt.timedelta(days=gun)
    _, d = _get(f"/repos/{REPO}/actions/workflows", token)
    sonuc = {"uretildi": simdi.isoformat(timespec="seconds"), "pencere_gun": gun,
             "sunucu_utc": simdi.strftime("%Y-%m-%d %H:%M"), "akislar": {}}

    for wf in d.get("workflows", []):
        ad = wf["name"]
        if ad not in IS_AKISLARI:
            continue
        _, rd = _get(f"/repos/{REPO}/actions/workflows/{wf['id']}/runs?per_page=100", token)
        runs = [r for r in rd.get("workflow_runs", [])
                if dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= bas]
        olay = {}
        for r in runs:
            olay[r["event"]] = olay.get(r["event"], 0) + 1
        sonlar = {}
        for r in rd.get("workflow_runs", []):
            sonlar.setdefault(r["event"], r["created_at"])
        son = rd["workflow_runs"][0]["created_at"] if rd.get("workflow_runs") else None
        gecen_dk = None
        if son:
            t = dt.datetime.fromisoformat(son.replace("Z", "+00:00"))
            gecen_dk = round((simdi - t).total_seconds() / 60)
        sonuc["akislar"][ad] = {
            "id": wf["id"], "durum": wf["state"],
            "son_calisma_utc": son, "gecen_dk": gecen_dk,
            "pencere_calisma": len(runs), "olay_dagilimi": olay,
            "son_calisma_olay_bazli": sonlar,
            "schedule_calisiyor": any(e == "schedule" for e in olay),
        }
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token")
    ap.add_argument("--gun", type=int, default=14)
    a = ap.parse_args()
    token = _token(a.token)
    try:
        if not token:
            raise RuntimeError("token yok")
        s = teshis(token, a.gun)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
        s = {"uretildi": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "durum": "veri yok", "hata": str(e)}
    DATA.mkdir(exist_ok=True)
    CIKTI.write_text(json.dumps(s, ensure_ascii=False, indent=2))
    for ad, v in (s.get("akislar") or {}).items():
        print(f"{ad:14s} son={v['son_calisma_utc']} gecen={v['gecen_dk']}dk "
              f"olaylar={v['olay_dagilimi']} schedule_calisiyor={v['schedule_calisiyor']}")
    if s.get("durum") == "veri yok":
        print("veri yok:", s.get("hata"))


if __name__ == "__main__":
    main()
