# -*- coding: utf-8 -*-
"""Cohérence des cours ajustés dans le temps.

Yahoo publie des cours ajustés (splits et dividendes) : à chaque split ou détachement,
TOUT l'historique d'une valeur est recalculé. Or la collecte quotidienne ne réécrit que
les 10 derniers jours. Sans correction, un split 10 pour 1 apparaîtrait comme une chute
de 90 % à la jonction entre l'ancien et le nouveau.

Principe : chaque soir, sur les jours déjà stockés ET re-téléchargés, on compare l'ancien
et le nouveau cours. Un écart constant signale un réajustement : on l'enregistre dans
data/ajustements.csv (ticker, avant, ratio) sans réécrire les vieux fichiers mensuels.
Au chargement, les cours antérieurs à « avant » sont multipliés par « ratio ».
"""
import os

import numpy as np
import pandas as pd

COLONNES_ADJ = ["ticker", "avant", "ratio", "detecte"]
SEUIL = 2e-4            # écart relatif minimal pour enregistrer un réajustement
DISPERSION_MAX = 0.01   # au-delà, l'écart n'est pas constant : révision ponctuelle, ignorée


def lire(chemin):
    if chemin and os.path.exists(chemin):
        adj = pd.read_csv(chemin, dtype={"ticker": str, "avant": str})
        return adj[COLONNES_ADJ] if len(adj) else pd.DataFrame(columns=COLONNES_ADJ)
    return pd.DataFrame(columns=COLONNES_ADJ)


def facteurs(df, adj):
    """Facteur multiplicatif à appliquer à chaque ligne de df (colonnes date, ticker)."""
    f = np.ones(len(df))
    if adj is None or adj.empty or df.empty:
        return f
    adj = adj.groupby(["ticker", "avant"], as_index=False)["ratio"].prod()
    positions = df.groupby("ticker", sort=False).indices          # ticker -> positions
    toutes_dates = df["date"].to_numpy(dtype=str)
    for t, a in adj.groupby("ticker"):
        p = positions.get(t)
        if p is None:
            continue
        a = a.sort_values("avant")
        bornes = a["avant"].to_numpy(dtype=str)
        # produit des ratios dont la borne est postérieure à la date
        suffixe = np.append(np.cumprod(a["ratio"].to_numpy()[::-1])[::-1], 1.0)
        f[p] = suffixe[np.searchsorted(bornes, toutes_dates[p], side="right")]
    return f


def appliquer(df, adj):
    """Renvoie une copie de df avec les prix (et volumes) mis en cohérence."""
    if adj is None or adj.empty or df.empty:
        return df
    df = df.copy()
    f = facteurs(df, adj)
    for c in ("open", "high", "low", "close"):
        if c in df:
            df[c] = df[c] * f
    if "volume" in df:
        df["volume"] = (df["volume"] / f).round()
    return df


def detecter(ancien, nouveau, debut, adj, aujourdhui):
    """ancien : lignes déjà stockées (date >= debut), brutes ; nouveau : téléchargement du jour.
    Renvoie la table d'ajustements mise à jour et la liste des réajustements détectés."""
    adj_avant = adj
    adj = adj.copy()
    obtenus = set(nouveau["ticker"].unique())
    # Les lignes >= debut des valeurs re-téléchargées vont être réécrites : les ajustements
    # existants ne doivent plus s'appliquer à elles.
    m = adj["ticker"].isin(obtenus)
    av = adj["avant"].astype(str)
    adj["avant"] = av.where(~m | (av < debut), debut)

    detectes = []
    if not ancien.empty:
        # cours tels que l'algorithme les voyait jusqu'ici (ajustements anterieurs compris)
        anc = appliquer(ancien, adj_avant)[["date", "ticker", "close"]]
        cmp_ = anc.merge(nouveau[["date", "ticker", "close"]], on=["date", "ticker"],
                         suffixes=("_a", "_n"))
        cmp_ = cmp_[(cmp_["close_a"] > 0) & (cmp_["close_n"] > 0)]
        cmp_["r"] = cmp_["close_n"] / cmp_["close_a"]
        for t, g in cmp_.groupby("ticker"):
            r = float(g["r"].median())
            if abs(r - 1) < SEUIL:
                continue
            if len(g) >= 2 and float((g["r"] / r - 1).abs().max()) > DISPERSION_MAX:
                print(f"  {t} : écart non constant entre ancien et nouveau cours, ignoré")
                continue
            detectes.append({"ticker": t, "avant": debut, "ratio": r, "detecte": aujourdhui})

    if detectes:
        adj = pd.concat([adj, pd.DataFrame(detectes)], ignore_index=True)
    # Un ajustement dont la borne est antérieure à toutes les données ne sert plus à rien
    # mais reste inoffensif ; on regroupe seulement les doublons.
    adj = (adj.groupby(["ticker", "avant"], as_index=False)
              .agg(ratio=("ratio", "prod"), detecte=("detecte", "max")))
    adj["ratio"] = adj["ratio"].round(10)
    return adj[COLONNES_ADJ].sort_values(["ticker", "avant"]).reset_index(drop=True), detectes
