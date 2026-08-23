#!/usr/bin/env python3
"""BIST 100 sektör haritası — yfinance (Yahoo resmi sınıflandırma) ile üretilir.

Çıktı: scripts/sektorler.json — {'THYAO': 'Industrials', ...}
Kaynak: yfinance Ticker.info['sector'] (Yahoo resmi sektör sınıflandırması).
Başarısız olan hisseler girilmez — sonraki çalıştırmada tekrar denenir.
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIST100 = ROOT / "bist100.txt"
OUT = Path(__file__).resolve().parent / "sektorler.json"

liste = [l.strip().upper() for l in BIST100.read_text().splitlines() if l.strip()]
try:
    mevcut = json.loads(OUT.read_text()) if OUT.exists() else {}
except Exception:
    mevcut = {}

import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

eksik = [s for s in liste if s not in mevcut]
print(f"Toplam {len(liste)} hisse | cache'de {len(mevcut)} | çekilecek {len(eksik)}", flush=True)

for i, sym in enumerate(eksik):
    try:
        t = yf.Ticker(f"{sym}.IS")
        info = t.info or {}
        sektor = info.get('sector')
        if sektor:
            mevcut[sym] = sektor
            print(f"[{i+1}/{len(eksik)}] {sym} → {sektor}", flush=True)
        else:
            print(f"[{i+1}/{len(eksik)}] {sym} → sektör yok", flush=True)
    except Exception as e:
        print(f"[{i+1}/{len(eksik)}] {sym} → HATA {str(e)[:50]}", flush=True)
    time.sleep(0.3)  # rate limit koruması

OUT.write_text(json.dumps(mevcut, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"KAYDEDİLDİ: {len(mevcut)} hisse → {OUT}", flush=True)
