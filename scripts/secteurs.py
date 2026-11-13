#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete le nom et le secteur des valeurs qui n'en ont pas dans tickers/univers.csv
(les valeurs europeennes), a partir de Yahoo Finance. Resultat : tickers/secteurs.csv.

Une valeur deja presente dans secteurs.csv n'est jamais redemandee : apres le premier
passage, ce script ne fait plus rien. Il est facultatif : s'il echoue, le scan tourne
quand meme, simplement sans plafond sectoriel sur les valeurs concernees.
"""
import os
import sys
import time

import pandas as pd
import yfinance as yf

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERS = os.path.join(RACINE, "tickers", "univers.csv")
SORTIE = os.path.join(RACINE, "tickers", "secteurs.csv")
MAX_PAR_PASSAGE = 400
PAUSE = 0.6

# Yahoo Finance -> nomenclature GICS, celle des valeurs du S&P 500 dans univers.csv
VERS_GICS = {
    "Technology": "Information Technology", "Healthcare": "Health Care",
    "Financial Services": "Financials", "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples", "Basic Materials": "Materials",
    "Communication Services": "Communication Services", "Energy": "Energy",
    "Industrials": "Industrials", "Real Estate": "Real Estate", "Utilities": "Utilities",
}


def main():
    uni = pd.read_csv(UNIVERS).fillna("")
    connus = pd.read_csv(SORTIE).fillna("") if os.path.exists(SORTIE) else \
        pd.DataFrame(columns=["ticker", "nom", "secteur"])
    a_faire = [t for t in uni.loc[uni["secteur"] == "", "ticker"] if t not in set(connus["ticker"])]
    if not a_faire:
        print("Secteurs : rien a completer.")
        return
    nouveaux, erreurs = [], 0
    for t in a_faire[:MAX_PAR_PASSAGE]:
        try:
            info = yf.Ticker(t).info or {}
            secteur = VERS_GICS.get(info.get("sector", ""), "Inconnu")
            nom = info.get("longName") or info.get("shortName") or ""
            nouveaux.append({"ticker": t, "nom": nom, "secteur": secteur})
            erreurs = 0
        except Exception as e:                                  # noqa: BLE001
            erreurs += 1
            print(f"  {t} : {e}", file=sys.stderr)
            if erreurs >= 15:                                   # Yahoo refuse : on reessaiera demain
                print("Trop d'echecs consecutifs, arret.", file=sys.stderr)
                break
        time.sleep(PAUSE)
    if nouveaux:
        pd.concat([connus, pd.DataFrame(nouveaux)], ignore_index=True) \
            .drop_duplicates("ticker", keep="last").sort_values("ticker") \
            .to_csv(SORTIE, index=False)
    trouves = sum(1 for n in nouveaux if n["secteur"] != "Inconnu")
    print(f"Secteurs : {len(nouveaux)} valeurs traitees, {trouves} secteurs trouves.")


if __name__ == "__main__":
    main()
