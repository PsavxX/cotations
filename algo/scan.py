#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan du jour : note toutes les valeurs du depot, applique les regles de publication
et ecrit les resultats dans resultats/.

    resultats/dernier.md            classement lisible directement sur GitHub
    resultats/dernier.json          le meme, pour une lecture par programme
    resultats/scores-dernier.csv    la note de TOUTES les valeurs analysees
    resultats/historique/<date>.json   archive, relue par bilan.py pour mesurer les resultats
"""
import json
import os
import sys
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import donnees
import moteur

FRAICHEUR_MAX = 4        # jours calendaires toleres entre la derniere cotation d'une valeur et le scan
VALIDITE_MACRO = 10      # jours pendant lesquels algo/macro.json reste applicable
MOIS_CHARGES = 8         # profondeur d'historique chargee pour le scan


def _jours(a, b):
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def charger_macro(date_scan):
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macro.json")
    vide = {"appliquee": False, "date": None, "resume": "", "biais_secteurs": {}}
    try:
        with open(chemin, encoding="utf-8") as fh:
            m = json.load(fh)
        age = _jours(date_scan, m["date"])
    except Exception:                                           # noqa: BLE001
        return vide
    if not m.get("biais_secteurs") or not (0 <= age <= VALIDITE_MACRO):
        return {**vide, "date": m.get("date")}
    return {"appliquee": True, "date": m["date"], "resume": m.get("resume", ""),
            "biais_secteurs": m["biais_secteurs"]}


def quatre_sorcieres(dates):
    """Vrai si une des seances est un 3e vendredi de mars, juin, septembre ou decembre."""
    for d in dates:
        j = date.fromisoformat(d)
        if j.month in (3, 6, 9, 12) and j.weekday() == 4 and 15 <= j.day <= 21:
            return d
    return None


def scanner():
    cours = donnees.charger_cours(MOIS_CHARGES)
    univers = donnees.charger_univers()
    sc = moteur.scorer(cours)
    if sc.empty:
        raise SystemExit("Pas assez d'historique pour noter une seule valeur.")

    date_scan = sc["date"].max()
    sc = sc.join(univers, on="ticker")
    for col in ("nom", "secteur", "place"):
        sc[col] = sc[col].fillna("")
    sc.loc[sc["nom"] == "", "nom"] = sc["ticker"]

    ecartes = []
    perime = sc["date"].map(lambda d: _jours(date_scan, d) > FRAICHEUR_MAX)
    ecartes += [(r.ticker, f"cotation perimee ({r.date})") for r in sc[perime].itertuples()]
    absents = sorted(set(univers.index) - set(sc["ticker"]))
    ecartes += [(t, "aucune donnee ou historique trop court") for t in absents]
    sc = sc[~perime].copy()

    macro = charger_macro(date_scan)
    biais = {k: float(v.get("biais", 0)) for k, v in macro["biais_secteurs"].items()}
    sc["biais_macro"] = sc["secteur"].map(biais).fillna(0.0)
    sc["score_tech"] = sc["score"]
    sc["score_final"] = (sc["score"] + moteur.POIDS_MACRO * sc["biais_macro"]).clip(-1, 1)
    # La macro module la confiance : +12 % si elle confirme le technique, -12 % si elle le contredit.
    b = sc["biais_macro"]
    meme_sens = (sc["score_final"] > 0) == (b > 0)
    sc["alignement"] = np.where(b.abs() <= 0.2, 0, np.where(meme_sens, 1, -1))
    sc["surete"] = moteur.surete(sc["surete_brute"].values * (1 + 0.12 * sc["alignement"].values))
    sc["sens"] = np.where(sc["score_final"] > 0, "HAUSSE", "BAISSE")

    h, ec_h = moteur.selectionner(sc[sc["score_final"] > 0])
    bz, ec_b = moteur.selectionner(sc[sc["score_final"] < 0])
    ecartes += ec_h + ec_b

    dates_us = sorted(cours.loc[cours["ticker"].isin(sc.loc[sc["place"] == "US", "ticker"]), "date"].unique())
    avert = []
    qs = quatre_sorcieres((dates_us or sorted(cours["date"].unique()))[-5:])
    if qs:
        avert.append(f"Seance des quatre sorcieres le {qs} dans la fenetre de 5 seances : "
                     "les volumes de ce jour sont gonfles, le signal « volume » est biaise.")
    if not macro["appliquee"]:
        avert.append("Aucun contexte d'actualite valide (algo/macro.json absent ou perime) : "
                     "classement purement technique.")
    sans_secteur = int((sc["secteur"] == "").sum())
    if sans_secteur:
        avert.append(f"{sans_secteur} valeurs sans secteur connu : le plafond sectoriel ne les couvre pas.")
    return date_scan, sc.set_index("ticker"), h, bz, ecartes, macro, avert


def fiche(r, ticker):
    return {
        "ticker": ticker, "nom": r["nom"], "secteur": r["secteur"], "place": r["place"],
        "prix": round(float(r["prix"]), 4), "sens": r["sens"], "surete": int(r["surete"]),
        "score_final": round(float(r["score_final"]), 4), "score_tech": round(float(r["score_tech"]), 4),
        "biais_macro": round(float(r["biais_macro"]), 2), "alignement": int(r["alignement"]),
        "var5": round(float(r["var5"]), 2), "var20": round(float(r["var20"]), 2),
        "rsi": round(float(r["rsi"]), 1), "r2": round(float(r["r2"]), 3),
        "vol_j": round(float(r["vol_j"]), 2),
        "signaux": {k: round(float(r["s_" + k]), 3) for k in moteur.SIGNAUX},
    }


def fr(x, nd=2, signe=True):
    return (f"{x:+.{nd}f}" if signe else f"{x:.{nd}f}").replace(".", ",")


def tableau(picks):
    if not picks:
        return "_Aucune valeur ne passe les regles de publication._\n"
    lignes = ["| # | Valeur | Nom | Secteur | Cours | Surete | Score | 5 s. | 20 s. | RSI | R² | Ampl./j |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, p in enumerate(picks, 1):
        macro = {1: " ✓", -1: " ⚠ macro contraire"}.get(p["alignement"], "")
        lignes.append(
            f"| {i} | **{p['ticker']}** | {p['nom'][:32]} | {p['secteur'] or '—'} | {fr(p['prix'], 2, False)} | "
            f"**{p['surete']}/10**{macro} | {fr(p['score_final'], 3)} | {fr(p['var5'])} % | {fr(p['var20'])} % | "
            f"{fr(p['rsi'], 0, False)} | {fr(p['r2'], 2, False)} | {fr(p['vol_j'], 2, False)} % |")
    return "\n".join(lignes) + "\n"


def main():
    date_scan, sc, h, bz, ecartes, macro, avert = scanner()
    hausse = [fiche(sc.loc[t], t) for t in h]
    baisse = [fiche(sc.loc[t], t) for t in bz]
    distribution = {int(k): int(v) for k, v in sc["surete"].value_counts().sort_index(ascending=False).items()}

    resultat = {
        "date": date_scan,
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "horizon": "5 a 10 seances",
        "valeurs_analysees": int(len(sc)),
        "regles": {"seuil_publication": moteur.SEUIL_PUBLICATION, "plafond_secteur": moteur.PLAFOND_SECTEUR,
                   "nb_max_par_cote": moteur.NB_MAX},
        "macro": {k: macro[k] for k in ("appliquee", "date", "resume")},
        "avertissements": avert,
        "distribution_surete": distribution,
        "hausse": hausse, "baisse": baisse,
        "ecartees": [{"ticker": t, "motif": m} for t, m in ecartes],
    }

    os.makedirs(os.path.join(donnees.RESULTATS, "historique"), exist_ok=True)
    with open(os.path.join(donnees.RESULTATS, "dernier.json"), "w", encoding="utf-8") as fh:
        json.dump(resultat, fh, ensure_ascii=False, indent=1)
    # Archive legere : juste ce qu'il faut a bilan.py pour mesurer le resultat plus tard.
    court = ("ticker", "nom", "secteur", "sens", "surete", "prix", "score_final")
    archive = {"date": date_scan, "valeurs_analysees": int(len(sc)), "macro_appliquee": macro["appliquee"],
               "hausse": [{k: p[k] for k in court} for p in hausse],
               "baisse": [{k: p[k] for k in court} for p in baisse]}
    with open(os.path.join(donnees.RESULTATS, "historique", f"{date_scan}.json"), "w", encoding="utf-8") as fh:
        json.dump(archive, fh, ensure_ascii=False, indent=1)

    cols = ["nom", "secteur", "place", "date", "prix", "sens", "surete", "score_final", "score_tech",
            "biais_macro", "rsi", "r2", "var5", "var10", "var20", "vol_j", "vol_ratio", "capitaux"]
    sc[cols].round(4).sort_values(["surete", "score_final"], ascending=False) \
        .to_csv(os.path.join(donnees.RESULTATS, "scores-dernier.csv"))

    plafonnes = [(t, m) for t, m in ecartes if m.startswith("plafond")]
    perimes = [(t, m) for t, m in ecartes if not m.startswith("plafond")]
    md = [f"# Scan du {date_scan}", "",
          f"**{len(sc)} valeurs analysees** · horizon 5 a 10 seances · "
          f"seuil de publication {moteur.SEUIL_PUBLICATION}/10 · au plus {moteur.PLAFOND_SECTEUR} valeurs par secteur et par cote", ""]
    if macro["appliquee"]:
        md += [f"**Contexte ({macro['date']}).** {macro['resume']}", ""]
    md += [f"> {a}" for a in avert] + ([""] if avert else [])
    md += [f"## Orientees a la hausse ({len(hausse)})", "", tableau(hausse),
           f"## Orientees a la baisse ({len(baisse)})", "", tableau(baisse),
           "## Repartition des notes", "",
           "| Surete | " + " | ".join(f"{k}/10" for k in distribution) + " |",
           "|---|" + "---|" * len(distribution),
           "| Valeurs | " + " | ".join(str(v) for v in distribution.values()) + " |", ""]
    if plafonnes:
        md += ["## Ecartees par le plafond sectoriel", "",
               ", ".join(f"{t} ({m})" for t, m in plafonnes), ""]
    if perimes:
        md += [f"## Non analysees ({len(perimes)})", "",
               ", ".join(f"{t}" for t, _ in perimes[:80]) + (" …" if len(perimes) > 80 else ""), ""]
    md += ["---", "",
           "L'indice de surete note la **confiance dans le signal**, pas l'ampleur du gain attendu. "
           "Ce qu'il vaut reellement se lit dans [`backtest.md`](backtest.md) (test sur tout l'historique) "
           "et [`bilan.md`](bilan.md) (resultat des scans publies). "
           "Analyse technique automatique : ni prediction, ni conseil en investissement.", ""]
    with open(os.path.join(donnees.RESULTATS, "dernier.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    print(f"Scan du {date_scan} : {len(sc)} valeurs analysees, "
          f"{len(hausse)} a la hausse, {len(baisse)} a la baisse, {len(ecartes)} ecartees.")


if __name__ == "__main__":
    main()
