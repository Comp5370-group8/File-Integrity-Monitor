import hashlib
import json

import pytest
from watchdog.events import (FileCreatedEvent, FileDeletedEvent,
                             FileModifiedEvent, FileMovedEvent)

from realtime_monitor import FileMonitor


@pytest.fixture
def folder(tmp_path, monkeypatch):
    # Alerts are written to activity_log.txt in the current directory
    monkeypatch.chdir(tmp_path)
    watched = tmp_path / "watched"
    watched.mkdir()
    return watched


@pytest.fixture
def baseline(tmp_path):
    return str(tmp_path / "baseline.json")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def read_saved(baseline):
    with open(baseline) as file:
        return json.load(file)


def alerts(capsys):
    return [line for line in capsys.readouterr().out.splitlines()
            if line.startswith("[ALERT]")]


# Startup and saved baseline

def test_first_run_creates_baseline(folder, baseline, capsys):
    (folder / "a.txt").write_text("A")

    FileMonitor(str(folder), baseline)

    assert read_saved(baseline) == {"a.txt": sha("A")}
    assert "No saved baseline found" in capsys.readouterr().out


def test_detects_changes_made_while_not_running(folder, baseline, capsys):
    (folder / "config.txt").write_text("safe")
    (folder / "old.txt").write_text("bye")
    FileMonitor(str(folder), baseline)
    capsys.readouterr()

    # Monitor is "stopped" while these happen
    (folder / "config.txt").write_text("tampered")
    (folder / "old.txt").unlink()
    (folder / "dropped.txt").write_text("new")

    FileMonitor(str(folder), baseline)

    out = " ".join(alerts(capsys))
    assert "config.txt was MODIFIED" in out
    assert "old.txt was DELETED" in out
    assert "dropped.txt was ADDED" in out


def test_restart_without_changes_reports_nothing(folder, baseline, capsys):
    (folder / "a.txt").write_text("A")
    FileMonitor(str(folder), baseline)
    capsys.readouterr()

    FileMonitor(str(folder), baseline)

    out = capsys.readouterr().out
    assert "No changes found." in out
    assert "[ALERT]" not in out


def test_offline_changes_are_only_reported_once(folder, baseline, capsys):
    (folder / "a.txt").write_text("A")
    FileMonitor(str(folder), baseline)
    (folder / "a.txt").write_text("changed")

    FileMonitor(str(folder), baseline)
    capsys.readouterr()
    FileMonitor(str(folder), baseline)

    assert alerts(capsys) == []


def test_corrupt_baseline_is_replaced(folder, baseline, capsys):
    (folder / "a.txt").write_text("A")
    with open(baseline, "w") as file:
        file.write("not json")

    FileMonitor(str(folder), baseline)

    assert "[WARNING]" in capsys.readouterr().out
    assert read_saved(baseline) == {"a.txt": sha("A")}


# Real-time events

def test_created_file_is_alerted_and_saved(folder, baseline, capsys):
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()
    path = folder / "new.txt"
    path.write_text("hi")

    monitor.on_created(FileCreatedEvent(str(path)))

    assert len(alerts(capsys)) == 1
    assert read_saved(baseline) == {"new.txt": sha("hi")}


def test_modified_file_is_alerted_and_saved(folder, baseline, capsys):
    path = folder / "a.txt"
    path.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    path.write_text("changed")
    monitor.on_modified(FileModifiedEvent(str(path)))

    assert "a.txt was MODIFIED" in alerts(capsys)[0]
    assert read_saved(baseline) == {"a.txt": sha("changed")}


def test_modified_event_without_content_change_is_ignored(folder, baseline, capsys):
    path = folder / "a.txt"
    path.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    monitor.on_modified(FileModifiedEvent(str(path)))

    assert alerts(capsys) == []


def test_deleted_file_is_alerted_and_removed(folder, baseline, capsys):
    path = folder / "a.txt"
    path.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    path.unlink()
    monitor.on_deleted(FileDeletedEvent(str(path)))

    assert "a.txt was DELETED" in alerts(capsys)[0]
    assert read_saved(baseline) == {}


def test_atomic_save_is_reported_as_modified(folder, baseline, capsys):
    # Editors often write a temp file, then rename it over the original
    target = folder / "notes.txt"
    target.write_text("original")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    temp = folder / ".notes.txt.swp"
    temp.write_text("edited")
    temp.replace(target)
    monitor.on_moved(FileMovedEvent(str(temp), str(target)))

    out = alerts(capsys)
    assert len(out) == 1
    assert "notes.txt was MODIFIED" in out[0]
    assert read_saved(baseline) == {"notes.txt": sha("edited")}


def test_atomic_save_with_macos_event_sequence(folder, baseline, capsys):
    # Event sequence observed from watchdog's FSEvents backend on macOS
    target = folder / "notes.txt"
    target.write_text("original")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    temp = folder / ".notes.swp"
    temp.write_text("edited")
    monitor.on_created(FileCreatedEvent(str(temp)))
    monitor.on_modified(FileModifiedEvent(str(temp)))
    temp.replace(target)
    monitor.on_moved(FileMovedEvent(str(temp), str(target)))
    monitor.on_created(FileCreatedEvent(str(target)))
    monitor.on_modified(FileModifiedEvent(str(target)))
    monitor.on_deleted(FileDeletedEvent(str(target)))

    out = alerts(capsys)
    assert len(out) == 1
    assert "notes.txt was MODIFIED" in out[0]
    assert read_saved(baseline) == {"notes.txt": sha("edited")}


def test_created_event_for_known_file_with_same_content_is_ignored(folder, baseline, capsys):
    path = folder / "a.txt"
    path.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    monitor.on_created(FileCreatedEvent(str(path)))

    assert alerts(capsys) == []


def test_rename_is_deletion_plus_creation(folder, baseline, capsys):
    old = folder / "old.txt"
    old.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    new = folder / "new.txt"
    old.rename(new)
    monitor.on_moved(FileMovedEvent(str(old), str(new)))

    out = alerts(capsys)
    assert "old.txt was DELETED" in out[0]
    assert "new.txt was CREATED" in out[1]
    assert read_saved(baseline) == {"new.txt": sha("A")}


def test_move_out_of_folder_is_only_a_deletion(folder, baseline, tmp_path, capsys):
    path = folder / "a.txt"
    path.write_text("A")
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()

    outside = tmp_path / "a.txt"
    path.rename(outside)
    monitor.on_moved(FileMovedEvent(str(path), str(outside)))

    out = alerts(capsys)
    assert len(out) == 1
    assert "a.txt was DELETED" in out[0]


def test_hidden_files_are_ignored(folder, baseline, capsys):
    monitor = FileMonitor(str(folder), baseline)
    capsys.readouterr()
    path = folder / ".DS_Store"
    path.write_text("x")

    monitor.on_created(FileCreatedEvent(str(path)))

    assert alerts(capsys) == []
    assert read_saved(baseline) == {}
