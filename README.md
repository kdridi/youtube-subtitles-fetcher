# YouTube subtitles fetcher

Petit outil configurable pour lister les vidéos d'une chaîne, d'une playlist ou d'une liste d'URLs YouTube, puis récupérer leurs sous-titres avec `yt-dlp`.

L'objectif est de constituer un corpus local de transcriptions réutilisable ensuite par des LLM, par exemple pour identifier quelles vidéos regarder afin d'apprendre un sujet donné.

## Installation avec uv

Ce projet utilise [`uv`](https://docs.astral.sh/uv/) d'Astral pour gérer l'environnement Python et les dépendances.

```bash
uv sync
```

Les dépendances Python déclarées dans `pyproject.toml` incluent `PyYAML`, `yt-dlp` et `streamlit`. Il n'est donc pas nécessaire d'installer `yt-dlp` avec `brew` si tu lances le script via `uv run`.

## Configuration

Si nécessaire, crée ta configuration locale depuis l'exemple :

```bash
cp config.example.yaml config.yaml
```

Puis édite `config.yaml`.

La configuration actuelle cible :

```yaml
https://www.youtube.com/@indydevdan
```

avec l'onglet `videos`, puis récupère les sous-titres anglais manuels et automatiques au format `vtt`. Tu peux ajouter `shorts` ou `streams` dans `tabs` si la chaîne possède ces onglets.

Pour accéder aux vidéos visibles uniquement via ton compte, active les cookies :

```yaml
youtube:
  use_cookies: true
  cookies_from_browser: "chrome" # ou firefox, safari, edge, brave, chromium
```

Cela ne contourne aucune restriction : `yt-dlp` utilisera seulement les droits de ton navigateur connecté.

## Interface graphique locale

Lance l'interface Streamlit :

```bash
uv run streamlit run app.py
```

L'interface permet de :

- construire un fichier `config.yaml` avec des garde-fous ;
- choisir une chaîne et/ou des playlists ;
- choisir le navigateur à utiliser pour les cookies ;
- limiter le traitement à quelques vidéos pour les tests ;
- lancer le listing ou le téléchargement avec logs et progression.

## Utilisation CLI

Lister les vidéos uniquement :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
```

Lister puis récupérer les sous-titres :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml
```

Reprendre uniquement la récupération des sous-titres à partir du listing existant :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --subtitles-only
```

## Sortie

Les fichiers sont écrits dans :

```text
data/indydevdan/
  video_urls.txt
  videos.jsonl
  subtitles/
    VIDEO_ID/
      titre [VIDEO_ID].en.vtt
      titre [VIDEO_ID].info.json
  report.json
```

## Tester sur peu de vidéos

Dans `config.yaml`, mets par exemple :

```yaml
processing:
  limit: 3
```

Puis relance le script.

## Documentation

- Validation sur une autre machine : [`docs/VALIDATION.md`](docs/VALIDATION.md)
- Reprise du contexte projet : [`docs/HANDOFF.md`](docs/HANDOFF.md)
- Diagnostic des problèmes courants : [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- Évolutions envisagées : [`docs/ROADMAP.md`](docs/ROADMAP.md)
