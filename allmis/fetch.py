from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from allmis.parser import ParseError, Schedule, merge_sessions, parse_workbook

BASE_URL = "https://www.ikgota.se"
DOCUMENTS_URL = f"{BASE_URL}/ikgota/dokument"
FOLDER_TITLE = "Istidsschema"
FALLBACK_FOLDER_ID = "73449"
USER_AGENT = "Mozilla/5.0 (compatible; allmis-bot; +https://github.com/)"
TZ = ZoneInfo("Europe/Stockholm")
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "docs" / "allmis.json"


class FetchError(Exception):
    pass


@dataclass(frozen=True)
class ScheduleLink:
    name: str
    url: str


def find_folder_id(page: str) -> str:
    for m in re.finditer(r'data-id="(\d+)"[^>]*>[\s\S]*?<span class="title">([^<]*)</span>', page):
        if html.unescape(m.group(2)).strip().lower() == FOLDER_TITLE.lower():
            return m.group(1)
    if f'folder-{FALLBACK_FOLDER_ID}"' in page:
        return FALLBACK_FOLDER_ID
    raise FetchError(f"Hittar ingen mapp som heter {FOLDER_TITLE!r} på {DOCUMENTS_URL}")


def find_schedule_links(page: str) -> list[ScheduleLink]:
    folder_id = find_folder_id(page)
    pattern = re.compile(
        r'<div class="folder-content[^"]*\bfolder-' + folder_id + r'">\s*'
        r'<div[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"'
    )
    links = []
    for href, title in pattern.findall(page):
        title = html.unescape(title)
        m = re.search(r"''(.+?)''", title)
        name = m.group(1) if m else title
        if name.lower().endswith(".xlsx"):
            links.append(ScheduleLink(name, BASE_URL + href if href.startswith("/") else href))
    if not links:
        raise FetchError(f"Mappen {FOLDER_TITLE!r} innehåller inga .xlsx-filer")
    return links


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except OSError as e:
        raise FetchError(f"Kunde inte hämta {url}: {e}") from e


def build_payload(schedules: list[Schedule], now: dt.datetime) -> dict:
    sessions = merge_sessions([s for sch in schedules for s in sch.sessions])
    return {
        "updated": now.isoformat(timespec="seconds"),
        "source": f"{DOCUMENTS_URL}#folder={FALLBACK_FOLDER_ID}",
        "coverage": {
            "from": min(s.first_day for s in schedules).isoformat(),
            "to": max(s.last_day for s in schedules).isoformat(),
        },
        "sessions": [s.to_dict() for s in sessions],
    }


def write_json(payload: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=".allmis-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, out)


def run(out: Path) -> dict:
    now = dt.datetime.now(TZ)
    page = _get(DOCUMENTS_URL).decode("utf-8", errors="replace")
    links = find_schedule_links(page)

    schedules = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, link in enumerate(links):
            data = _get(link.url)
            if not data.startswith(b"PK"):
                raise FetchError(f"{link.name} ({link.url}) är ingen Excel-fil")
            path = Path(tmp) / f"{i}.xlsx"
            path.write_bytes(data)
            schedules.append(parse_workbook(path, name=link.name, today=now.date()))
            print(f"{link.name}: {len(schedules[-1].sessions)} pass", file=sys.stderr)

    payload = build_payload(schedules, now)
    write_json(payload, out)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Hämtar istidsschemat och skriver allmis.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    try:
        payload = run(args.out)
    except (FetchError, ParseError) as e:
        print(f"FEL: {e}", file=sys.stderr)
        print(f"{args.out} lämnades orörd.", file=sys.stderr)
        return 1
    print(f"Skrev {len(payload['sessions'])} pass till {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
