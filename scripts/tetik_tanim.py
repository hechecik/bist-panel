#!/usr/bin/env python3
"""Yedek tetikleyici icin is (job) tanimlarini uretir — SIR ICERMEZ.

cron-job.org gibi harici zamanlayicilar GitHub Actions'i uyandirmak icin
repository_dispatch ya da workflow_dispatch cagirir. Bu betik API'ye GONDERILECEK
govdeyi (JSON) uretir; kimlik bilgisi dosyaya yazilmaz, sadece stdout'a "TOKEN"
yer tutucusu olarak basilir. Gercek token ortam degiskeninden okunur:

    CRONJOB_SECRET=... python3 scripts/tetik_tanim.py            # govdeleri bas
    CRONJOB_SECRET=... python3 scripts/tetik_tanim.py --kur      # API'ye gonder

Neden repository_dispatch: cron-job.org URL'i acik metin olarak saklar; URL'de
GitHub PAT tasimak sizinti riskidir. Bunun yerine cron-job.org'un "request body"
ozelligine KRIPTOGRAFLANMIS bir secret konur; secret yalnizca Actions secret
olarak durur. PAT hicbir yerde yazili olmaz.

Sirlar:
  CRONJOB_SECRET  — ortak anahtar (GitHub secret CRONJOB_SECRET ile ayni)
  CRONJOB_API_KEY — cron-job.org API anahtari (yalnizca --kur icin gerekir)
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = "hechecik/bist-panel"
URL = f"https://api.github.com/repos/{REPO}/dispatches"
# is akisi -> (baslik, cron ifadesi, event_type)
ISLER = {
    "veri-cek": ("iste-bist-panel-veri", "*/10 * * * *", "veri"),
    "altin-cek": ("iste-bist-panel-altin", "*/10 * * * *", "altin"),
    "kripto-cek": ("iste-bist-panel-kripto", "*/10 * * * *", "kripto"),
    "ek-veri-cek": ("iste-bist-panel-ekveri", "*/30 * * * *", "ek"),
}


def imza(secret, ts):
    """Zaman damgali HMAC — eski istek tekrar oynatilamaz (5 dk pencere)."""
    return hmac.new(secret.encode(), f"{ts}".encode(), hashlib.sha256).hexdigest()


def govde(tip, secret, ts=None):
    """client_payload'u (uyandirilacak akis tipini tasir) imzali gonderir."""
    ts = int(ts if ts is not None else time.time())
    return {"event_type": "harici-" + tip,
            "client_payload": {"ts": ts, "sign": imza(secret, ts)}}


def tanimlar(secret):
    return {ad: {"title": baslik, "url": URL, "schedule": cron, "tip": tip,
                 "body": json.dumps(govde(tip, secret))}
            for ad, (baslik, cron, tip) in ISLER.items()}


def kur(secret, api_key):
    out = []
    for ad, t in tanimlar(secret).items():
        d = {"job": {"title": t["title"], "url": t["url"], "enabled": True,
                     "saveResponses": True, "requestMethod": 1,  # 1 = POST
                     "requestBody": t["body"],
                     "schedule": {"timezone": "UTC", "expiresAt": 0,
                                  "hours": list(range(24)),
                                  "mdays": list(range(1, 32)),
                                  "months": list(range(1, 13)),
                                  "wdays": [-1], "minutes": _dakika(t["schedule"]),
                                  "interval": 0}}}
        req = urllib.request.Request("https://api.cron-job.org/jobs",
                                     data=json.dumps(d).encode(), method="PUT")
        req.add_header("Authorization", "Bearer " + api_key)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                jid = json.loads(r.read().decode() or "{}").get("jobId")
                out.append(f"{ad}: jobId={jid} HTTP {r.status}")
        except urllib.error.HTTPError as e:
            out.append(f"{ad}: HATA {e.code} {e.read().decode()[:200]}")
    return out


def _dakika(cron):
    """'*/10 * * * *' -> [0,10,...,50] (cron-job.org minutes listesi)."""
    alan = cron.split()[0]
    if alan.startswith("*/"):
        adim = int(alan[2:])
        return list(range(0, 60, adim))
    return [int(x) for x in alan.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kur", action="store_true", help="cron-job.org API'sine gonder")
    a = ap.parse_args()
    secret = os.environ.get("CRONJOB_SECRET")
    if not secret:
        print("CRONJOB_SECRET tanimli degil — tanimlar uretilemez", file=sys.stderr)
        return 2
    if a.kur:
        key = os.environ.get("CRONJOB_API_KEY")
        if not key:
            print("CRONJOB_API_KEY tanimli degil", file=sys.stderr)
            return 2
        for satir in kur(secret, key):
            print(satir)
        return 0
    print(json.dumps(tanimlar(secret), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
