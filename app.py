#!/usr/bin/env python3
"""Interface Streamlit pour générer et exécuter des configurations."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "fetch_youtube_subtitles.py"
YOUTUBE_RE = re.compile(r"^https://(www\.)?(youtube\.com|youtu\.be)/.+", re.IGNORECASE)
PROGRESS_RE = re.compile(r"^\[(\d+)/(\d+)\]")


BROWSERS = ["chrome", "firefox", "safari", "brave", "edge", "chromium"]
SUBTITLE_FORMATS = ["vtt", "srt", "ass", "ttml"]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "source"


def safe_project_path(raw: str, *, must_be_yaml: bool = False) -> Path:
    """Retourne un chemin situé dans le repository, ou lève ValueError."""
    if not raw.strip():
        raise ValueError("Le chemin ne peut pas être vide.")
    path = Path(raw).expanduser()
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (ROOT / path).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise ValueError("Par sécurité, le chemin doit rester dans le dossier du repository.")
    if must_be_yaml and resolved.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("Le fichier de configuration doit avoir l'extension .yaml ou .yml.")
    return resolved


def validate_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match(url.strip()))


def parse_lines(value: str) -> List[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def parse_languages(value: str) -> List[str]:
    langs = [part.strip() for part in value.split(",") if part.strip()]
    return langs or ["en"]


def build_config(
    *,
    source_name: str,
    channel_url: str,
    channel_tabs: List[str],
    playlist_urls: List[str],
    playlist_prefix: str,
    subtitle_languages: List[str],
    include_language_variants: bool,
    manual_subs: bool,
    auto_subs: bool,
    subtitle_format: str,
    output_dir: str,
    save_metadata: bool,
    overwrite: bool,
    limit: Optional[int],
    use_cookies: bool,
    cookies_from_browser: str,
    extra_args: List[str],
) -> Dict[str, Any]:
    sources: List[Dict[str, Any]] = []

    if channel_url.strip():
        sources.append(
            {
                "name": slugify(source_name or "youtube-channel"),
                "type": "channel",
                "url": channel_url.strip(),
                "tabs": channel_tabs or ["videos"],
            }
        )

    for index, url in enumerate(playlist_urls, start=1):
        sources.append(
            {
                "name": slugify(f"{playlist_prefix or source_name or 'playlist'}-{index}"),
                "type": "playlist",
                "url": url,
            }
        )

    return {
        "sources": sources,
        "subtitles": {
            "languages": subtitle_languages,
            "include_language_variants": include_language_variants,
            "manual": manual_subs,
            "auto": auto_subs,
            "format": subtitle_format,
        },
        "output": {
            "directory": output_dir,
            "save_video_urls": True,
            "save_listing_jsonl": True,
            "save_metadata": save_metadata,
            "overwrite": overwrite,
        },
        "processing": {
            "limit": limit,
        },
        "youtube": {
            "use_cookies": use_cookies,
            "cookies_from_browser": cookies_from_browser,
            "cookies_file": None,
        },
        "yt_dlp": {
            "binary": "yt-dlp",
            "extra_args": extra_args,
        },
    }


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def first_source_report_path(config: Dict[str, Any]) -> Optional[Path]:
    sources = config.get("sources") or []
    if not sources:
        return None
    source = sources[0]
    name = source.get("name") or source.get("url") or source.get("path") or "source"
    output_dir = Path(((config.get("output") or {}).get("directory")) or "./data")
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    return output_dir / slugify(str(name)) / "report.json"


def format_eta(start: float, done: int, total: int) -> str:
    if done <= 0 or total <= 0:
        return "ETA indisponible"
    elapsed = time.time() - start
    remaining = max(total - done, 0)
    seconds = int((elapsed / done) * remaining)
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"ETA ~ {hours}h{minutes:02d}m"
    if minutes:
        return f"ETA ~ {minutes}m{sec:02d}s"
    return f"ETA ~ {sec}s"


def run_fetcher(config_path: Path, mode: str) -> int:
    cmd = [sys.executable, "-u", str(SCRIPT), "--config", str(config_path)]
    if mode == "list-only":
        cmd.append("--list-only")
    elif mode == "subtitles-only":
        cmd.append("--subtitles-only")

    st.code(" ".join(cmd), language="bash")

    progress_bar = st.progress(0.0, text="En attente du démarrage…")
    status = st.empty()
    logs_box = st.empty()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    log_lines: List[str] = []
    start = time.time()
    done = 0
    total = 0
    assert process.stdout is not None

    for line in process.stdout:
        line = line.rstrip("\n")
        log_lines.append(line)
        if len(log_lines) > 600:
            log_lines = log_lines[-600:]

        match = PROGRESS_RE.match(line)
        if match:
            done = int(match.group(1)) - 1
            total = int(match.group(2))
        elif total and line.startswith("Résumé"):
            done = total

        if total:
            fraction = max(0.0, min(done / total, 1.0))
            progress_bar.progress(fraction, text=f"{done}/{total} vidéos — {format_eta(start, max(done, 1), total)}")
        status.text(line[:250] if line else " ")
        logs_box.text_area("Logs", "\n".join(log_lines), height=420)

    return_code = process.wait()
    if total:
        progress_bar.progress(1.0 if return_code == 0 else max(done / total, 0.0), text=f"Terminé — code {return_code}")
    else:
        progress_bar.progress(1.0 if return_code == 0 else 0.0, text=f"Terminé — code {return_code}")

    return return_code


def render_config_builder() -> None:
    st.header("Construire une configuration")
    st.info("Garde-fou par défaut : le fichier généré limite le traitement à 3 vidéos, sauf confirmation explicite.")

    with st.form("config_builder"):
        st.subheader("Source principale")
        source_name = st.text_input("Nom de la source", value="indydevdan")
        channel_url = st.text_input("URL de la chaîne YouTube", value="https://www.youtube.com/@indydevdan")
        channel_tabs = st.multiselect("Onglets de chaîne", ["videos", "shorts", "streams"], default=["videos"])

        st.subheader("Playlists optionnelles")
        use_playlists = st.checkbox("Ajouter une ou plusieurs playlists", value=False)
        playlist_prefix = st.text_input("Préfixe de nom pour les playlists", value="playlist", disabled=not use_playlists)
        playlists_raw = st.text_area("URLs de playlists, une par ligne", disabled=not use_playlists)

        st.subheader("Sous-titres")
        subtitle_languages_raw = st.text_input("Langues, séparées par des virgules", value="en")
        include_language_variants = st.checkbox("Inclure les variantes de langue, ex. en-*", value=True)
        manual_subs = st.checkbox("Récupérer les sous-titres manuels", value=True)
        auto_subs = st.checkbox("Récupérer les sous-titres automatiques", value=True)
        subtitle_format = st.selectbox("Format", SUBTITLE_FORMATS, index=0)

        st.subheader("Accès YouTube")
        use_cookies = st.checkbox("Utiliser les cookies du navigateur connecté", value=False)
        cookies_from_browser = st.selectbox("Navigateur", BROWSERS, index=0, disabled=not use_cookies)

        st.subheader("Exécution")
        limit_mode = st.radio("Limite de traitement", ["Test rapide : 3 vidéos", "Test élargi : 10 vidéos", "Illimité"], index=0)
        confirm_unlimited = False
        if limit_mode == "Illimité":
            confirm_unlimited = st.checkbox("Je confirme vouloir générer une configuration sans limite.", value=False)
        output_dir = st.text_input("Dossier de sortie", value="./data")
        save_metadata = st.checkbox("Sauvegarder les métadonnées .info.json", value=True)
        overwrite = st.checkbox("Écraser les fichiers déjà présents", value=False)
        extra_args_raw = st.text_input("Arguments yt-dlp additionnels, séparés par des espaces", value="")

        st.subheader("Fichier de configuration")
        target_path_raw = st.text_input("Chemin du fichier à générer", value="config.yaml")
        overwrite_config = st.checkbox("Écraser le fichier de configuration s'il existe", value=False)

        submitted = st.form_submit_button("Générer la configuration")

    if not submitted:
        return

    errors: List[str] = []
    playlist_urls = parse_lines(playlists_raw) if use_playlists else []

    if not channel_url.strip() and not playlist_urls:
        errors.append("Il faut fournir au moins une chaîne ou une playlist.")
    if channel_url.strip() and not validate_youtube_url(channel_url):
        errors.append("L'URL de chaîne ne ressemble pas à une URL YouTube valide.")
    for url in playlist_urls:
        if not validate_youtube_url(url):
            errors.append(f"Playlist invalide : {url}")
    if not manual_subs and not auto_subs:
        errors.append("Il faut sélectionner les sous-titres manuels, automatiques, ou les deux.")
    if limit_mode == "Illimité" and not confirm_unlimited:
        errors.append("La configuration illimitée nécessite une confirmation explicite.")

    try:
        target_path = safe_project_path(target_path_raw, must_be_yaml=True)
    except ValueError as exc:
        errors.append(str(exc))
        target_path = None  # type: ignore[assignment]

    try:
        safe_project_path(output_dir)
    except ValueError as exc:
        errors.append(f"Dossier de sortie invalide : {exc}")

    if target_path and target_path.exists() and not overwrite_config:
        errors.append(f"Le fichier existe déjà : {target_path.relative_to(ROOT)}. Coche l'option d'écrasement.")

    if errors:
        for error in errors:
            st.error(error)
        return

    limit: Optional[int]
    if limit_mode.startswith("Test rapide"):
        limit = 3
    elif limit_mode.startswith("Test élargi"):
        limit = 10
    else:
        limit = None

    config = build_config(
        source_name=source_name,
        channel_url=channel_url,
        channel_tabs=channel_tabs,
        playlist_urls=playlist_urls,
        playlist_prefix=playlist_prefix,
        subtitle_languages=parse_languages(subtitle_languages_raw),
        include_language_variants=include_language_variants,
        manual_subs=manual_subs,
        auto_subs=auto_subs,
        subtitle_format=subtitle_format,
        output_dir=output_dir,
        save_metadata=save_metadata,
        overwrite=overwrite,
        limit=limit,
        use_cookies=use_cookies,
        cookies_from_browser=cookies_from_browser,
        extra_args=parse_lines(extra_args_raw.replace(" ", "\n")),
    )

    assert target_path is not None
    target_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    st.success(f"Configuration écrite : {target_path.relative_to(ROOT)}")
    st.code(target_path.read_text(encoding="utf-8"), language="yaml")


def render_runner() -> None:
    st.header("Appliquer une configuration")

    config_files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("*.y*ml"))
    default_index = config_files.index("config.yaml") if "config.yaml" in config_files else 0 if config_files else None
    selected = st.selectbox("Fichier de configuration", config_files or ["config.yaml"], index=default_index or 0)
    custom_path = st.text_input("Ou chemin manuel", value=selected)

    try:
        config_path = safe_project_path(custom_path, must_be_yaml=True)
    except ValueError as exc:
        st.error(str(exc))
        return

    if not config_path.exists():
        st.warning("Le fichier n'existe pas encore.")
        return

    try:
        config = load_config(config_path)
    except Exception as exc:  # pragma: no cover - affichage UI
        st.error(f"Impossible de lire la configuration : {exc}")
        return

    sources = config.get("sources") or []
    limit = (config.get("processing") or {}).get("limit")
    output_dir = ((config.get("output") or {}).get("directory")) or "./data"
    use_cookies = bool((config.get("youtube") or {}).get("use_cookies"))

    try:
        safe_project_path(str(output_dir))
    except ValueError as exc:
        st.error(f"Dossier de sortie refusé par l'interface : {exc}")
        return

    st.subheader("Résumé")
    st.write(
        {
            "sources": len(sources),
            "limit": limit,
            "output": output_dir,
            "use_cookies": use_cookies,
        }
    )
    with st.expander("Voir le YAML"):
        st.code(config_path.read_text(encoding="utf-8"), language="yaml")

    if limit is None:
        st.warning("Cette configuration est sans limite : elle peut traiter toute la chaîne ou playlist.")
        confirm_full = st.checkbox("Je confirme vouloir exécuter cette configuration complète.", value=False)
    else:
        confirm_full = True

    col1, col2 = st.columns(2)
    with col1:
        run_listing = st.button("Lister les vidéos uniquement")
    with col2:
        run_download = st.button("Lister puis télécharger les sous-titres", disabled=not confirm_full)

    if run_listing:
        code = run_fetcher(config_path, "list-only")
        if code == 0:
            st.success("Listing terminé.")
        else:
            st.error(f"Listing terminé avec erreur : code {code}")

    if run_download:
        code = run_fetcher(config_path, "full")
        if code == 0:
            st.success("Téléchargement terminé.")
            report_path = first_source_report_path(config)
            if report_path and report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                st.subheader("Rapport")
                st.write(
                    {
                        "videos_total": report.get("videos_total"),
                        "subtitles_found": report.get("subtitles_found"),
                        "without_subtitles": report.get("without_subtitles"),
                        "errors": report.get("errors"),
                    }
                )
                with st.expander("Voir report.json"):
                    st.json(report)
        else:
            st.error(f"Téléchargement terminé avec erreur : code {code}")


def render_safeguards() -> None:
    st.header("Garde-fous intégrés")
    st.markdown(
        """
- Le générateur limite par défaut le traitement à **3 vidéos**.
- Le mode illimité nécessite une confirmation explicite.
- L'interface n'écrit que dans le dossier du repository.
- `config.yaml` et `data/` restent ignorés par Git.
- Les cookies ne sont jamais exportés dans le repo : seule l'option `cookies_from_browser` est écrite.
- L'exécution utilise le CLI existant, ce qui conserve le même comportement en terminal et dans l'interface.
- Les logs sont affichés en temps réel et la progression est calculée à partir des vidéos traitées.
        """
    )


def main() -> None:
    st.set_page_config(page_title="YouTube subtitles fetcher", layout="wide")
    st.title("YouTube subtitles fetcher")
    st.caption("Générer une configuration, puis lister des vidéos et récupérer leurs sous-titres.")

    page = st.sidebar.radio(
        "Action",
        ["Construire une configuration", "Appliquer une configuration", "Garde-fous"],
    )

    if page == "Construire une configuration":
        render_config_builder()
    elif page == "Appliquer une configuration":
        render_runner()
    else:
        render_safeguards()


if __name__ == "__main__":
    main()
