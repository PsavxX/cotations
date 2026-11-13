# Cotations — collecte et scan quotidiens automatisés

Chaque soir de bourse, ce dépôt fait trois choses tout seul :

1. **Collecte** les cotations de 803 valeurs (CAC 40, SBF 120, grandes capitalisations
   européennes, S&P 500).
2. **Scanne** : l'algorithme note chaque valeur et publie jusqu'à 10 valeurs orientées à la
   hausse et 10 à la baisse, avec un indice de sûreté de 1 à 10.
3. **Se contrôle** : il mesure le résultat de ses propres classements passés et rejoue
   l'algorithme sur tout l'historique.

## Où lire les résultats

| Fichier | Contenu |
|---|---|
| [`resultats/dernier.md`](resultats/dernier.md) | Le classement du jour, lisible ici même |
| [`resultats/backtest.md`](resultats/backtest.md) | Ce que l'algorithme vaut sur tout l'historique |
| [`resultats/bilan.md`](resultats/bilan.md) | Le résultat réel des classements publiés, à 5 et 10 séances |
| `resultats/scores-dernier.csv` | La note de **toutes** les valeurs analysées |
| `resultats/dernier.json` | Le classement du jour, pour une lecture par programme |
| `resultats/historique/` | Un fichier par scan publié |

Ces fichiers apparaissent après la première exécution.

## Mise en route

1. Dépôt GitHub **public** contenant ces fichiers.
2. **Settings → Actions → General → Workflow permissions → Read and write permissions.**
3. Amorçage : onglet **Actions → Collecte et scan quotidiens → Run workflow**, champ
   *depuis* = `2024-01-01`. Compter 20 à 40 minutes.
4. Ensuite l'automatisation tourne seule à 22 h 00 UTC, du lundi au vendredi.

## L'algorithme

`algo/moteur.py` calcule, pour chaque valeur et à partir des seules clôtures et volumes
passés, huit signaux bornés entre −1 et +1 :

| Signal | Poids | Mesure |
|---|---|---|
| `momentum` | 1,40 | variations à 5, 10 et 20 séances |
| `tendance_mm` | 1,30 | cours par rapport aux moyennes mobiles 10 / 20 / 40 |
| `macd` | 1,20 | histogramme MACD(12,26,9) et croisement |
| `pente` | 1,10 | pente de la régression sur les log-prix (20 séances) |
| `croisement_mm` | 1,00 | écart MM10 / MM20 et sa dynamique |
| `rsi` | 0,90 | niveau et pente du RSI(14) |
| `volume` | 0,70 | volume 5 j / 40 j, signé par le sens du mouvement |
| `position_40s` | 0,60 | position dans le range des 40 dernières séances |

- **Score directionnel** : moyenne pondérée des signaux. Le signe donne le sens.
- **Indice de sûreté (1-10)** : force du score, part des signaux alignés, netteté de la
  tendance (R²), moins des pénalités pour volatilité excessive, liquidité faible ou RSI extrême.
  Il note la confiance dans le signal, pas l'ampleur du gain espéré.
- **Règles de publication** : rien sous 6/10, au plus 3 valeurs d'un même secteur par côté,
  au plus 10 valeurs par côté. Une liste peut donc être courte, ou vide.

Le même code sert au scan du jour et au backtest : ce qui est publié est exactement ce qui
est testé.

### Contexte d'actualité (facultatif)

`algo/macro.json` permet d'ajouter un biais par secteur (guerre, pétrole, taux…). Il déplace
le score d'au plus ±0,11 et la confiance de ±12 %. Il n'est appliqué que pendant 10 jours
après sa date : un contexte périmé est ignoré, et le scan redevient purement technique.

## Organisation

```
.github/workflows/collecte.yml   l'automatisation quotidienne
scripts/collecte.py              téléchargement des cotations -> data/
scripts/secteurs.py              nom et secteur des valeurs européennes -> tickers/secteurs.csv
scripts/lecture.py               lecture des données et du dernier scan depuis l'extérieur
algo/moteur.py                   signaux, score, indice de sûreté, règles de sélection
algo/scan.py                     classement du jour -> resultats/
algo/bilan.py                    résultat des scans publiés -> resultats/bilan.md
algo/backtest.py                 test sur tout l'historique -> resultats/backtest.md
algo/macro.json                  contexte d'actualité facultatif
tickers/univers.csv              les 803 valeurs suivies
data/ohlcv-AAAA-MM.csv.gz        les cotations, un fichier par mois
```

Un fichier de cotations par mois, et seul le mois courant est réécrit : l'historique du dépôt
reste léger. Colonnes : `date, ticker, open, high, low, close, volume`, cours ajustés des
dividendes et des divisions.

## Modifier l'univers

Éditer `tickers/univers.csv`. Les tickers suivent la convention Yahoo Finance : `MC.PA` pour
Paris, `SHEL.L` pour Londres, `SAP.DE` pour Francfort, `AAPL` sans suffixe pour les États-Unis.
Les valeurs introuvables sont listées en bas de `data/INDEX.md` après chaque exécution.

## Ce que ce dépôt n'est pas

Une analyse technique automatique. Elle mesure l'inertie des cours et ne voit ni les
résultats d'entreprise, ni les annonces, ni les événements. Ce n'est ni une prédiction ni un
conseil en investissement, et `resultats/backtest.md` dit sans fard ce qu'elle vaut.
