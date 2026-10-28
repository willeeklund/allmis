import datetime as dt
import json
from pathlib import Path

import pytest

from allmis.fetch import FetchError, build_payload, find_schedule_links, write_json
from allmis.parser import parse_workbook

FIXTURES = Path(__file__).parent / "fixtures"


def test_finds_xlsx_links_in_ice_schedule_folder():
    page = (FIXTURES / "dokument.html").read_text(encoding="utf-8")
    links = find_schedule_links(page)
    assert [link.name for link in links] == ["Vecka 44.xlsx", "Vecka 45.xlsx", "Vecka 46.xlsx"]
    assert links[0].url == "https://www.ikgota.se/dokument/acbe7d27-56f7-44d8-a501-7f443a139724"


def test_folder_found_by_title_when_id_changes():
    page = (FIXTURES / "dokument.html").read_text(encoding="utf-8").replace("73449", "99999")
    assert len(find_schedule_links(page)) == 3


def test_missing_folder_fails():
    with pytest.raises(FetchError):
        find_schedule_links("<html><body>Inga dokument</body></html>")


def test_payload_merges_files(tmp_path):
    today = dt.date(2026, 10, 28)
    schedules = [
        parse_workbook(FIXTURES / "Vecka 44.xlsx", today=today),
        parse_workbook(FIXTURES / "Vecka 45.xlsx", today=today),
        parse_workbook(FIXTURES / "Vecka 45.xlsx", today=today),
    ]
    now = dt.datetime(2026, 10, 28, 5, 0)
    payload = build_payload(schedules, now)
    assert payload["coverage"] == {"from": "2026-10-26", "to": "2026-11-08"}
    assert len(payload["sessions"]) == len(schedules[0].sessions) + len(schedules[1].sessions)

    out = tmp_path / "docs" / "allmis.json"
    write_json(payload, out)
    assert json.loads(out.read_text(encoding="utf-8")) == payload
