#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilan des scans publies : chaque valeur publiee est confrontee au cours observe
5 et 10 seances plus tard. C'est la mesure la plus honnete de ce que vaut l'algorithme,
parce qu'elle porte sur des classements reellement emis, jamais recalcules apres coup.

    resultats/bilan.md  +  resultats/bilan.json
"""
import glob
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import donnees

HORIZONS = (5, 10)


def fr(x, nd=2):
    return f"{x:+.{nd}f}".replace(".", ",")


def evaluer():
    fichiers = sorted(glob.glob(os.path.join(donnees.RESULTATS, "historique", "*.json")))
    if not fichiers:
        return pd.DataFrame()
    cours = donnees.charger_cours()
    series = {t: g.set_index("date")["close"] for t, g in cours.groupby("ticker", sort=False)}
    lignes = []
    for f in fichiers:
        with open(f, encoding="utf-8") as fh:
            scan = json.load(fh)
        for p in scan.get("hausse", []) + scan.get("baisse", []):
            s = series.get(p["ticker"])
            if s is None or scan["date"] not in s.index:
                continue
            i = s.index.get_loc(scan["date"])
            ligne = {"scan": scan["date"], "ticker": p["ticker"], "sens": p["sens"],
                     "surete": p["surete"], "secteur": p.get("secteur", "")}
            for h in HORIZONS:
                if i + h < len(s):
                    r = (s.iloc[i + h] / s.iloc[i] - 1) * 100
                    ligne[f"pari{h}"] = r if p["sens"] == "HAUSSE" else -r
            lignes.append(ligne)
    return pd.DataFrame(lignes)


def resume(df, h):
    col = f"pari{h}"
    if col not in df:
        return None
    d = df.dropna(subset=[col])
    if d.empty:
        return None
    return {"n": int(len(d)), "sens_correct": round(100 * float((d[col] > 0).mean()), 1),
            "pari_moyen": round(float(d[col].mean()), 2)}


def main():
    df = evaluer()
    sortie = {"scans": 0, "tableaux": {}}
    md = ["# Bilan des scans publies", "",
          "Chaque valeur publiee est comparee au cours observe 5 et 10 seances plus tard. "
          "« Pari » = rendement dans le sens annonce (inverse pour un pari a la baisse).", ""]
    if df.empty or not any(f"pari{h}" in df for h in HORIZONS):
        md += ["_Aucun scan n'est encore assez ancien pour etre evalue (il faut 5 seances)._", ""]
    else:
        sortie["scans"] = int(df.dropna(subset=["pari5"])["scan"].nunique()) if "pari5" in df else 0
        coupes = [("Tous", df), ("Paris a la hausse", df[df.sens == "HAUSSE"]),
                  ("Paris a la baisse", df[df.sens == "BAISSE"]),
                  ("Surete 8-10", df[df.surete >= 8]), ("Surete 6-7", df[df.surete.between(6, 7)])]
        for h in HORIZONS:
            lignes = [(nom, resume(d, h)) for nom, d in coupes]
            lignes = [(n, r) for n, r in lignes if r]
            if not lignes:
                continue
            sortie["tableaux"][f"{h}_seances"] = {n: r for n, r in lignes}
            md += [f"## A {h} seances", "",
                   "| Perimetre | Paris evalues | Sens correct | Rendement moyen du pari |",
                   "|---|---|---|---|"]
            md += [f"| {n} | {r['n']} | {fr(r['sens_correct'], 1).lstrip('+')} % | {fr(r['pari_moyen'])} % |"
                   for n, r in lignes]
            md += [""]
        md += [f"{sortie['scans']} scans evalues. Tant que ce nombre est faible, ces chiffres "
               "indiquent une direction, ils ne prouvent rien : voir `backtest.md` pour le test "
               "sur tout l'historique.", ""]
    with open(os.path.join(donnees.RESULTATS, "bilan.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(donnees.RESULTATS, "bilan.json"), "w", encoding="utf-8") as fh:
        json.dump(sortie, fh, ensure_ascii=False, indent=1)
    print(f"Bilan : {sortie['scans']} scans evalues.")


if __name__ == "__main__":
    main()
