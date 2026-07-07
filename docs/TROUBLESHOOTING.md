# Troubleshooting

## `yt-dlp` affiche des warnings `impersonation`

Exemple :

```text
WARNING: The extractor specified to use impersonation for this download, but no impersonate target is available.
```

Ce warning n'est pas forcément bloquant. Si le résumé final indique :

```text
Erreurs: 0
Avec sous-titres: N
```

alors le téléchargement a fonctionné.

Action recommandée : ne rien changer tant que les sous-titres sont récupérés.

## Warnings `EJS`, `JS challenge`, `deno`

Exemples :

```text
WARNING: [youtube] [jsc] Remote components challenge solver script ...
WARNING: [youtube] ... n challenge solving failed: Some formats may be missing.
```

Ces warnings viennent des mécanismes de protection de YouTube. Ils peuvent apparaître même si les sous-titres sont récupérés correctement.

Action recommandée : vérifier le résumé final et la présence des fichiers `.vtt`.

Si cela devient bloquant, pistes possibles :

- mettre à jour les dépendances :

```bash
uv lock --upgrade
uv sync
```

- ajouter des arguments `yt-dlp` dans `config.yaml`, section `yt_dlp.extra_args` ;
- consulter la documentation `yt-dlp` sur les JS challenges.

## La chaîne n'a pas d'onglet `shorts` ou `streams`

Exemple :

```text
ERROR: [youtube:tab] @channel: This channel does not have a shorts tab
```

Ce n'est pas bloquant si l'onglet `videos` fonctionne.

Solution : ne garder que :

```yaml
tabs: ["videos"]
```

## Aucune vidéo trouvée

Vérifier :

1. que l'URL YouTube est correcte ;
2. que le type de source est correct : `channel`, `playlist`, `url`, `video`, `urls_file` ;
3. que la chaîne ou playlist est publique, ou que les cookies sont activés si nécessaire.

Test utile :

```bash
uv run scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
```

## Vidéos trouvées mais pas de sous-titres

Causes possibles :

- les vidéos n'ont pas de sous-titres ;
- la langue demandée n'existe pas ;
- les sous-titres automatiques sont désactivés dans la configuration ;
- YouTube bloque temporairement certaines requêtes.

Vérifier la configuration :

```yaml
subtitles:
  languages: ["en"]
  include_language_variants: true
  manual: true
  auto: true
```

## Accès avec compte YouTube

Pour utiliser les droits du compte connecté dans le navigateur :

```yaml
youtube:
  use_cookies: true
  cookies_from_browser: "chrome"
```

Navigateurs possibles selon la machine :

```yaml
cookies_from_browser: "firefox"
cookies_from_browser: "safari"
cookies_from_browser: "brave"
cookies_from_browser: "edge"
cookies_from_browser: "chromium"
```

Important : cette option ne contourne aucune restriction. Elle permet seulement à `yt-dlp` d'utiliser les droits du compte déjà connecté dans le navigateur.

## Streamlit ne démarre pas

Vérifier l'installation :

```bash
uv sync
uv run streamlit --version
```

Puis relancer :

```bash
uv run streamlit run app.py
```

## Streamlit indique que le port est déjà utilisé

Utiliser un autre port :

```bash
uv run streamlit run app.py --server.port 8502
```

## La configuration générée écrase un fichier existant

L'interface demande une confirmation explicite avant d'écraser un fichier existant.

En CLI, sauvegarder manuellement avant modification :

```bash
cp config.yaml config.backup.yaml
```

## Nettoyer les données générées

```bash
rm -rf data/
```

## Nettoyer l'environnement Python

```bash
rm -rf .venv/
uv sync
```
