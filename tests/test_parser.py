import datetime as dt
from pathlib import Path

import openpyxl
import pytest

from allmis.parser import ParseError, Session, merge_sessions, parse_workbook, schedule_start

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = dt.date(2026, 10, 28)


def rows(schedule):
    return [(s.date.isoformat(), s.start, s.end, s.hall, s.note) for s in schedule.sessions]


def test_week_44_autumn_break_and_open_ice():
    sch = parse_workbook(FIXTURES / "Vecka 44.xlsx", today=TODAY)
    assert rows(sch) == [
        ("2026-10-27", "11:00", "14:00", "HCL Arena", ""),
        ("2026-10-29", "11:00", "14:00", "HCL Arena", ""),
        ("2026-10-29", "15:00", "16:00", "HCL Arena", ""),
        ("2026-10-30", "11:00", "14:00", "HCL Arena", ""),
        ("2026-10-30", "15:00", "16:00", "HCL Arena", ""),
        ("2026-10-31", "12:00", "14:00", "HCL Arena", ""),
        ("2026-10-31", "17:30", "20:00", "HCL Arena", ""),
        ("2026-11-01", "12:00", "14:00", "HCL Arena", ""),
    ]
    assert sch.first_day == dt.date(2026, 10, 26)
    assert sch.last_day == dt.date(2026, 11, 1)


def test_week_45_time_in_text_and_notes():
    sch = parse_workbook(FIXTURES / "Vecka 45.xlsx", today=TODAY)
    assert rows(sch)[:4] == [
        ("2026-11-02", "09:30", "14:30", "HCL Arena", "delad is"),
        ("2026-11-02", "15:00", "16:00", "HCL Arena", ""),
        ("2026-11-03", "15:00", "16:00", "HCL Arena", ""),
        ("2026-11-04", "08:00", "14:30", "HCL Arena", "delad is"),
    ]
    assert ("2026-11-06", "08:00", "14:30", "HCL Arena", "med klubba") in rows(sch)
    assert rows(sch)[-2:] == [
        ("2026-11-07", "12:00", "14:00", "HCL Arena", ""),
        ("2026-11-08", "12:00", "14:00", "HCL Arena", ""),
    ]


def test_multi_week_file():
    sch = parse_workbook(FIXTURES / "Vecka 41-43.xlsx", today=TODAY)
    assert sch.first_day == dt.date(2026, 10, 5)
    assert sch.last_day == dt.date(2026, 10, 25)
    dates = {s.date for s in sch.sessions}
    assert dt.date(2026, 10, 24) in dates
    assert dt.date(2026, 10, 25) in dates
    assert len(sch.sessions) == 28


def test_open_ice_back_to_back_is_merged():
    sch = parse_workbook(FIXTURES / "Istider-vecka-16-april-2026.xlsx", today=TODAY)
    assert rows(sch) == [
        (f"2026-04-{d}", "14:00", "16:00", "HCL Arena", "") for d in range(13, 18)
    ]


@pytest.mark.parametrize(
    "name, today, expected",
    [
        ("Vecka 44.xlsx", dt.date(2026, 10, 28), dt.date(2026, 10, 26)),
        ("Vecka 2.xlsx", dt.date(2026, 12, 28), dt.date(2027, 1, 11)),
        ("Vecka 52.xlsx", dt.date(2027, 1, 3), dt.date(2026, 12, 21)),
        ("Istider20Vecka2014-15.xlsx", dt.date(2026, 3, 25), dt.date(2026, 3, 30)),
        ("Istider-vecka-16-april-2026.xlsx", dt.date(2030, 1, 1), dt.date(2026, 4, 13)),
    ],
)
def test_schedule_start(name, today, expected):
    assert schedule_start(name, today) == expected


def test_filename_without_week_fails():
    with pytest.raises(ParseError):
        schedule_start("istider.xlsx", TODAY)


def test_workbook_without_grid_fails(tmp_path):
    wb = openpyxl.Workbook()
    wb.active["A1"] = "Något helt annat"
    path = tmp_path / "Vecka 44.xlsx"
    wb.save(path)
    with pytest.raises(ParseError):
        parse_workbook(path, today=TODAY)


def test_non_excel_file_fails(tmp_path):
    path = tmp_path / "Vecka 44.xlsx"
    path.write_text("<html>Sidan kan inte hittas</html>")
    with pytest.raises(ParseError):
        parse_workbook(path, today=TODAY)


def test_merge_overlapping_and_duplicates():
    d = dt.date(2026, 11, 1)
    merged = merge_sessions([
        Session(d, "12:00", "14:00", "HCL Arena"),
        Session(d, "12:00", "14:00", "HCL Arena"),
        Session(d, "13:30", "15:00", "HCL Arena", "med klubba"),
        Session(d, "12:00", "13:00", "A-Hallen"),
    ])
    assert [(s.start, s.end, s.hall, s.note) for s in merged] == [
        ("12:00", "13:00", "A-Hallen", ""),
        ("12:00", "15:00", "HCL Arena", "med klubba"),
    ]
