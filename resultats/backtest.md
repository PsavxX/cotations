# Backtest de l'algorithme

Periode : **2024-02-26 → 2026-11-13** · 788 valeurs · 536 769 couples valeur-seance

A chaque seance, le moteur ne voit que le passe. « Rendement du pari » = ce que le cours a fait ensuite, dans le sens annonce. « Relatif au marche » = le meme, une fois retire le mouvement moyen de la zone (US ou Europe) : **c'est la colonne qui compte.** Positive, l'algorithme choisit mieux que le hasard ; nulle ou negative, non.

## 1. Le score contient-il de l'information ?

| Horizon | Observations | Correlation score / rendement | Correlation score / rendement relatif | Derive du marche |
|---|---|---|---|---|
| 1 seance | 535 981 | -0,015 | **-0,010** | +0,08 % |
| 3 seances | 534 405 | -0,019 | **-0,007** | +0,23 % |
| 5 seances | 532 829 | -0,021 | **-0,006** | +0,37 % |
| 10 seances | 528 889 | -0,023 | **+0,003** | +0,72 % |

Correlation de rang (Spearman). Une valeur de +0,02 a +0,05 sur des centaines de milliers d'observations est faible mais reelle ; proche de zero ou negative, le score n'apporte rien a cet horizon.

## 2. La note de surete, a 5 seances

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Surete 8-10 · hausse | 59 188 | 52,4 % | +0,15 % | **-0,07 %** |
| Surete 8-10 · baisse | 37 298 | 44,9 % | -0,38 % | **+0,13 %** |
| Surete 6-7 · hausse | 71 752 | 52,7 % | +0,21 % | **-0,07 %** |
| Surete 6-7 · baisse | 52 297 | 45,0 % | -0,39 % | **+0,15 %** |
| Surete 4-5 · hausse | 83 428 | 53,3 % | +0,30 % | **-0,04 %** |
| Surete 4-5 · baisse | 77 118 | 45,6 % | -0,42 % | **+0,01 %** |
| Surete 1-3 · hausse | 76 674 | 53,0 % | +0,35 % | **-0,05 %** |
| Surete 1-3 · baisse | 75 074 | 46,3 % | -0,74 % | **-0,39 %** |

### A 10 seances

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Surete 8-10 · hausse | 58 073 | 53,3 % | +0,41 % | **-0,05 %** |
| Surete 8-10 · baisse | 37 177 | 43,2 % | -0,92 % | **+0,16 %** |
| Surete 6-7 · hausse | 71 048 | 53,3 % | +0,45 % | **-0,07 %** |
| Surete 6-7 · baisse | 52 023 | 43,7 % | -0,81 % | **+0,23 %** |
| Surete 4-5 · hausse | 82 868 | 53,7 % | +0,54 % | **-0,06 %** |
| Surete 4-5 · baisse | 76 655 | 45,1 % | -0,72 % | **+0,15 %** |
| Surete 1-3 · hausse | 76 304 | 53,5 % | +0,73 % | **+0,04 %** |
| Surete 1-3 · baisse | 74 741 | 46,2 % | -1,21 % | **-0,53 %** |

Si la note vaut quelque chose, le rendement relatif doit **augmenter avec elle**. S'il est plat ou inverse, la note ne mesure pas ce qu'elle pretend.

## 3. La selection publiee, rejouee sur le passe

Regles du scan : note ≥ 6, au plus 3 valeurs par secteur, 10 par cote. Dates espacees de l'horizon (pas de chevauchement).

### A 5 seances — 137 dates rejouees

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| **Hausse** — toute la periode | 1 357 | 55,0 % | +0,27 % | **-0,17 %** |
| Hausse · 2024 | 430 | 60,0 % | +0,56 % | **-0,17 %** |
| Hausse · 2025 | 497 | 53,5 % | +0,03 % | **-0,31 %** |
| Hausse · 2026 | 430 | 51,9 % | +0,26 % | **+0,00 %** |
| **Baisse** — toute la periode | 1 352 | 46,5 % | -0,30 % | **+0,14 %** |
| Baisse · 2024 | 426 | 45,5 % | -0,28 % | **+0,29 %** |
| Baisse · 2025 | 496 | 48,8 % | -0,18 % | **+0,16 %** |
| Baisse · 2026 | 430 | 44,9 % | -0,45 % | **-0,04 %** |

### A 10 seances — 69 dates rejouees

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| **Hausse** — toute la periode | 677 | 53,9 % | +0,65 % | **-0,01 %** |
| Hausse · 2024 | 220 | 53,2 % | +0,94 % | **-0,01 %** |
| Hausse · 2025 | 247 | 57,1 % | +0,86 % | **+0,28 %** |
| Hausse · 2026 | 210 | 51,0 % | +0,09 % | **-0,36 %** |
| **Baisse** — toute la periode | 680 | 47,2 % | -0,56 % | **+0,20 %** |
| Baisse · 2024 | 220 | 43,6 % | -0,70 % | **+0,12 %** |
| Baisse · 2025 | 250 | 50,0 % | -0,38 % | **+0,36 %** |
| Baisse · 2026 | 210 | 47,6 % | -0,63 % | **+0,10 %** |

## 4. Hypothese H1 — cote hausse, RSI au-dessus de 70

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Hausse, note ≥ 6, RSI > 70 (5 seances) | 35 004 | 51,6 % | +0,14 % | **+0,01 %** |
| Hausse, note ≥ 6, RSI ≤ 70 (5 seances) | 95 936 | 52,9 % | +0,20 % | **-0,09 %** |

## Limites de ce test

- **Biais du survivant** : l'univers est celui des indices d'aujourd'hui. Les societes sorties des indices ou radiees depuis n'y figurent pas, ce qui embellit le passe.
- **Aucun frais** : ni courtage, ni ecart achat-vente, ni cout d'emprunt pour les paris a la baisse.
- **Observations liees** : les valeurs d'un meme secteur bougent ensemble, et les fenetres des sections 1 et 2 se chevauchent. Le nombre d'observations surestime la quantite d'information independante.
- **Technique seul** : le contexte d'actualite (macro) n'est pas rejoue.
- Un resultat passe ne garantit rien pour la suite.
