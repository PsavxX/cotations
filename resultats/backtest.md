# Backtest de l'algorithme

Periode : **2015-02-26 → 2026-11-13** · 788 valeurs · 2 256 104 couples valeur-seance

A chaque seance, le moteur ne voit que le passe. « Rendement du pari » = ce que le cours a fait ensuite, dans le sens annonce. « Relatif au marche » = le meme, une fois retire le mouvement moyen de la zone (US ou Europe) : **c'est la colonne qui compte.** Positive, l'algorithme choisit mieux que le hasard ; nulle ou negative, non.

## 1. Le score contient-il de l'information ?

| Horizon | Observations | Correlation score / rendement | Correlation score / rendement relatif | Derive du marche |
|---|---|---|---|---|
| 1 seance | 2 255 316 | -0,018 | **-0,010** | +0,06 % |
| 3 seances | 2 253 740 | -0,022 | **-0,012** | +0,19 % |
| 5 seances | 2 252 164 | -0,025 | **-0,013** | +0,31 % |
| 10 seances | 2 248 224 | -0,028 | **-0,012** | +0,61 % |

Correlation de rang (Spearman). Une valeur de +0,02 a +0,05 sur des centaines de milliers d'observations est faible mais reelle ; proche de zero ou negative, le score n'apporte rien a cet horizon.

## 2. La note de surete, a 5 seances

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Surete 8-10 · hausse | 249 103 | 53,6 % | +0,17 % | **-0,08 %** |
| Surete 8-10 · baisse | 146 229 | 43,1 % | -0,40 % | **-0,01 %** |
| Surete 6-7 · hausse | 315 478 | 53,7 % | +0,20 % | **-0,05 %** |
| Surete 6-7 · baisse | 215 999 | 44,6 % | -0,32 % | **+0,00 %** |
| Surete 4-5 · hausse | 362 173 | 53,5 % | +0,24 % | **-0,03 %** |
| Surete 4-5 · baisse | 317 854 | 45,3 % | -0,35 % | **-0,02 %** |
| Surete 1-3 · hausse | 328 060 | 53,2 % | +0,31 % | **-0,02 %** |
| Surete 1-3 · baisse | 317 268 | 45,3 % | -0,52 % | **-0,14 %** |

### A 10 seances

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Surete 8-10 · hausse | 247 984 | 55,0 % | +0,39 % | **-0,11 %** |
| Surete 8-10 · baisse | 146 108 | 42,1 % | -0,76 % | **+0,01 %** |
| Surete 6-7 · hausse | 314 777 | 54,9 % | +0,42 % | **-0,10 %** |
| Surete 6-7 · baisse | 215 725 | 43,3 % | -0,62 % | **+0,00 %** |
| Surete 4-5 · hausse | 361 614 | 54,6 % | +0,46 % | **-0,06 %** |
| Surete 4-5 · baisse | 317 392 | 44,2 % | -0,67 % | **-0,03 %** |
| Surete 1-3 · hausse | 327 690 | 54,5 % | +0,69 % | **+0,04 %** |
| Surete 1-3 · baisse | 316 934 | 44,3 % | -0,93 % | **-0,19 %** |

Si la note vaut quelque chose, le rendement relatif doit **augmenter avec elle**. S'il est plat ou inverse, la note ne mesure pas ce qu'elle pretend.

## 3. La selection publiee, rejouee sur le passe

Regles du scan : note ≥ 6, au plus 3 valeurs par secteur, 10 par cote. Dates espacees de l'horizon (pas de chevauchement).

### A 5 seances — 590 dates rejouees

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| **Hausse** — toute la periode | 5 800 | 53,3 % | +0,23 % | **-0,07 %** |
| Hausse · 2015 | 416 | 49,5 % | +0,01 % | **+0,07 %** |
| Hausse · 2016 | 493 | 57,2 % | +0,36 % | **-0,11 %** |
| Hausse · 2017 | 510 | 55,3 % | +0,68 % | **+0,13 %** |
| Hausse · 2018 | 494 | 51,0 % | -0,19 % | **-0,07 %** |
| Hausse · 2019 | 500 | 54,2 % | +0,25 % | **-0,28 %** |
| Hausse · 2020 | 471 | 54,1 % | +0,61 % | **+0,15 %** |
| Hausse · 2021 | 500 | 55,4 % | +0,33 % | **-0,18 %** |
| Hausse · 2022 | 480 | 48,8 % | -0,24 % | **+0,03 %** |
| Hausse · 2023 | 499 | 51,9 % | +0,26 % | **-0,11 %** |
| Hausse · 2024 | 510 | 57,5 % | +0,54 % | **-0,04 %** |
| Hausse · 2025 | 497 | 51,1 % | -0,14 % | **-0,41 %** |
| Hausse · 2026 | 430 | 52,1 % | +0,20 % | **-0,02 %** |
| **Baisse** — toute la periode | 5 782 | 45,9 % | -0,38 % | **-0,06 %** |
| Baisse · 2015 | 430 | 47,4 % | +0,10 % | **+0,09 %** |
| Baisse · 2016 | 470 | 41,5 % | -0,95 % | **-0,49 %** |
| Baisse · 2017 | 510 | 40,8 % | -0,61 % | **-0,10 %** |
| Baisse · 2018 | 500 | 50,6 % | +0,31 % | **+0,30 %** |
| Baisse · 2019 | 500 | 43,4 % | -0,64 % | **-0,08 %** |
| Baisse · 2020 | 457 | 45,7 % | -0,56 % | **-0,20 %** |
| Baisse · 2021 | 500 | 44,4 % | -0,81 % | **-0,24 %** |
| Baisse · 2022 | 486 | 51,6 % | +0,28 % | **+0,06 %** |
| Baisse · 2023 | 498 | 43,0 % | -0,77 % | **-0,39 %** |
| Baisse · 2024 | 507 | 48,5 % | -0,35 % | **+0,05 %** |
| Baisse · 2025 | 494 | 47,6 % | -0,19 % | **+0,16 %** |
| Baisse · 2026 | 430 | 47,0 % | -0,27 % | **+0,09 %** |

### A 10 seances — 295 dates rejouees

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| **Hausse** — toute la periode | 2 896 | 55,4 % | +0,50 % | **-0,11 %** |
| Hausse · 2015 | 215 | 44,7 % | -0,46 % | **+0,04 %** |
| Hausse · 2016 | 250 | 60,8 % | +0,87 % | **-0,33 %** |
| Hausse · 2017 | 250 | 63,2 % | +1,43 % | **+0,34 %** |
| Hausse · 2018 | 248 | 52,4 % | +0,27 % | **+0,43 %** |
| Hausse · 2019 | 250 | 57,2 % | +0,32 % | **-0,83 %** |
| Hausse · 2020 | 237 | 54,9 % | +1,25 % | **+0,38 %** |
| Hausse · 2021 | 250 | 55,2 % | +0,12 % | **-0,78 %** |
| Hausse · 2022 | 239 | 51,5 % | -0,07 % | **+0,14 %** |
| Hausse · 2023 | 250 | 54,0 % | +0,53 % | **-0,17 %** |
| Hausse · 2024 | 250 | 63,6 % | +1,38 % | **+0,38 %** |
| Hausse · 2025 | 247 | 59,1 % | +0,38 % | **-0,21 %** |
| Hausse · 2026 | 210 | 44,3 % | -0,29 % | **-0,76 %** |
| **Baisse** — toute la periode | 2 876 | 44,5 % | -0,57 % | **+0,03 %** |
| Baisse · 2015 | 220 | 50,5 % | +1,06 % | **+0,82 %** |
| Baisse · 2016 | 235 | 37,9 % | -1,78 % | **-0,60 %** |
| Baisse · 2017 | 250 | 38,0 % | -1,34 % | **-0,32 %** |
| Baisse · 2018 | 250 | 44,0 % | -0,11 % | **-0,05 %** |
| Baisse · 2019 | 250 | 36,8 % | -1,40 % | **-0,30 %** |
| Baisse · 2020 | 227 | 43,2 % | -0,79 % | **+0,07 %** |
| Baisse · 2021 | 250 | 42,0 % | -1,09 % | **-0,14 %** |
| Baisse · 2022 | 243 | 46,5 % | -0,01 % | **-0,30 %** |
| Baisse · 2023 | 250 | 44,8 % | -0,47 % | **+0,08 %** |
| Baisse · 2024 | 247 | 50,6 % | -0,27 % | **+0,46 %** |
| Baisse · 2025 | 244 | 54,1 % | +0,04 % | **+0,56 %** |
| Baisse · 2026 | 210 | 47,1 % | -0,55 % | **+0,16 %** |

## 4. Hypothese H1 — cote hausse, RSI au-dessus de 70

| Perimetre | Observations | Sens correct | Rendement du pari | Rendement relatif au marche |
|---|---|---|---|---|
| Hausse, note ≥ 6, RSI > 70 (5 seances) | 148 202 | 52,1 % | +0,07 % | **-0,07 %** |
| Hausse, note ≥ 6, RSI ≤ 70 (5 seances) | 416 379 | 54,2 % | +0,23 % | **-0,06 %** |

## Limites de ce test

- **Biais du survivant** : l'univers est celui des indices d'aujourd'hui. Les societes sorties des indices ou radiees depuis n'y figurent pas, ce qui embellit le passe.
- **Aucun frais** : ni courtage, ni ecart achat-vente, ni cout d'emprunt pour les paris a la baisse.
- **Observations liees** : les valeurs d'un meme secteur bougent ensemble, et les fenetres des sections 1 et 2 se chevauchent. Le nombre d'observations surestime la quantite d'information independante.
- **Technique seul** : le contexte d'actualite (macro) n'est pas rejoue.
- Un resultat passe ne garantit rien pour la suite.
