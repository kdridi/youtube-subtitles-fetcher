# Roadmap

Cette roadmap liste les évolutions envisagées. Elle n'est pas un engagement d'ordre ou de priorité.

## Phase 1 — Récupération fiable des transcriptions

État : MVP validé.

- [x] Configuration YAML
- [x] Support chaîne YouTube
- [x] Support playlist YouTube
- [x] Listing vidéo via `yt-dlp`
- [x] Récupération sous-titres manuels et automatiques
- [x] Métadonnées `.info.json`
- [x] Rapport `report.json`
- [x] Interface Streamlit pour générer une configuration
- [x] Interface Streamlit pour lancer listing/téléchargement
- [x] Garde-fous pour tests courts et mode illimité

## Phase 2 — Qualité des données pour LLM

Objectif : transformer les `.vtt` en documents propres et exploitables.

Idées :

- convertir `.vtt` vers `.txt` ou `.md` ;
- supprimer timestamps, balises et répétitions ;
- conserver un mapping optionnel vers les timestamps ;
- produire un fichier par vidéo :

```text
data/<source>/transcripts/<VIDEO_ID>.md
```

- produire un index global :

```text
data/<source>/transcripts/index.jsonl
```

Champs possibles :

```json
{
  "video_id": "...",
  "title": "...",
  "url": "...",
  "duration": 1234,
  "transcript_path": "...",
  "language": "en"
}
```

## Phase 3 — Analyse LLM

Objectif : déterminer quelles vidéos regarder pour apprendre un sujet donné.

Fonctionnalités possibles :

- résumé court par vidéo ;
- résumé détaillé par vidéo ;
- extraction des outils, concepts et bibliothèques mentionnés ;
- classification par thèmes ;
- scoring d'une vidéo par rapport à une requête utilisateur ;
- génération d'une watchlist priorisée.

Exemple de sortie souhaitée :

```text
Sujet: multi-agent orchestration

1. Video A — score 92/100
   Pourquoi: traite directement de l'orchestration multi-agent avec Claude Code.

2. Video B — score 78/100
   Pourquoi: utile pour comprendre les modèles utilisés, mais moins pratique.
```

## Phase 4 — Indexation et recherche

Objectif : retrouver rapidement les vidéos pertinentes.

Options :

- index lexical local ;
- embeddings locaux ou API ;
- base vectorielle locale ;
- recherche hybride texte + vecteurs ;
- recherche par chaîne, playlist, outil, date, durée.

## Phase 5 — Améliorations de l'interface

Idées :

- aperçu des vidéos trouvées avant téléchargement ;
- sélection manuelle des vidéos à traiter ;
- meilleur suivi de progression multi-sources ;
- estimation de durée plus précise ;
- historique des runs ;
- bouton de nettoyage `data/` ;
- téléchargement du rapport depuis l'interface ;
- page d'analyse LLM.

## Phase 6 — Robustesse et performances

Idées :

- parallélisation contrôlée des téléchargements ;
- retry configurable ;
- rate limiting ;
- meilleure gestion des erreurs par vidéo ;
- support complet multi-sources en mode `--subtitles-only` ;
- tests unitaires ;
- tests d'intégration courts ;
- logs structurés.

## Phase 7 — Packaging

Options possibles :

- commande CLI installable ;
- image Docker ;
- application desktop légère ;
- template GitHub Actions pour validation de base.

## Priorité recommandée suivante

La prochaine étape la plus utile est probablement :

```text
Conversion VTT -> transcript texte/markdown propre
```

Raison : c'est le pont direct entre la récupération actuelle et l'exploitation LLM.
