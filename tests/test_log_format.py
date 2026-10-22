# The alert format written by alerts.py must stay readable by log_analysis.py
from pathlib import Path

import pytest

from alerts import send_alert
from log_analysis import EVENT_PATTERN, analyze_log


@pytest.fixture(autouse=True)
def run_in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("change_type",
                         ["CREATED", "ADDED", "MODIFIED", "DELETED"])
def test_every_alert_type_matches_analyzer_pattern(change_type):
    send_alert("report final.txt", change_type)

    line = Path("activity_log.txt").read_text().strip()
    match = EVENT_PATTERN.fullmatch(line)

    assert match is not None
    assert match.groups() == ("report final.txt", change_type)


def test_analyzer_counts_alerts_from_monitor(capsys):
    send_alert("a.txt", "CREATED")
    send_alert("a.txt", "MODIFIED")
    send_alert("b.txt", "ADDED")
    send_alert("a.txt", "DELETED")
    capsys.readouterr()

    analyze_log(Path("activity_log.txt").resolve())

    out = capsys.readouterr().out
    assert "Created/Added: 2" in out
    assert "Modified:      1" in out
    assert "Deleted:       1" in out
    assert "Total events:  4" in out
    assert "unrecognized" not in out
