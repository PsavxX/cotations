#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backtest sur tout l'historique du depot.

A chaque seance passee, le moteur est execute avec la seule information disponible ce
jour-la (aucune donnee future), puis on releve ce que le cours a reellement fait ensuite.

Trois precautions pour ne pas se raconter d'histoires :
  1. Rendement RELATIF : on retire a chaque valeur le mouvement moyen de sa zone (US ou
     Europe) le meme jour. Dans un marche qui monte, tout pari a la hausse gagne : seul
     l'ecart au marche mesure un vrai talent de selection.
  2. Selection simulee sur des dates espacees de l'horizon, pour que les periodes
     mesurees ne se chevauchent pas.
  3. Decoupage par annee, pour voir si un resultat tient dans plusieurs regimes de marche.

    resultats/backtest.md  +  resultats/backtest.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import donnees
import moteur

HORIZONS = (1, 3, 5, 10)


def fr(x, nd=2, signe=True):
    if x is None or not np.isfinite(x):
        return "—"
    return (f"{x:+.{nd}f}" if signe else f"{x:.{nd}f}").replace(".", ",")


def construire():
    cours = donnees.charger_cours()
    univers = donnees.charger_univers()
    morceaux = []
    for ticker, g in cours.groupby("ticker", sort=False):
        if len(g) < moteur.MIN_SEANCES + max(HORIZONS):
            continue
        g = g.set_index("date")
        r = moteur.calculer(g["close"], g["volume"])[["score", "surete_brute", "rsi"]]
        if r.empty:
            continue
        for h in HORIZONS:
            r[f"r{h}"] = ((g["close"].shift(-h) / g["close"] - 1) * 100).reindex(r.index)
        r = r.rename_axis("date").reset_index()
        r.insert(1, "ticker", ticker)
        morceaux.append(r)
    if not morceaux:
        raise SystemExit("Historique insuffisant pour un backtest.")
    df = pd.concat(morceaux, ignore_index=True)
    df["surete"] = moteur.surete(df["surete_brute"].values)
    df["secteur"] = df["ticker"].map(univers["secteur"]).fillna("")
    place = df["ticker"].map(univers["place"]).fillna("")
    df["zone"] = np.where(place == "US", "US", "Europe")
    df["sens"] = np.where(df["score"] > 0, 1.0, -1.0)
    for h in HORIZONS:
        marche = df.groupby(["date", "zone"])[f"r{h}"].transform("mean")
        df[f"rel{h}"] = df[f"r{h}"] - marche                 # rendement relatif a la zone
        df[f"pari{h}"] = df["sens"] * df[f"r{h}"]
        df[f"parirel{h}"] = df["sens"] * df[f"rel{h}"]
    return df


def stats(d, h):
    d = d.dropna(subset=[f"r{h}"])
    if len(d) == 0:
        return None
    return {"n": int(len(d)),
            "sens_correct": round(100 * float((d[f"pari{h}"] > 0).mean()), 1),
            "pari": round(float(d[f"pari{h}"].mean()), 3),
            "pari_relatif": round(float(d[f"parirel{h}"].mean()), 3)}


def simuler_selection(df, h):
    """Rejoue la selection publiee (seuil, plafond sectoriel, 10 par cote) sur des dates
    espacees de h seances."""
    compte = df.groupby("date")["ticker"].size()
    dates = sorted(compte[compte >= 0.5 * compte.max()].index)[::h]
    cand = df[(df["surete"] >= moteur.SEUIL_PUBLICATION) & df["date"].isin(dates)] \
        .dropna(subset=[f"r{h}"]).assign(score_final=lambda x: x["score"])
    retenus = []
    for _, jour in cand.groupby("date"):
        for cote in (jour[jour["score"] > 0], jour[jour["score"] < 0]):
            if len(cote):
                tickers, _ = moteur.selectionner(cote)
                retenus.append(cote[cote["ticker"].isin(tickers)])
    return (pd.concat(retenus, ignore_index=True) if retenus else cand.iloc[0:0]), len(dates)


def nb(n):
    return f"{n:,}".replace(",", " ")


def ligne(nom, s):
    if not s:
        return f"| {nom} | 0 | — | — | — |"
    return (f"| {nom} | {nb(s['n'])} | {fr(s['sens_correct'], 1, False)} % | "
            f"{fr(s['pari'])} % | **{fr(s['pari_relatif'])} %** |")


ENTETE = ["| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |",
          "|---|---|---|---|---|"]


def main():
    df = construire()
    debut, fin = df["date"].min(), df["date"].max()
    sortie = {"periode": [debut, fin], "valeurs": int(df["ticker"].nunique()),
              "observations": int(len(df))}
    md = ["# Backtest de l'algorithme", "",
          f"Periode : **{debut} → {fin}** · {sortie['valeurs']} valeurs · "
          f"{nb(len(df))} couples valeur-seance", "",
          "A chaque seance, le moteur ne voit que le passe. « Rendement du pari » = ce que le "
          "cours a fait ensuite, dans le sens annonce. « Relatif au marche » = le meme, une fois "
          "retire le mouvement moyen de la zone (US ou Europe) : **c'est la colonne qui compte.** "
          "Positive, l'algorithme choisit mieux que le hasard ; nulle ou negative, non.", ""]

    # 1. Le score predit-il quelque chose, et a quel horizon ?
    md += ["## 1. Le score contient-il de l'information ?", "",
           "| Horizon | Observations | Correlation score / rendement | Correlation score / rendement relatif | Derive du marche |",
           "|---|---|---|---|---|"]
    sortie["par_horizon"] = {}
    for h in HORIZONS:
        d = df.dropna(subset=[f"r{h}"])
        c1 = float(d["score"].corr(d[f"r{h}"], method="spearman"))
        c2 = float(d["score"].corr(d[f"rel{h}"], method="spearman"))
        derive = float(d[f"r{h}"].mean())
        sortie["par_horizon"][h] = {"n": int(len(d)), "corr": round(c1, 4), "corr_relatif": round(c2, 4),
                                    "derive": round(derive, 3)}
        md.append(f"| {h} seance{'s' if h > 1 else ''} | {nb(len(d))} | {fr(c1, 3)} | "
                  f"**{fr(c2, 3)}** | {fr(derive)} % |")
    md += ["", "Correlation de rang (Spearman). Une valeur de +0,02 a +0,05 sur des centaines de "
           "milliers d'observations est faible mais reelle ; proche de zero ou negative, le score "
           "n'apporte rien a cet horizon.", ""]

    # 2. La note de surete tient-elle sa promesse ?
    sortie["par_surete"] = {}
    for h in (5, 10):
        md += [f"## 2. La note de surete, a {h} seances" if h == 5 else f"### A {h} seances", ""] + ENTETE
        bloc = {}
        for nom, lo, hi in (("Surete 8-10", 8, 10), ("Surete 6-7", 6, 7), ("Surete 4-5", 4, 5), ("Surete 1-3", 1, 3)):
            for cote, sg in (("hausse", 1.0), ("baisse", -1.0)):
                s = stats(df[df["surete"].between(lo, hi) & (df["sens"] == sg)], h)
                bloc[f"{nom} {cote}"] = s
                md.append(ligne(f"{nom} · {cote}", s))
        sortie["par_surete"][h] = bloc
        md.append("")
    md += ["Si la note vaut quelque chose, le rendement relatif doit **augmenter avec elle**. "
           "S'il est plat ou inverse, la note ne mesure pas ce qu'elle pretend.", ""]

    # 3. La selection reellement publiee
    md += ["## 3. La selection publiee, rejouee sur le passe", "",
           f"Regles du scan : note ≥ {moteur.SEUIL_PUBLICATION}, au plus {moteur.PLAFOND_SECTEUR} valeurs "
           f"par secteur, {moteur.NB_MAX} par cote. Dates espacees de l'horizon (pas de chevauchement).", ""]
    sortie["selection"] = {}
    for h in (5, 10):
        sel, nb_dates = simuler_selection(df, h)
        md += [f"### A {h} seances — {nb_dates} dates rejouees", ""] + ENTETE
        bloc = {"dates": nb_dates}
        for nom, d in (("Hausse", sel[sel["sens"] > 0]), ("Baisse", sel[sel["sens"] < 0])):
            bloc[nom] = stats(d, h)
            md.append(ligne(f"**{nom}** — toute la periode", bloc[nom]))
            for an in sorted(sel["date"].str.slice(0, 4).unique()):
                s = stats(d[d["date"].str.startswith(an)], h)
                bloc[f"{nom} {an}"] = s
                md.append(ligne(f"{nom} · {an}", s))
        sortie["selection"][h] = bloc
        md.append("")

    # 4. Hypothese H1 du journal : cote hausse, un RSI > 70 annonce-t-il un retournement ?
    publ = df[(df["surete"] >= moteur.SEUIL_PUBLICATION) & (df["sens"] > 0)]
    md += ["## 4. Hypothese H1 — cote hausse, RSI au-dessus de 70", ""] + ENTETE
    sortie["h1"] = {"rsi_sup_70": stats(publ[publ["rsi"] > 70], 5), "rsi_inf_70": stats(publ[publ["rsi"] <= 70], 5)}
    md += [ligne("Hausse, note ≥ 6, RSI > 70 (5 seances)", sortie["h1"]["rsi_sup_70"]),
           ligne("Hausse, note ≥ 6, RSI ≤ 70 (5 seances)", sortie["h1"]["rsi_inf_70"]), ""]

    md += ["## Limites de ce test", "",
           "- **Biais du survivant** : l'univers est celui des indices d'aujourd'hui. Les societes "
           "sorties des indices ou radiees depuis n'y figurent pas, ce qui embellit le passe.",
           "- **Aucun frais** : ni courtage, ni ecart achat-vente, ni cout d'emprunt pour les paris a la baisse.",
           "- **Observations liees** : les valeurs d'un meme secteur bougent ensemble, et les fenetres "
           "des sections 1 et 2 se chevauchent. Le nombre d'observations surestime la quantite "
           "d'information independante.",
           "- **Technique seul** : le contexte d'actualite (macro) n'est pas rejoue.",
           "- Un resultat passe ne garantit rien pour la suite.", ""]

    with open(os.path.join(donnees.RESULTATS, "backtest.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(donnees.RESULTATS, "backtest.json"), "w", encoding="utf-8") as fh:
        json.dump(sortie, fh, ensure_ascii=False, indent=1)
    print(f"Backtest : {sortie['valeurs']} valeurs, {len(df)} observations, {debut} -> {fin}.")


if __name__ == "__main__":
    main()
