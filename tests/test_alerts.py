import hashlib

import pytest

from alerts import calculate_hash, check_integrity, get_folder_state, send_alert


@pytest.fixture(autouse=True)
def run_in_tmp(tmp_path, monkeypatch):
    # send_alert writes activity_log.txt to the current directory
    monkeypatch.chdir(tmp_path)


def read_log():
    with open("activity_log.txt") as log:
        return log.read()


# calculate_hash

def test_hash_matches_known_sha256(tmp_path):
    path = tmp_path / "hello.txt"
    path.write_bytes(b"hello")

    assert calculate_hash(path) == hashlib.sha256(b"hello").hexdigest()


def test_hash_of_empty_file(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    assert calculate_hash(path) == hashlib.sha256(b"").hexdigest()


def test_hash_of_file_larger_than_one_chunk(tmp_path):
    data = b"abc123" * 5000  # 30,000 bytes, several 4096-byte chunks
    path = tmp_path / "big.bin"
    path.write_bytes(data)

    assert calculate_hash(path) == hashlib.sha256(data).hexdigest()


def test_hash_changes_when_content_changes(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("original")
    before = calculate_hash(path)

    path.write_text("tampered")

    assert calculate_hash(path) != before


# get_folder_state

def test_folder_state_hashes_regular_files(tmp_path):
    folder = tmp_path / "watched"
    folder.mkdir()
    (folder / "a.txt").write_text("A")
    (folder / "b.txt").write_text("B")

    state = get_folder_state(folder)

    assert state == {
        "a.txt": hashlib.sha256(b"A").hexdigest(),
        "b.txt": hashlib.sha256(b"B").hexdigest(),
    }


def test_folder_state_skips_hidden_files_and_directories(tmp_path):
    folder = tmp_path / "watched"
    folder.mkdir()
    (folder / "visible.txt").write_text("x")
    (folder / ".DS_Store").write_text("x")
    (folder / "subdir").mkdir()

    assert list(get_folder_state(folder)) == ["visible.txt"]


def test_folder_state_of_empty_folder(tmp_path):
    folder = tmp_path / "watched"
    folder.mkdir()

    assert get_folder_state(folder) == {}


# check_integrity

def test_no_changes_returns_false_and_logs_nothing(tmp_path, capsys):
    state = {"a.txt": "hash1"}

    assert check_integrity(state, dict(state)) is False
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "activity_log.txt").exists()


def test_detects_added_file(capsys):
    assert check_integrity({}, {"new.txt": "hash"}) is True
    assert "new.txt was ADDED" in capsys.readouterr().out


def test_detects_deleted_file(capsys):
    assert check_integrity({"gone.txt": "hash"}, {}) is True
    assert "gone.txt was DELETED" in capsys.readouterr().out


def test_detects_modified_file(capsys):
    assert check_integrity({"f.txt": "old"}, {"f.txt": "new"}) is True
    assert "f.txt was MODIFIED" in capsys.readouterr().out


def test_detects_multiple_changes_at_once(capsys):
    original = {"keep.txt": "1", "edit.txt": "2", "remove.txt": "3"}
    current = {"keep.txt": "1", "edit.txt": "changed", "add.txt": "4"}

    assert check_integrity(original, current) is True

    out = capsys.readouterr().out
    assert "add.txt was ADDED" in out
    assert "remove.txt was DELETED" in out
    assert "edit.txt was MODIFIED" in out
    assert "keep.txt" not in out


def test_end_to_end_with_real_files(tmp_path, capsys):
    folder = tmp_path / "watched"
    folder.mkdir()
    (folder / "config.txt").write_text("safe")
    (folder / "old.txt").write_text("bye")
    baseline = get_folder_state(folder)

    (folder / "config.txt").write_text("tampered")
    (folder / "old.txt").unlink()
    (folder / "dropped.txt").write_text("new")

    assert check_integrity(baseline, get_folder_state(folder)) is True
    out = capsys.readouterr().out
    assert "config.txt was MODIFIED" in out
    assert "old.txt was DELETED" in out
    assert "dropped.txt was ADDED" in out


# send_alert

def test_send_alert_prints_and_appends_to_log(capsys):
    send_alert("a.txt", "MODIFIED")
    send_alert("b.txt", "DELETED")

    out = capsys.readouterr().out
    assert out.startswith("[ALERT] a.txt was MODIFIED at ")

    lines = read_log().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("[ALERT] a.txt was MODIFIED at ")
    assert lines[1].startswith("[ALERT] b.txt was DELETED at ")


def test_send_alert_includes_timestamp():
    send_alert("a.txt", "ADDED")

    # Format: YYYY-MM-DD HH:MM:SS
    timestamp = read_log().strip().rsplit(" at ", 1)[1]
    assert len(timestamp) == 19
    assert timestamp[4] == "-" and timestamp[13] == ":"
