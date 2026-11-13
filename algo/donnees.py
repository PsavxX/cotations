# -*- coding: utf-8 -*-
"""Lecture des fichiers mensuels du depot et de la liste des valeurs."""
import glob
import os

import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RACINE, "data")
RESULTATS = os.path.join(RACINE, "resultats")


def charger_cours(derniers_mois=None):
    """DataFrame long trie : date, ticker, open, high, low, close, volume."""
    fichiers = sorted(glob.glob(os.path.join(DATA, "ohlcv-*.csv.gz")))
    if derniers_mois:
        fichiers = fichiers[-derniers_mois:]
    if not fichiers:
        raise SystemExit("Aucun fichier de cotations dans data/ : lancer d'abord la collecte.")
    df = pd.concat((pd.read_csv(f) for f in fichiers), ignore_index=True)
    df = df.dropna(subset=["close"])
    df = df[df["close"] > 0]
    df["volume"] = df["volume"].fillna(0)
    return df.drop_duplicates(["date", "ticker"], keep="last") \
             .sort_values(["ticker", "date"]).reset_index(drop=True)


def charger_univers():
    """DataFrame indexe par ticker : nom, secteur, place.
    tickers/secteurs.csv (rempli automatiquement) complete les secteurs manquants."""
    uni = pd.read_csv(os.path.join(RACINE, "tickers", "univers.csv")).fillna("")
    uni = uni.drop_duplicates("ticker").set_index("ticker")
    extra = os.path.join(RACINE, "tickers", "secteurs.csv")
    if os.path.exists(extra):
        sec = pd.read_csv(extra).fillna("").drop_duplicates("ticker").set_index("ticker")
        for t, r in sec.iterrows():
            if t not in uni.index:
                continue
            if not uni.at[t, "secteur"] and r.get("secteur", ""):
                uni.at[t, "secteur"] = r["secteur"]
            if uni.at[t, "nom"] in ("", t) and r.get("nom", ""):
                uni.at[t, "nom"] = r["nom"]
    return uni[["nom", "secteur", "place"]]
