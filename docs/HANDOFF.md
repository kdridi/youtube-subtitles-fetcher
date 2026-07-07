# Handoff — YouTube subtitles fetcher

## Objectif du projet

Ce repository sert à construire un corpus local de sous-titres YouTube à partir de chaînes, playlists ou listes d'URLs.

Le but final est de pouvoir exploiter ces transcriptions avec des LLM afin de déterminer quelles vidéos regarder pour apprendre un sujet donné.

## État actuel

Le projet contient deux modes d'utilisation :

1. **CLI** : `scripts/fetch_youtube_subtitles.py`
2. **Interface graphique locale Streamlit** : `app.py`

Les deux modes utilisent `yt-dlp` pour :

- lister les vidéos ;
- récupérer les sous-titres manuels et/ou automatiques ;
- sauvegarder les métadonnées vidéo ;
- produire un rapport JSON.

## Stack technique

- Python
- `uv` pour l'environnement et les dépendances
- `yt-dlp` pour YouTube
- `PyYAML` pour la configuration
- `Streamlit` pour l'interface locale

## Commandes principales

Installer :

```bash
uv sync
```

Créer une configuration locale :

```bash
cp config.example.yaml config.yaml
```

Lancer l'interface graphique :

```bash
uv run streamlit run app.py
```

Lister les vidéos en CLI :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
```

Lister puis télécharger les sous-titres en CLI :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml
```

Télécharger uniquement les sous-titres à partir d'un listing existant :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --subtitles-only
```

## Fichiers importants

```text
app.py                              # Interface Streamlit
scripts/fetch_youtube_subtitles.py  # CLI principal
config.example.yaml                 # Configuration modèle versionnée
config.yaml                         # Configuration locale ignorée par Git
data/                               # Données générées ignorées par Git
docs/VALIDATION.md                  # Procédure de validation complète
docs/HANDOFF.md                     # Ce document
docs/TROUBLESHOOTING.md             # Aide au diagnostic
docs/ROADMAP.md                     # Évolutions envisagées
```

## Garde-fous actuels

- `config.yaml` est ignoré par Git.
- `data/` est ignoré par Git.
- L'interface Streamlit limite par défaut les tests à 3 vidéos.
- Le mode illimité dans l'interface nécessite une confirmation explicite.
- L'interface refuse d'écrire en dehors du dossier du repository.
- L'utilisation des cookies navigateur est optionnelle.
- Les cookies eux-mêmes ne sont pas stockés dans le repository.

## Validation déjà effectuée

Validation manuelle réussie sur la chaîne :

```text
https://www.youtube.com/@indydevdan
```

Résultats observés :

- `uv sync` OK ;
- CLI `--help` OK ;
- interface Streamlit OK ;
- génération de `config.yaml` via interface OK ;
- listing de 204 vidéos OK ;
- téléchargement des sous-titres sur 3 vidéos OK ;
- génération de `.vtt`, `.info.json`, `report.json` OK ;
- logs et progression visibles dans l'interface OK ;
- pas de pollution Git après exécution OK.

## Limites connues

- La progression est calculée au niveau vidéo, pas au niveau exact du téléchargement interne de chaque sous-titre.
- `yt-dlp` peut afficher des warnings non bloquants liés à l'impersonation ou aux challenges JavaScript YouTube.
- Certaines vidéos peuvent ne pas avoir de sous-titres dans la langue demandée.
- Le mode `--subtitles-only` traite actuellement la première source configurée.
- Pas encore de nettoyage des fichiers `.vtt` vers texte brut optimisé LLM.
- Pas encore d'indexation, résumé, recherche sémantique ou scoring par sujet.

## Reprise conseillée après reset de conversation

1. Lire `README.md`.
2. Lire `docs/HANDOFF.md`.
3. Lire `docs/VALIDATION.md` si une nouvelle validation est nécessaire.
4. Pour travailler sur les erreurs YouTube, lire `docs/TROUBLESHOOTING.md`.
5. Pour les prochaines fonctionnalités, lire `docs/ROADMAP.md`.
