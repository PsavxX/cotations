# -*- coding: utf-8 -*-
"""Moteur d'analyse technique court terme (horizon vise : 5 a 10 seances).

Pour chaque valeur et chaque seance, a partir des seules clotures et volumes passes :
  - un score directionnel dans [-1, 1]  (signe = sens attendu, amplitude = force)
  - un indice de surete de 1 a 10       (confiance dans le signal, PAS le gain espere)

Le meme code sert au scan du jour (derniere ligne) et au backtest (toutes les lignes) :
ce qui est publie est exactement ce qui est teste.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

POIDS = {
    "tendance_mm":   1.30,   # position du cours vs moyennes mobiles 10 / 20 / 40
    "croisement_mm": 1.00,   # ecart MM10 / MM20 et sa dynamique
    "momentum":      1.40,   # variations a 5 / 10 / 20 seances
    "rsi":           0.90,   # niveau et pente du RSI(14)
    "macd":          1.20,   # histogramme MACD(12,26,9) + croisement
    "volume":        0.70,   # volume 5 j / 40 j, signe par le sens du mouvement
    "position_40s":  0.60,   # position dans le range des 40 dernieres seances
    "pente":         1.10,   # pente de la regression sur les log-prix (20 seances)
}
SIGNAUX = list(POIDS)
MIN_SEANCES = 40             # historique minimal pour produire un score

# --- Regles de selection, issues du journal d'apprentissage --------------------------
SEUIL_PUBLICATION = 6        # rien sous 6/10 n'est publie
PLAFOND_SECTEUR = 3          # au plus 3 valeurs d'un meme secteur par cote
NB_MAX = 10                  # au plus 10 valeurs par cote
POIDS_MACRO = 0.11           # influence maximale du biais sectoriel sur le score
SECTEUR_INCONNU = ("", "Inconnu")


def _rsi(c, n=14):
    d = c.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    p = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + g / p.replace(0, np.nan))).fillna(50)


def _pente_r2(y, n=20):
    """Regression lineaire glissante sur n points : pente annualisee et R2."""
    pente = np.full(len(y), np.nan)
    r2 = np.full(len(y), np.nan)
    if len(y) < n:
        return pente, r2
    w = sliding_window_view(y, n)
    x = np.arange(n, dtype=float) - (n - 1) / 2
    sxx = float((x ** 2).sum())
    yc = w - w.mean(axis=1, keepdims=True)
    a = (yc @ x) / sxx
    tot = (yc ** 2).sum(axis=1)
    res = tot - a * a * sxx
    ok = tot > 1e-12
    pente[n - 1:] = a * 252
    r2[n - 1:] = np.where(ok, np.clip(1 - res / np.where(ok, tot, 1.0), 0.0, 1.0), 0.0)
    return pente, r2


def calculer(close, volume):
    """close, volume : Series indexees par date croissante, sans trou.
    Renvoie un DataFrame (une ligne par seance exploitable)."""
    c = close.astype(float)
    v = volume.astype(float)
    clip = lambda s: s.clip(-1.0, 1.0)                                   # noqa: E731

    mm10, mm20, mm40 = c.rolling(10).mean(), c.rolling(20).mean(), c.rolling(40).mean()
    rsi = _rsi(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    msig = macd.ewm(span=9, adjust=False).mean()
    mhist = macd - msig
    pente_a, r2_a = _pente_r2(np.log(c.values))
    pente = pd.Series(pente_a, index=c.index)
    r2 = pd.Series(r2_a, index=c.index)
    vol_j = c.pct_change().rolling(20).std() * 100                       # volatilite quotidienne %

    s = pd.DataFrame(index=c.index)
    s["tendance_mm"] = clip(0.45 * np.tanh((c / mm10 - 1) * 30) +
                            0.35 * np.tanh((c / mm20 - 1) * 20) +
                            0.20 * np.tanh((c / mm40 - 1) * 11))

    ec = mm10 / mm20 - 1
    s["croisement_mm"] = clip(0.65 * np.tanh(ec * 45) + 0.35 * np.tanh((ec - ec.shift(5)) * 200))

    roc5, roc10, roc20 = c / c.shift(5) - 1, c / c.shift(10) - 1, c / c.shift(20) - 1
    s["momentum"] = clip(0.45 * np.tanh(roc5 * 22) + 0.35 * np.tanh(roc10 * 15) +
                         0.20 * np.tanh(roc20 * 9))

    niv = (rsi - 50) / 25.0
    niv = niv.where(~((rsi > 78) | (rsi < 22)), niv * 0.45)              # extremes = signal ambigu
    s["rsi"] = clip(0.70 * niv + 0.30 * np.tanh((rsi - rsi.shift(4)) / 9))

    croise = pd.Series(np.where(macd > msig, 1.0, -1.0), index=c.index)
    s["macd"] = clip(0.55 * np.tanh(mhist / c * 260) +
                     0.25 * np.tanh((mhist - mhist.shift(4)) / c * 520) + 0.20 * croise)

    v5, v40 = v.rolling(5).mean(), v.rolling(40).mean()
    rv = (v5 / v40).where(v40 > 0, 1.0)
    s["volume"] = clip(np.sign(roc5) * np.tanh((rv - 1) * 1.6) * 0.85)

    hi, lo = c.rolling(40).max(), c.rolling(40).min()
    pos = ((c - lo) / (hi - lo)).where(hi > lo, 0.5)
    s["position_40s"] = clip((pos - 0.5) * 1.7)

    s["pente"] = clip(np.tanh(pente * 1.1))

    tw = sum(POIDS.values())
    score = sum(s[k] * p for k, p in POIDS.items()) / tw
    sgn = np.sign(score).where(score != 0, 1.0)
    confl = sum(((np.sign(s[k]) == sgn) & (s[k].abs() > 0.08)) * p for k, p in POIDS.items()) / tw

    force = (score.abs() / 0.72).clip(upper=1.0)
    pen_vol = (1.0 - (vol_j - 2.2) * 0.15).clip(lower=0.35).where(vol_j > 2.2, 1.0)
    pen_ext = pd.Series(np.where(((rsi > 80) & (score > 0)) | ((rsi < 20) & (score < 0)), 0.78, 1.0),
                        index=c.index)
    capitaux = v40 * c
    pen_liq = (capitaux / 5e6).clip(lower=0.45).where(capitaux < 5e6, 1.0)

    brut = ((0.33 * force + 0.29 * confl + 0.38 * r2) * pen_vol * pen_ext * pen_liq) ** 1.25

    out = pd.DataFrame({
        "prix": c, "score": score, "surete_brute": brut, "confluence": confl, "r2": r2,
        "rsi": rsi, "vol_j": vol_j, "var5": roc5 * 100, "var10": roc10 * 100,
        "var20": roc20 * 100, "vol_ratio": rv, "pos40": pos, "capitaux": capitaux,
    })
    for k in SIGNAUX:
        out["s_" + k] = s[k]
    out = out.iloc[MIN_SEANCES - 1:]
    return out.dropna(subset=["score", "surete_brute"])


def surete(brut):
    """Passe de la confiance brute [0, 1] a la note entiere 1-10."""
    return np.rint(1 + 9 * np.clip(brut, 0.0, 1.0)).astype(int)


def selectionner(candidats):
    """Applique les regles de publication a un DataFrame de candidats d'un meme cote
    (colonnes requises : ticker, secteur, surete, score_final).
    Renvoie (retenus, ecartes) ; ecartes = [(ticker, motif), ...]."""
    retenus, ecartes, par_secteur = [], [], {}
    ordre = candidats.assign(_f=candidats["score_final"].abs()) \
                     .sort_values(["surete", "_f"], ascending=False)
    for r in ordre.itertuples(index=False):
        if r.surete < SEUIL_PUBLICATION:
            continue                                   # sous le seuil : jamais publie
        sec = r.secteur if isinstance(r.secteur, str) else ""
        if sec not in SECTEUR_INCONNU and par_secteur.get(sec, 0) >= PLAFOND_SECTEUR:
            ecartes.append((r.ticker, f"plafond de {PLAFOND_SECTEUR} valeurs « {sec} » atteint"))
            continue
        if len(retenus) >= NB_MAX:
            continue
        par_secteur[sec] = par_secteur.get(sec, 0) + 1
        retenus.append(r.ticker)
    return retenus, ecartes


def scorer(cours, toutes_les_dates=False):
    """Applique le moteur a chaque valeur d'un DataFrame long (date, ticker, close, volume).
    Par defaut ne garde que la derniere seance de chaque valeur (scan du jour)."""
    morceaux = []
    for ticker, g in cours.groupby("ticker", sort=False):
        if len(g) < MIN_SEANCES:
            continue
        g = g.set_index("date")
        r = calculer(g["close"], g["volume"])
        if r.empty:
            continue
        if not toutes_les_dates:
            r = r.iloc[[-1]]
        r = r.rename_axis("date").reset_index()
        r.insert(1, "ticker", ticker)
        morceaux.append(r)
    if not morceaux:
        return pd.DataFrame()
    out = pd.concat(morceaux, ignore_index=True)
    out["surete"] = surete(out["surete_brute"].values)
    return out
