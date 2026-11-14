#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collecte les cotations quotidiennes de l'univers et les range par mois.

Un fichier par mois (data/ohlcv-AAAA-MM.csv.gz) : seul le mois courant est
reecrit a chaque execution, les mois passes ne bougent plus. L'historique
du depot reste donc leger meme apres des annees de collecte.

Usage :
    python scripts/collecte.py                 # met a jour les 10 derniers jours
    python scripts/collecte.py --depuis 2024-01-01   # rattrapage / amorcage
"""
import argparse, gzip, io, os, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

import ajustements

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERS = os.path.join(RACINE, "tickers", "univers.csv")
DOSSIER = os.path.join(RACINE, "data")
AJUSTEMENTS = os.path.join(DOSSIER, "ajustements.csv")
COLONNES = ["date", "ticker", "open", "high", "low", "close", "volume"]
LOT = 40                      # tickers par requete yfinance
PAUSE = 1.2                   # secondes entre deux lots, pour rester courtois


def tickers():
    df = pd.read_csv(UNIVERS)
    return df["ticker"].dropna().astype(str).tolist()


CHAMPS = [("Open", "open"), ("High", "high"), ("Low", "low"),
          ("Close", "close"), ("Volume", "volume")]


def _telecharger_lot(lot, debut, fin, essais=3):
    """Un lot yfinance, avec reprise progressive en cas d'erreur ou de reponse vide."""
    for k in range(essais):
        try:
            brut = yf.download(lot, start=debut, end=fin, interval="1d",
                               auto_adjust=True, progress=False, threads=True,
                               group_by="column")
            if brut is not None and not brut.empty:
                return brut
        except Exception as e:                                  # noqa: BLE001
            print(f"    essai {k + 1}/{essais} : {e}", file=sys.stderr)
        time.sleep(PAUSE * (4 ** k))                            # 1,2 s puis 4,8 s puis 19 s
    return None


def _mettre_en_lignes(brut, lot):
    """Colonnes (champ, ticker) -> lignes date, ticker, open, high, low, close, volume."""
    if not isinstance(brut.columns, pd.MultiIndex):             # un seul ticker, format plat
        brut = brut.copy()
        brut.columns = pd.MultiIndex.from_product([brut.columns, lot])
    niveaux = brut.columns.get_level_values(0)
    colonnes = {cible: brut[champ].stack(future_stack=True)
                for champ, cible in CHAMPS if champ in niveaux}
    if "close" not in colonnes:
        return pd.DataFrame(columns=COLONNES)
    bloc = pd.DataFrame(colonnes)
    bloc.index.names = ["date", "ticker"]
    return bloc.reset_index().dropna(subset=["close"])


def telecharger(liste, debut, fin):
    """Renvoie un DataFrame long : date, ticker, open, high, low, close, volume."""
    morceaux, echecs = [], []
    nb_lots = (len(liste) - 1) // LOT + 1
    for i in range(0, len(liste), LOT):
        lot = liste[i:i + LOT]
        brut = _telecharger_lot(lot, debut, fin)
        if brut is None:
            echecs.extend(lot)
            print(f"  lot {i // LOT + 1}/{nb_lots} : aucune donnee")
            continue
        bloc = _mettre_en_lignes(brut, lot)
        obtenus = set(bloc["ticker"].unique())
        echecs.extend(t for t in lot if t not in obtenus)
        morceaux.append(bloc)
        print(f"  lot {i // LOT + 1}/{nb_lots} : {len(obtenus)}/{len(lot)} valeurs")
        time.sleep(PAUSE)

    morceaux = [m for m in morceaux if not m.empty]
    if not morceaux:
        return pd.DataFrame(columns=COLONNES), sorted(set(echecs))

    df = pd.concat(morceaux, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for c in ("open", "high", "low", "close"):
        if c in df:
            df[c] = df[c].astype(float).round(4)
    if "volume" in df:
        df["volume"] = df["volume"].fillna(0).astype("int64")
    return df[[c for c in COLONNES if c in df.columns]], sorted(set(echecs))


def fichier_mois(mois):
    return os.path.join(DOSSIER, f"ohlcv-{mois}.csv.gz")


def lignes_stockees(debut):
    """Lignes deja stockees a partir de debut (brutes, sans ajustement)."""
    if not os.path.isdir(DOSSIER):
        return pd.DataFrame(columns=COLONNES)
    blocs = []
    for f in sorted(os.listdir(DOSSIER)):
        if f.startswith("ohlcv-") and f[6:13] >= debut[:7]:
            b = pd.read_csv(os.path.join(DOSSIER, f), dtype={"date": str, "ticker": str})
            blocs.append(b[b["date"] >= debut])
    return pd.concat(blocs, ignore_index=True) if blocs else pd.DataFrame(columns=COLONNES)


def mettre_a_jour_ajustements(df, debut):
    """Detecte les reajustements Yahoo (splits, dividendes) sur les jours deja stockes."""
    adj, detectes = ajustements.detecter(lignes_stockees(debut), df, debut,
                                         ajustements.lire(AJUSTEMENTS), date.today().isoformat())
    os.makedirs(DOSSIER, exist_ok=True)
    adj.to_csv(AJUSTEMENTS, index=False)
    if detectes:
        print(f"{len(detectes)} reajustement(s) enregistre(s) : " +
              ", ".join(f"{d['ticker']} x{d['ratio']:.4f}" for d in detectes[:12]) +
              (" ..." if len(detectes) > 12 else ""))


def fusionner(df):
    """Ecrit chaque mois concerne, en fusionnant avec l'existant (les nouvelles
    lignes remplacent les anciennes sur le couple date+ticker)."""
    os.makedirs(DOSSIER, exist_ok=True)
    ecrits = []
    df = df.copy()
    df["mois"] = df["date"].str.slice(0, 7)
    for mois, bloc in df.groupby("mois"):
        bloc = bloc.drop(columns="mois")
        chemin = fichier_mois(mois)
        if os.path.exists(chemin):
            ancien = pd.read_csv(chemin)
            bloc = pd.concat([ancien, bloc], ignore_index=True)
        bloc = (bloc.drop_duplicates(subset=["date", "ticker"], keep="last")
                    .sort_values(["date", "ticker"]))
        bloc.to_csv(chemin, index=False, compression={"method": "gzip", "mtime": 0})
        ecrits.append((mois, len(bloc)))
    return ecrits


def ecrire_index(echecs):
    """Petit fichier de metadonnees, pratique a lire sans decompresser quoi que ce soit."""
    fichiers = sorted(f for f in os.listdir(DOSSIER) if f.startswith("ohlcv-"))
    lignes = ["# Index des donnees collectees", "",
              f"Derniere mise a jour : {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
              "| Fichier | Lignes |", "|---|---|"]
    for f in fichiers:
        n = sum(1 for _ in gzip.open(os.path.join(DOSSIER, f), "rt")) - 1
        lignes.append(f"| `{f}` | {n} |")
    if echecs:
        lignes += ["", f"Tickers sans donnee a la derniere execution ({len(echecs)}) :", "",
                   "```", ", ".join(echecs), "```"]
    with open(os.path.join(DOSSIER, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lignes) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depuis", help="date de debut AAAA-MM-JJ (amorcage)")
    ap.add_argument("--jours", type=int, default=10,
                    help="nombre de jours a rafraichir si --depuis est absent")
    a = ap.parse_args()

    debut = a.depuis or (date.today() - timedelta(days=a.jours)).isoformat()
    fin = (date.today() + timedelta(days=1)).isoformat()
    liste = tickers()
    print(f"{len(liste)} tickers, du {debut} au {fin}")

    df, echecs = telecharger(liste, debut, fin)
    if df.empty:
        print("Aucune donnee recuperee.", file=sys.stderr)
        sys.exit(1)

    mettre_a_jour_ajustements(df, debut)
    ecrits = fusionner(df)
    ecrire_index(echecs)
    print(f"\n{len(df)} lignes collectees, {df.ticker.nunique()} valeurs distinctes")
    for mois, n in ecrits:
        print(f"  {mois} : {n} lignes au total")
    if echecs:
        print(f"{len(echecs)} tickers sans donnee : {', '.join(echecs[:15])}"
              f"{' ...' if len(echecs) > 15 else ''}")


if __name__ == "__main__":
    main()
