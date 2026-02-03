#!/usr/bin/env python3
"""Download SCOOP wave ZIP files and scoopTrackerLatest.dta from GitHub."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API_ROOT = "https://api.github.com/repos/ScottishElectionStudy/Scottish_Opinion_Monitor/contents"
DOWNLOAD_ROOT = "https://github.com/ScottishElectionStudy/Scottish_Opinion_Monitor/raw"


def fetch_json(url: str) -> list[dict]:
    request = Request(url, headers={"Accept": "application/vnd.github+json"})
    with urlopen(request) as response:  # nosec B310 - intended to call GitHub API
        return json.loads(response.read().decode("utf-8"))


def list_repo_files(path: str = "") -> Iterable[dict]:
    url = f"{API_ROOT}/{path}" if path else API_ROOT
    try:
        entries = fetch_json(url)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to list {url}: {exc}") from exc

    for entry in entries:
        if entry.get("type") == "dir":
            yield from list_repo_files(entry.get("path", ""))
        elif entry.get("type") == "file":
            yield entry


def is_target_file(name: str) -> bool:
    lower = name.lower()
    if lower == "scooptrackerlatest.dta":
        return True
    return lower.endswith(".zip") and "scoop" in lower


def download_file(url: str, destination: Path) -> None:
    request = Request(url)
    with urlopen(request) as response:  # nosec B310 - intended to call GitHub
        destination.write_bytes(response.read())


def build_manifest_entry(
    destination: Path,
    url: str,
    size: int | None,
    downloaded_at: dt.datetime,
) -> dict:
    return {
        "filename": destination.name,
        "url": url,
        "size": size,
        "downloaded_at": downloaded_at.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download SCOOP wave ZIP files and scoopTrackerLatest.dta "
            "from the Scottish_Opinion_Monitor GitHub repository."
        )
    )
    parser.add_argument("--out", default="data/raw/scoop", help="Output directory")
    parser.add_argument("--force", action="store_true", help="Redownload files")
    args = parser.parse_args()

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict] = []

    for entry in list_repo_files():
        name = entry.get("name", "")
        if not is_target_file(name):
            continue
        path = entry.get("path")
        if not path:
            continue
        download_url = f"{DOWNLOAD_ROOT}/{path}"
        destination = output_dir / name
        file_exists = destination.exists()
        downloaded_at: dt.datetime

        if file_exists and not args.force:
            downloaded_at = dt.datetime.fromtimestamp(
                destination.stat().st_mtime,
                tz=dt.timezone.utc,
            )
        else:
            download_file(download_url, destination)
            downloaded_at = dt.datetime.now(dt.timezone.utc)

        manifest_entries.append(
            build_manifest_entry(
                destination=destination,
                url=download_url,
                size=entry.get("size"),
                downloaded_at=downloaded_at,
            )
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(sorted(manifest_entries, key=lambda item: item["filename"]), indent=2)
        + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
