#!/usr/bin/env python3
"""Récupère les URLs de vidéos YouTube et leurs sous-titres via yt-dlp.

Usage:
    python3 scripts/fetch_youtube_subtitles.py --config config.yaml
    python3 scripts/fetch_youtube_subtitles.py --config config.yaml --list-only
    python3 scripts/fetch_youtube_subtitles.py --config config.yaml --subtitles-only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


YOUTUBE_WATCH = "https://www.youtube.com/watch?v="


@dataclass
class Video:
    id: str
    url: str
    title: str = ""
    source: str = ""
    raw: Optional[Dict[str, Any]] = None


def die(message: str, code: int = 1) -> None:
    print(f"Erreur: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        die(f"fichier de configuration introuvable: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            die("PyYAML n'est pas installé. Lance: python3 -m pip install -r requirements.txt")
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_yt_dlp(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        die(f"{binary!r} introuvable. Installe yt-dlp, par ex.: brew install yt-dlp")
    return found


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "source"


def yt_auth_args(config: Dict[str, Any]) -> List[str]:
    youtube = config.get("youtube", {}) or {}
    args: List[str] = []
    cookies_file = youtube.get("cookies_file")
    if cookies_file:
        args += ["--cookies", str(cookies_file)]
    elif youtube.get("use_cookies"):
        browser = youtube.get("cookies_from_browser") or "chrome"
        args += ["--cookies-from-browser", str(browser)]
    return args


def yt_extra_args(config: Dict[str, Any]) -> List[str]:
    extra = ((config.get("yt_dlp", {}) or {}).get("extra_args") or [])
    if not isinstance(extra, list):
        die("yt_dlp.extra_args doit être une liste")
    return [str(x) for x in extra]


def run_command(args: Sequence[str], *, quiet: bool = False) -> subprocess.CompletedProcess:
    if not quiet:
        print("$ " + " ".join(shell_quote(x) for x in args))
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def source_targets(source: Dict[str, Any]) -> List[str]:
    source_type = source.get("type", "url")
    url = source.get("url")

    if source_type == "urls_file":
        path = Path(source.get("path", ""))
        if not path.exists():
            die(f"fichier URLs introuvable pour la source {source.get('name')}: {path}")
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

    if not url:
        die(f"source sans url: {source}")

    if source_type == "channel":
        tabs = source.get("tabs") or ["videos"]
        base = str(url).rstrip("/")
        return [f"{base}/{tab}" for tab in tabs]

    if source_type in {"playlist", "url", "video"}:
        return [str(url)]

    die(f"type de source non supporté: {source_type}")
    return []


def normalize_video(entry: Dict[str, Any], source_name: str) -> Optional[Video]:
    video_id = entry.get("id")
    if not video_id:
        url = entry.get("url") or entry.get("webpage_url")
        if isinstance(url, str):
            match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
            if match:
                video_id = match.group(1)
    if not video_id:
        return None

    webpage_url = entry.get("webpage_url") or entry.get("webpage_url_basename")
    if not isinstance(webpage_url, str) or not webpage_url.startswith("http"):
        webpage_url = YOUTUBE_WATCH + str(video_id)

    return Video(
        id=str(video_id),
        url=webpage_url,
        title=str(entry.get("title") or ""),
        source=source_name,
        raw=entry,
    )


def list_videos(config: Dict[str, Any], source: Dict[str, Any], yt_dlp: str) -> List[Video]:
    source_name = source.get("name") or slugify(source.get("url") or source.get("path") or "source")
    videos: Dict[str, Video] = {}

    for target in source_targets(source):
        print(f"\n[listing] {source_name}: {target}")
        args = [
            yt_dlp,
            "--ignore-errors",
            "--no-warnings",
            "--flat-playlist",
            "--dump-json",
            *yt_auth_args(config),
            *yt_extra_args(config),
            target,
        ]
        proc = run_command(args, quiet=True)
        if proc.returncode != 0:
            print(proc.stderr.strip(), file=sys.stderr)
            print(f"Attention: échec du listing pour {target}", file=sys.stderr)
            continue

        count = 0
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            video = normalize_video(entry, str(source_name))
            if video:
                videos.setdefault(video.id, video)
                count += 1
        print(f"  {count} entrée(s), {len(videos)} vidéo(s) unique(s) cumulée(s)")

    return list(videos.values())


def write_listing_files(base_dir: Path, videos: List[Video], save_urls: bool, save_jsonl: bool) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    if save_urls:
        (base_dir / "video_urls.txt").write_text("\n".join(v.url for v in videos) + ("\n" if videos else ""), encoding="utf-8")
    if save_jsonl:
        with (base_dir / "videos.jsonl").open("w", encoding="utf-8") as f:
            for v in videos:
                payload = {
                    "id": v.id,
                    "url": v.url,
                    "title": v.title,
                    "source": v.source,
                    "raw": v.raw,
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_existing_listing(base_dir: Path) -> List[Video]:
    jsonl = base_dir / "videos.jsonl"
    urls = base_dir / "video_urls.txt"
    videos: List[Video] = []

    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            videos.append(Video(id=item["id"], url=item["url"], title=item.get("title", ""), source=item.get("source", ""), raw=item.get("raw")))
        return videos

    if urls.exists():
        for url in urls.read_text(encoding="utf-8").splitlines():
            match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
            if match:
                videos.append(Video(id=match.group(1), url=url))
    return videos


def subtitle_langs(config: Dict[str, Any]) -> str:
    subtitles = config.get("subtitles", {}) or {}
    langs = subtitles.get("languages") or ["en"]
    include_variants = subtitles.get("include_language_variants", True)
    expanded: List[str] = []
    for lang in langs:
        lang = str(lang)
        expanded.append(lang)
        if include_variants and ".*" not in lang and "-" not in lang:
            expanded.append(f"{lang}.*")
    # Déduplique en conservant l'ordre.
    return ",".join(dict.fromkeys(expanded))


def download_subtitles(config: Dict[str, Any], base_dir: Path, videos: List[Video], yt_dlp: str) -> Dict[str, Any]:
    subtitles_cfg = config.get("subtitles", {}) or {}
    output_cfg = config.get("output", {}) or {}
    processing_cfg = config.get("processing", {}) or {}

    limit = processing_cfg.get("limit")
    if limit:
        videos = videos[: int(limit)]

    subtitles_dir = base_dir / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "videos_total": len(videos),
        "subtitles_found": 0,
        "without_subtitles": 0,
        "errors": 0,
        "items": [],
    }

    for index, video in enumerate(videos, start=1):
        video_dir = subtitles_dir / video.id
        before = set(video_dir.glob("*")) if video_dir.exists() else set()
        video_dir.mkdir(parents=True, exist_ok=True)

        args = [yt_dlp, "--ignore-errors", "--skip-download"]
        if subtitles_cfg.get("manual", True):
            args.append("--write-subs")
        if subtitles_cfg.get("auto", True):
            args.append("--write-auto-subs")
        if output_cfg.get("save_metadata", True):
            args.append("--write-info-json")
        if not output_cfg.get("overwrite", False):
            args.append("--no-overwrites")

        args += [
            "--sub-langs",
            subtitle_langs(config),
            "--sub-format",
            str(subtitles_cfg.get("format") or "vtt"),
            "-o",
            str(video_dir / "%(title).200B [%(id)s].%(ext)s"),
            *yt_auth_args(config),
            *yt_extra_args(config),
            video.url,
        ]

        print(f"\n[{index}/{len(videos)}] {video.title or video.id}")
        proc = run_command(args, quiet=False)
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)

        after = set(video_dir.glob("*"))
        subtitle_files = sorted(p for p in after if p.suffix.lower() in {".vtt", ".srt", ".ass", ".ttml", ".srv1", ".srv2", ".srv3"})
        item = {
            "id": video.id,
            "url": video.url,
            "title": video.title,
            "ok": proc.returncode == 0,
            "subtitle_files": [str(p.relative_to(base_dir)) for p in subtitle_files],
            "new_files": [str(p.relative_to(base_dir)) for p in sorted(after - before)],
        }
        report["items"].append(item)

        if proc.returncode != 0:
            report["errors"] += 1
        if subtitle_files:
            report["subtitles_found"] += 1
        else:
            report["without_subtitles"] += 1

    (base_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Récupère les URLs et sous-titres YouTube via yt-dlp")
    parser.add_argument("--config", default="config.yaml", help="chemin du fichier de configuration")
    parser.add_argument("--list-only", action="store_true", help="ne fait que lister les vidéos")
    parser.add_argument("--subtitles-only", action="store_true", help="utilise le listing existant et récupère seulement les sous-titres")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    config = load_config(config_path)
    yt_dlp = ensure_yt_dlp(str((config.get("yt_dlp", {}) or {}).get("binary") or "yt-dlp"))

    output_dir = Path((config.get("output", {}) or {}).get("directory") or "./data")
    sources = config.get("sources") or []
    if not sources:
        die("aucune source définie dans la configuration")

    all_videos: List[Video] = []
    seen: set = set()

    if not args.subtitles_only:
        for source in sources:
            source_name = source.get("name") or slugify(source.get("url") or source.get("path") or "source")
            base_dir = output_dir / slugify(str(source_name))
            videos = list_videos(config, source, yt_dlp)
            for video in videos:
                if video.id not in seen:
                    all_videos.append(video)
                    seen.add(video.id)
            write_listing_files(
                base_dir,
                videos,
                bool((config.get("output", {}) or {}).get("save_video_urls", True)),
                bool((config.get("output", {}) or {}).get("save_listing_jsonl", True)),
            )
            print(f"\nListing écrit dans: {base_dir}")
    else:
        # Mode simple: pour l'instant, on traite la première source configurée.
        source = sources[0]
        source_name = source.get("name") or slugify(source.get("url") or source.get("path") or "source")
        base_dir = output_dir / slugify(str(source_name))
        all_videos = read_existing_listing(base_dir)
        if not all_videos:
            die(f"aucun listing existant trouvé dans {base_dir}")

    if args.list_only:
        print(f"\nTerminé: {len(all_videos)} vidéo(s) listée(s).")
        return 0

    # Téléchargement par source afin de garder des dossiers séparés.
    if args.subtitles_only:
        source = sources[0]
        source_name = source.get("name") or slugify(source.get("url") or source.get("path") or "source")
        base_dir = output_dir / slugify(str(source_name))
        report = download_subtitles(config, base_dir, all_videos, yt_dlp)
        print_summary(report, base_dir)
    else:
        for source in sources:
            source_name = source.get("name") or slugify(source.get("url") or source.get("path") or "source")
            base_dir = output_dir / slugify(str(source_name))
            videos = read_existing_listing(base_dir)
            report = download_subtitles(config, base_dir, videos, yt_dlp)
            print_summary(report, base_dir)

    return 0


def print_summary(report: Dict[str, Any], base_dir: Path) -> None:
    print("\nRésumé")
    print(f"  Dossier: {base_dir}")
    print(f"  Vidéos traitées: {report['videos_total']}")
    print(f"  Avec sous-titres: {report['subtitles_found']}")
    print(f"  Sans sous-titres: {report['without_subtitles']}")
    print(f"  Erreurs: {report['errors']}")
    print(f"  Rapport: {base_dir / 'report.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
