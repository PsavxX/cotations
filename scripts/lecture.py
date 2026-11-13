#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lecture des donnees depuis le depot, cote analyse.

A utiliser depuis n'importe quel environnement qui joint raw.githubusercontent.com
(c'est le cas du conteneur Claude, qui ne joint en revanche aucune API de cotation).

    from lecture import charger
    df = charger("pierre3710", "cotations", mois=6)     # 6 derniers mois
    serie = df[df.ticker == "MC.PA"]
"""
import gzip, io, urllib.request
from datetime import date

import pandas as pd

GABARIT = "https://raw.githubusercontent.com/{u}/{d}/main/data/ohlcv-{m}.csv.gz"


def _mois_recents(n):
    y, m = date.today().year, date.today().month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return out[::-1]


def charger(utilisateur, depot, mois=3, branche="main"):
    """Renvoie un DataFrame long : date, ticker, open, high, low, close, volume."""
    blocs = []
    for m in _mois_recents(mois):
        url = GABARIT.format(u=utilisateur, d=depot, m=m).replace("/main/", f"/{branche}/")
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                brut = gzip.decompress(r.read())
        except Exception:                                       # noqa: BLE001
            continue                                            # mois absent : on passe
        blocs.append(pd.read_csv(io.BytesIO(brut)))
    if not blocs:
        raise RuntimeError("Aucun fichier mensuel accessible - depot public ? branche correcte ?")
    df = pd.concat(blocs, ignore_index=True)
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def series_par_ticker(df):
    """{ticker: [(date, close, volume), ...]} du plus recent au plus ancien,
    format attendu par le moteur de scoring."""
    out = {}
    for t, bloc in df.groupby("ticker"):
        bloc = bloc.sort_values("date", ascending=False)
        out[t] = list(zip(bloc["date"], bloc["close"], bloc["volume"]))
    return out


def dernier_scan(utilisateur, depot, branche="main"):
    """Le dernier classement publie par l'automatisation (dict) :
    date, hausse, baisse, avertissements, valeurs ecartees..."""
    import json
    url = f"https://raw.githubusercontent.com/{utilisateur}/{depot}/{branche}/resultats/dernier.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)
