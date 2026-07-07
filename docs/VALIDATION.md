# Procédure de validation sur une nouvelle machine

Cette procédure sert à vérifier qu'un clone frais du repository permet bien de :

1. installer l'environnement Python avec `uv` ;
2. lister les vidéos d'une chaîne ou d'une playlist YouTube ;
3. récupérer les sous-titres disponibles ;
4. produire les fichiers attendus dans `data/`.

## 1. Prérequis système

Sur la machine cible, vérifier que les outils suivants sont disponibles :

```bash
git --version
uv --version
```

Si `uv` n'est pas installé :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Puis ouvrir un nouveau terminal ou recharger le shell.

## 2. Cloner le repository

```bash
git clone <URL_DU_REPOSITORY>
cd <NOM_DU_REPOSITORY>
```

Exemple :

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
```

## 3. Installer les dépendances

```bash
uv sync
```

Cette commande crée l'environnement `.venv/` et installe les dépendances déclarées dans `pyproject.toml`, notamment :

- `PyYAML` ;
- `yt-dlp`.

## 4. Vérifier que le script démarre

```bash
uv run scripts/fetch_youtube_subtitles.py --help
```

Résultat attendu : l'aide du script doit s'afficher avec les options `--config`, `--list-only` et `--subtitles-only`.

## 5. Préparer une configuration de test

Si `config.yaml` n'existe pas encore :

```bash
cp config.example.yaml config.yaml
```

Pour un premier test rapide, limiter le nombre de vidéos dans `config.yaml` :

```yaml
processing:
  limit: 3
```

Tu peux aussi remplacer la source par une playlist ou une autre chaîne.

### Exemple chaîne

```yaml
sources:
  - name: example-channel
    type: channel
    url: "https://www.youtube.com/@indydevdan"
    tabs: ["videos"]
```

### Exemple playlist

```yaml
sources:
  - name: example-playlist
    type: playlist
    url: "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

## 6. Tester uniquement le listing des vidéos

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
```

Résultat attendu :

```text
data/<source>/
  video_urls.txt
  videos.jsonl
```

Vérifications :

```bash
wc -l data/*/video_urls.txt
head data/*/video_urls.txt
```

Le fichier `video_urls.txt` doit contenir des URLs YouTube.

## 7. Tester la récupération des sous-titres

Avec `processing.limit: 3` pour éviter un test trop long :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml
```

Résultat attendu :

```text
data/<source>/
  video_urls.txt
  videos.jsonl
  subtitles/
  report.json
```

Vérifier le rapport :

```bash
cat data/*/report.json
```

Au moins une vidéo devrait généralement avoir un fichier de sous-titres, par exemple :

```text
data/<source>/subtitles/<VIDEO_ID>/*.vtt
```

Note : certaines vidéos peuvent ne pas avoir de sous-titres dans la langue demandée. Dans ce cas, elles apparaîtront dans `report.json` comme sans sous-titres.

## 8. Tester la reprise à partir du listing existant

Supprimer éventuellement un dossier de sous-titres, puis relancer seulement l'étape sous-titres :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --subtitles-only
```

Résultat attendu : le script réutilise `videos.jsonl` ou `video_urls.txt` déjà présent dans `data/<source>/`.

## 9. Tester l'accès authentifié facultatif

Si tu veux récupérer les contenus visibles depuis ton compte YouTube connecté, active les cookies dans `config.yaml` :

```yaml
youtube:
  use_cookies: true
  cookies_from_browser: "chrome"
```

Autres valeurs possibles selon le navigateur :

```yaml
cookies_from_browser: "firefox"
cookies_from_browser: "safari"
cookies_from_browser: "brave"
cookies_from_browser: "edge"
cookies_from_browser: "chromium"
```

Puis relancer :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
```

Important : cette option ne contourne pas les restrictions YouTube. Elle permet seulement à `yt-dlp` d'utiliser les droits du compte déjà connecté dans le navigateur.

## 10. Critères de validation

Le projet est considéré fonctionnel si :

- `uv sync` réussit ;
- `uv run scripts/fetch_youtube_subtitles.py --help` fonctionne ;
- `--list-only` crée `video_urls.txt` et `videos.jsonl` ;
- l'exécution complète crée `subtitles/` et `report.json` ;
- le script peut être relancé sans tout casser ;
- le changement de source dans `config.yaml` permet de tester une autre chaîne ou playlist.

## 11. Nettoyer après test

Pour supprimer les données générées :

```bash
rm -rf data/
```

Pour supprimer l'environnement virtuel :

```bash
rm -rf .venv/
```
