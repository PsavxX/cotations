#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portefeuille fictif : investit chaque soir, sans argent réel, selon des règles figées.

Trois stratégies tournent en parallèle, comparées à la même référence :
  - « Moteur actuel »         : les 10 valeurs publiées à la hausse par le scan, tous les 10 jours
  - « Momentum »              : les 20 valeurs les plus fortes sur 6 et 12 mois, une fois par mois
  - « Momentum + filtre »     : idem, mais tout en liquidités quand le marché est sous sa
                                moyenne de 200 séances
  - Référence « Marché »      : toutes les valeurs de l'univers à poids égaux, sans frais

Deux lectures du même code :
  1. Simulation sur le passé : toutes les données disponibles avant DEBUT_TEST.
  2. Suivi en direct : départ le DEBUT_TEST avec 10 000, sur des cours inconnus au moment
     où les règles ont été écrites. C'est le vrai test.

RÈGLE D'OR : ne jamais modifier REGLES ni le code de sélection en cours de test.
Toute modification = nouvelle version (REGLES["version"] + 1) et nouvelle DEBUT_TEST.
L'empreinte affichée dans le rapport permet de vérifier que rien n'a bougé.

Aucun ordre réel n'est passé. Ce n'est pas un conseil en investissement.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import donnees                                                  # noqa: E402
import moteur                                                   # noqa: E402

DEBUT_TEST = "2026-11-16"
CAPITAL = 10_000.0

REGLES = {
    "version": 1,
    "fige_le": "2026-11-14",
    "capital": CAPITAL,
    "frais_par_ordre": 0.0015,          # 0,10 % de courtage + 0,05 % d'écart achat-vente
    "execution": "décision à la clôture d'une séance, exécution à la clôture de la suivante",
    "eligibilite": {"historique_min": 260, "capitaux_min_40j": 5e6, "saut_max_252j": 0.60},
    "strategies": {
        "moteur": {"nom": "Moteur actuel", "frequence": 10, "lignes": 10,
                   "selection": "scan publié côté hausse (sûreté >= 6, 3 par secteur), 10 % par ligne"},
        "momentum": {"nom": "Momentum", "frequence": 21, "lignes": 20, "plafond_secteur": 4,
                     "poids_max": 0.10, "classement": "moyenne des rangs (dans la zone) de la "
                     "hausse 12 mois et 6 mois, hors dernier mois", "poids": "inverse de la volatilité 60 j",
                     "filtre_marche": False},
        "momentum_filtre": {"nom": "Momentum + filtre", "frequence": 21, "lignes": 20,
                            "plafond_secteur": 4, "poids_max": 0.10, "filtre_marche": True,
                            "mm_filtre": 200},
    },
    "reference": "univers entier à poids égaux, réajusté chaque jour, sans frais",
}
EMPREINTE = hashlib.sha256(json.dumps(REGLES, sort_keys=True, ensure_ascii=False)
                           .encode()).hexdigest()[:10]
ORDRE = ["moteur", "momentum", "momentum_filtre"]
FRAIS = REGLES["frais_par_ordre"]
OUT = donnees.RESULTATS


# ------------------------------------------------------------------------------ données
class Marche:
    """Matrices dates x valeurs et indicateurs nécessaires aux trois stratégies."""

    def __init__(self, cours, univers):
        self.c = cours.pivot(index="date", columns="ticker", values="close").sort_index()
        v = cours.pivot(index="date", columns="ticker", values="volume").reindex_like(self.c)
        self.dates = self.c.index.to_numpy(dtype=str)
        self.tickers = self.c.columns.to_numpy(dtype=str)
        self.cf = self.c.ffill()                                       # pour valoriser
        r = self.c / self.cf.shift(1) - 1                              # depuis la dernière cotation
        saut = r.abs() > REGLES["eligibilite"]["saut_max_252j"]
        self.r = r.mask(saut)                                          # aberrations exclues

        el = REGLES["eligibilite"]
        historique = self.c.notna().cumsum()
        capitaux = v.rolling(40, min_periods=20).mean() * self.cf
        saut_recent = saut.astype(float).rolling(252, min_periods=1).max() > 0
        self.eligible = (historique >= el["historique_min"]) & (capitaux >= el["capitaux_min_40j"]) \
            & ~saut_recent & self.c.notna()

        mom12 = self.cf.shift(21) / self.cf.shift(252) - 1
        mom6 = self.cf.shift(21) / self.cf.shift(126) - 1
        place = univers["place"].reindex(self.tickers).fillna("")
        zone = np.where(place.to_numpy() == "US", "US", "Europe")
        rang = pd.DataFrame(np.nan, index=self.c.index, columns=self.c.columns)
        for z in ("US", "Europe"):
            col = self.c.columns[zone == z]
            if len(col):
                rang[col] = (mom12[col].rank(axis=1, pct=True) + mom6[col].rank(axis=1, pct=True)) / 2
        self.mom = rang.where(self.eligible)
        self.vol = self.r.rolling(60, min_periods=40).std()

        rm = self.r.mean(axis=1).fillna(0.0)                           # référence équipondérée
        self.indice = (1 + rm).cumprod()
        self.rm = rm
        self.filtre_ok = self.indice >= self.indice.rolling(200, min_periods=200).mean()

        self.secteur = univers["secteur"].reindex(self.tickers).fillna("").to_numpy()
        self.nom = univers["nom"].reindex(self.tickers).fillna("").to_numpy()

        sc = moteur.scorer(cours[["date", "ticker", "close", "volume"]], toutes_les_dates=True)
        self.score = sc.pivot(index="date", columns="ticker", values="score").reindex_like(self.c)
        self.surete = sc.pivot(index="date", columns="ticker", values="surete").reindex_like(self.c)


# ------------------------------------------------------------------------------ sélection
def poids_moteur(m, i):
    sc, su = m.score.iloc[i], m.surete.iloc[i]
    ok = (sc > 0) & m.c.iloc[i].notna()
    if not ok.any():
        return np.zeros(len(m.tickers))
    cand = pd.DataFrame({"ticker": m.tickers[ok.to_numpy()], "secteur": m.secteur[ok.to_numpy()],
                         "surete": su[ok].astype(int).to_numpy(), "score_final": sc[ok].to_numpy()})
    retenus, _ = moteur.selectionner(cand)
    w = np.zeros(len(m.tickers))
    w[np.isin(m.tickers, retenus)] = 1.0 / REGLES["strategies"]["moteur"]["lignes"]
    return w


def poids_momentum(m, i, regle):
    w = np.zeros(len(m.tickers))
    if regle.get("filtre_marche") and not bool(m.filtre_ok.iloc[i]):
        return w                                                       # marché baissier : liquidités
    mom = m.mom.iloc[i].to_numpy()
    ordre = [j for j in np.argsort(-np.nan_to_num(mom, nan=-1.0)) if np.isfinite(mom[j])]
    choisis, par_secteur = [], {}
    for j in ordre:
        s = m.secteur[j] or "?"
        if s != "?" and par_secteur.get(s, 0) >= regle["plafond_secteur"]:
            continue
        par_secteur[s] = par_secteur.get(s, 0) + 1
        choisis.append(j)
        if len(choisis) == regle["lignes"]:
            break
    if not choisis:
        return w
    vol = m.vol.iloc[i].to_numpy()[choisis]
    vol = np.where(np.isfinite(vol) & (vol > 0), vol, np.nanmedian(vol) if np.isfinite(vol).any() else 0.02)
    x = 1 / vol
    x = x / x.sum()
    for _ in range(50):                                                # plafond par ligne
        trop = x > regle["poids_max"] + 1e-12
        if not trop.any():
            break
        surplus = (x[trop] - regle["poids_max"]).sum()
        x[trop] = regle["poids_max"]
        libres = ~trop & (x < regle["poids_max"])
        if not libres.any():
            break
        x[libres] += surplus * x[libres] / x[libres].sum()
    w[choisis] = x
    return w


def poids(m, strategie, i):
    if strategie == "moteur":
        return poids_moteur(m, i)
    return poids_momentum(m, i, REGLES["strategies"][strategie])


# ------------------------------------------------------------------------------ simulation
def simuler(m, strategie, debut, fin, journal=False):
    """Simule de l'indice debut à fin inclus. Renvoie valeurs, ordres, frais, positions, prévu."""
    freq = REGLES["strategies"][strategie]["frequence"]
    px_tout = m.cf.to_numpy()
    cash, parts = CAPITAL, np.zeros(len(m.tickers))
    valeurs, ordres, frais_total, prevu = [], [], 0.0, None
    for i in range(debut, fin + 1):
        px = px_tout[i]
        tenu = np.nan_to_num(parts * px)
        if prevu is not None:                                          # exécution à cette clôture
            V = cash + tenu.sum()
            negociable = np.isfinite(px)
            cible = np.where(negociable, prevu * V, tenu)
            frais = FRAIS * np.abs(cible - tenu).sum()
            cible = cible * (V - frais) / V
            frais = FRAIS * np.abs(cible - tenu).sum()
            nouv = np.where(negociable, np.divide(cible, px, out=np.zeros_like(cible),
                                                  where=negociable & (px > 0)), parts)
            if journal:
                for j in np.nonzero(np.abs(cible - tenu) > 1.0)[0]:
                    ordres.append({"date": m.dates[i], "ticker": m.tickers[j], "nom": m.nom[j],
                                   "sens": "achat" if cible[j] > tenu[j] else "vente",
                                   "montant": round(float(abs(cible[j] - tenu[j])), 2),
                                   "cours": round(float(px[j]), 4)})
            parts = nouv
            frais_total += frais
            cash = V - frais - float(np.nan_to_num(parts * px).sum())
            tenu = np.nan_to_num(parts * px)
            prevu = None
        valeurs.append(cash + tenu.sum())
        if (i - debut) % freq == 0:
            prevu = poids(m, strategie, i)                             # exécuté à la séance suivante
    serie = pd.Series(valeurs, index=m.dates[debut:fin + 1])
    pos = np.nan_to_num(parts * px_tout[fin])
    positions = [{"ticker": m.tickers[j], "nom": m.nom[j], "secteur": m.secteur[j],
                  "poids": round(float(pos[j] / serie.iloc[-1]), 4)}
                 for j in np.argsort(-pos) if pos[j] > 1.0]
    return {"valeurs": serie, "ordres": ordres, "frais": frais_total, "positions": positions,
            "liquidites": round(float(cash / serie.iloc[-1]), 4),
            "prevu": prevu}


def reference(m, debut, fin):
    rm = m.rm.iloc[debut + 1:fin + 1].to_numpy()
    return pd.Series(CAPITAL * np.concatenate([[1.0], np.cumprod(1 + rm)]), index=m.dates[debut:fin + 1])


# ------------------------------------------------------------------------------ statistiques
def stats(v, ref):
    jours = (pd.Timestamp(v.index[-1]) - pd.Timestamp(v.index[0])).days
    ans = max(jours / 365.25, 1e-9)
    an = lambda s: (s.iloc[-1] / s.iloc[0]) ** (1 / ans) - 1 if ans >= 1 else s.iloc[-1] / s.iloc[0] - 1  # noqa: E731
    r = v.pct_change().dropna()
    par_an = len(r) / ans if ans > 0 else 252
    idx = pd.to_datetime(v.index)
    mois = lambda s: pd.Series(s.to_numpy(), index=idx).resample("ME").last()  # noqa: E731
    ex = (mois(v).pct_change() - mois(ref).pct_change()).dropna()
    t = float(ex.mean() / (ex.std(ddof=1) / np.sqrt(len(ex)))) if len(ex) > 2 and ex.std() > 0 else np.nan
    return {"depuis": v.index[0], "jusqua": v.index[-1], "valeur": float(v.iloc[-1]),
            "total": float(v.iloc[-1] / v.iloc[0] - 1), "annuel": float(an(v)),
            "annuel_ref": float(an(ref)), "ecart_annuel": float(an(v) - an(ref)),
            "volatilite": float(r.std() * np.sqrt(par_an)) if len(r) > 2 else np.nan,
            "pire_baisse": float((v / v.cummax() - 1).min()),
            "pire_baisse_ref": float((ref / ref.cummax() - 1).min()),
            "mois": int(len(ex)), "mois_gagnants": float((ex > 0).mean()) if len(ex) else np.nan,
            "t_mensuel": t, "annualise": ans >= 1}


def par_annee(series):
    idx = pd.to_datetime(next(iter(series.values())).index)
    out = {}
    for nom, s in series.items():
        a = pd.Series(s.to_numpy(), index=idx)
        fin = a.groupby(a.index.year).last()
        debut = pd.concat([pd.Series([a.iloc[0]], index=[fin.index[0] - 1]), fin]).shift(1).dropna()
        out[nom] = (fin / debut.reindex(fin.index) - 1)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------ rapport
def pc(x, nd=1, signe=True):
    if x is None or not np.isfinite(x):
        return "—"
    return (f"{100 * x:+.{nd}f} %" if signe else f"{100 * x:.{nd}f} %").replace(".", ",")


def eur(x):
    return f"{x:,.0f}".replace(",", " ") + " €"


def fr(x, nd=1):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.{nd}f}".replace(".", ",")


def section_strategies(res, ref_stats, titre_valeur=True):
    lignes = ["| Stratégie | Valeur | Rendement" + (" annuel" if ref_stats["annualise"] else "") +
              " | Écart avec le marché | Pire baisse | Mois gagnants | t mensuel | Frais payés |",
              "|---|---|---|---|---|---|---|---|"]
    k = "annuel" if ref_stats["annualise"] else "total"
    for s in ORDRE:
        st = res[s]["stats"]
        ecart = st["annuel"] - st["annuel_ref"] if ref_stats["annualise"] else st["total"] - ref_stats["total"]
        lignes.append(f"| {REGLES['strategies'][s]['nom']} | {eur(st['valeur'])} | {pc(st[k])} | "
                      f"**{pc(ecart)}** | {pc(st['pire_baisse'], signe=False)} | "
                      f"{pc(st['mois_gagnants'], 0, False)} | {fr(st['t_mensuel'])} | {eur(res[s]['frais'])} |")
    lignes.append(f"| *Marché (référence)* | {eur(ref_stats['valeur'])} | {pc(ref_stats[k])} | — | "
                  f"{pc(ref_stats['pire_baisse'], signe=False)} | — | — | 0 € |")
    return lignes


def ecrire(m, hist, direct, debut_hist, i_test):
    L = ["# Portefeuille fictif", "",
         f"Règles **version {REGLES['version']}**, figées le {REGLES['fige_le']} · empreinte `{EMPREINTE}` · "
         f"données jusqu'au **{m.dates[-1]}**", "",
         "> Argent fictif : aucun ordre réel n'est passé. Frais de 0,15 % par ordre déduits. "
         "Rendements en devise locale (change ignoré). Univers = composition actuelle des indices : "
         "le passé est flatté (biais du survivant), surtout pour le momentum. Ce n'est pas un conseil "
         "en investissement.", ""]

    L += ["## 1. Suivi en direct — le vrai test", ""]
    if direct is None:
        L += [f"Départ le **{DEBUT_TEST}** avec {eur(CAPITAL)} par stratégie. "
              "Les premiers achats sont décidés à la clôture de cette séance et exécutés à la suivante.", ""]
    else:
        L += [f"Départ le {DEBUT_TEST} avec {eur(CAPITAL)} par stratégie, sur des cours qui n'existaient "
              "pas quand les règles ont été écrites.", ""]
        L += section_strategies(direct, direct["ref_stats"])
        L += ["", "Moins de 6 mois de suivi : les écarts relèvent encore largement du hasard." if
              direct["ref_stats"]["mois"] < 6 else "", ""]
        for s in ORDRE:
            d = direct[s]
            L += [f"### {REGLES['strategies'][s]['nom']} — positions au {m.dates[-1]}", ""]
            if d["positions"]:
                L += ["| Valeur | Nom | Secteur | Poids |", "|---|---|---|---|"]
                L += [f"| **{p['ticker']}** | {p['nom'][:30]} | {p['secteur']} | {pc(p['poids'], 1, False)} |"
                      for p in d["positions"]]
            L += [f"", f"Liquidités : {pc(d['liquidites'], 1, False)}"]
            if d["prevu"] is not None:
                L += ["", "**Réajustement décidé ce soir**, exécuté à la clôture de la prochaine séance : " +
                      (", ".join(f"{m.tickers[j]} {pc(d['prevu'][j], 1, False)}"
                                 for j in np.argsort(-d["prevu"]) if d["prevu"][j] > 0) or
                       "tout en liquidités") + "."]
            L.append("")

    L += ["## 2. Simulation sur le passé", "",
          f"Du **{hist['ref_stats']['depuis']}** au **{hist['ref_stats']['jusqua']}**, mêmes règles, "
          "mêmes frais. Écart avec le marché et t mensuel : la stratégie ne bat le marché de façon "
          "crédible que si l'écart est positif **et** le t supérieur à 2.", ""]
    L += section_strategies(hist, hist["ref_stats"])
    an = par_annee({**{REGLES["strategies"][s]["nom"]: hist[s]["valeurs"] for s in ORDRE},
                    "Marché": hist["ref"]})
    L += ["", "### Année par année", "", "| Année | " + " | ".join(an.columns) + " |",
          "|---|" + "---|" * len(an.columns)]
    for y, row in an.iterrows():
        L.append(f"| {y} | " + " | ".join(pc(x) for x in row) + " |")

    L += ["", "## 3. Critères de passage à un compte de démonstration", "",
          f"Fixés le {REGLES['fige_le']}, avant le début du test :", "",
          "| Critère | " + " | ".join(REGLES["strategies"][s]["nom"] for s in ORDRE) + " |",
          "|---|" + "---|" * len(ORDRE)]
    ok = lambda b: "oui" if b else "non"                               # noqa: E731
    c1 = [hist[s]["stats"]["ecart_annuel"] > 0 and (hist[s]["stats"]["t_mensuel"] or 0) > 2 for s in ORDRE]
    hist_ans = hist["ref_stats"]["annualise"] and \
        (pd.Timestamp(hist["ref_stats"]["jusqua"]) - pd.Timestamp(hist["ref_stats"]["depuis"])).days > 8 * 365
    if direct is None:
        c2 = c3 = [False] * len(ORDRE)
    else:
        c2 = [direct["ref_stats"]["mois"] >= 6] * len(ORDRE)
        c3 = [direct[s]["stats"]["total"] > direct["ref_stats"]["total"] for s in ORDRE]
    L += [f"| Simulation sur au moins 8 ans | " + " | ".join([ok(hist_ans)] * len(ORDRE)) + " |",
          f"| Simulation : bat le marché, t > 2 | " + " | ".join(ok(x) for x in c1) + " |",
          f"| Suivi en direct depuis au moins 6 mois | " + " | ".join(ok(x) for x in c2) + " |",
          f"| Suivi en direct : bat le marché | " + " | ".join(ok(x) for x in c3) + " |",
          "| Pire baisse acceptable pour Pierre | à fixer | à fixer | à fixer |", ""]

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "portefeuille.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    cours = donnees.charger_cours()
    univers = donnees.charger_univers()
    m = Marche(cours, univers)
    n = len(m.dates)
    # premier jour où le momentum est calculable pour l'essentiel de l'univers
    couvert = m.mom.notna().sum(axis=1).to_numpy()
    candidats = np.nonzero(couvert >= 0.5 * max(couvert.max(), 1))[0]
    i_test = int(np.searchsorted(m.dates, DEBUT_TEST))
    if len(candidats) == 0:
        raise SystemExit("Historique insuffisant (il faut plus d'un an de cotations).")
    debut_hist = int(candidats[0])
    fin_hist = min(i_test, n) - 1
    if fin_hist - debut_hist < 21:
        raise SystemExit("Historique insuffisant avant DEBUT_TEST pour la simulation.")

    hist = {s: simuler(m, s, debut_hist, fin_hist) for s in ORDRE}
    hist["ref"] = reference(m, debut_hist, fin_hist)
    hist["ref_stats"] = stats(hist["ref"], hist["ref"])
    for s in ORDRE:
        hist[s]["stats"] = stats(hist[s]["valeurs"], hist["ref"])

    direct = None
    if i_test < n:
        direct = {s: simuler(m, s, i_test, n - 1, journal=True) for s in ORDRE}
        direct["ref"] = reference(m, i_test, n - 1)
        direct["ref_stats"] = stats(direct["ref"], direct["ref"])
        for s in ORDRE:
            direct[s]["stats"] = stats(direct[s]["valeurs"], direct["ref"])

    ecrire(m, hist, direct, debut_hist, i_test)

    # fichiers de données
    blocs = []
    for periode, res in (("simulation", hist), ("direct", direct)):
        if res is None:
            continue
        b = pd.DataFrame({REGLES["strategies"][s]["nom"]: res[s]["valeurs"] for s in ORDRE})
        b["Marché"] = res["ref"]
        b.insert(0, "periode", periode)
        blocs.append(b.round(2).rename_axis("date").reset_index())
    pd.concat(blocs).to_csv(os.path.join(OUT, "portefeuille-valeurs.csv"), index=False)
    if direct is not None:
        pd.DataFrame([dict(o, strategie=REGLES["strategies"][s]["nom"]) for s in ORDRE
                      for o in direct[s]["ordres"]],
                     columns=["date", "strategie", "ticker", "nom", "sens", "montant", "cours"]) \
          .to_csv(os.path.join(OUT, "portefeuille-ordres.csv"), index=False)
    resume = {"version": REGLES["version"], "empreinte": EMPREINTE, "debut_test": DEBUT_TEST,
              "donnees_jusqua": m.dates[-1], "regles": REGLES,
              "simulation": {s: hist[s]["stats"] for s in ORDRE} | {"marche": hist["ref_stats"]},
              "direct": None if direct is None else
              {s: dict(direct[s]["stats"], positions=direct[s]["positions"],
                       liquidites=direct[s]["liquidites"]) for s in ORDRE} | {"marche": direct["ref_stats"]}}
    with open(os.path.join(OUT, "portefeuille.json"), "w", encoding="utf-8") as fh:
        json.dump(resume, fh, ensure_ascii=False, indent=1, default=lambda x: None if x != x else float(x))

    print(f"Portefeuille fictif (règles v{REGLES['version']}, empreinte {EMPREINTE})")
    print(f"Simulation {m.dates[debut_hist]} -> {m.dates[fin_hist]}")
    for s in ORDRE:
        st = hist[s]["stats"]
        print(f"  {REGLES['strategies'][s]['nom']:<20} annuel {pc(st['annuel']):>9}  écart {pc(st['ecart_annuel']):>9}"
              f"  t {fr(st['t_mensuel'])}  pire baisse {pc(st['pire_baisse'], signe=False)}")
    print(f"  {'Marché':<20} annuel {pc(hist['ref_stats']['annuel']):>9}")
    print("Suivi en direct : " + ("pas encore commencé" if direct is None else
                                  f"{len(direct['ref'])} séance(s) depuis le {DEBUT_TEST}"))


if __name__ == "__main__":
    main()
