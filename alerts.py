from datetime import datetime
import hashlib
import json
import os

TEST_FOLDER = "test"
LOG_FILE = "activity_log.txt"
BASELINE_FILE = "baseline.json"


# Single place where alerts are written. log_analysis.py parses this
# exact format, so keep the two in sync (see tests/test_log_format.py).
def send_alert(filename, change_type):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"[ALERT] {filename} was {change_type} at {current_time}"

    # Show alert in Terminal
    print(message)

    # Save alert to activity log
    with open(LOG_FILE, "a") as log:
        log.write(message + "\n")


def calculate_hash(filepath):
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as file:
        while chunk := file.read(4096):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_folder_state(folder):
    state = {}

    for filename in os.listdir(folder):

        # Ignore hidden Mac files like .DS_Store
        if filename.startswith("."):
            continue

        filepath = os.path.join(folder, filename)

        # Only monitor regular files
        if os.path.isfile(filepath):
            state[filename] = calculate_hash(filepath)

    return state


def check_integrity(original_state, current_state):
    changes_found = False

    # Check for ADDED files
    for filename in current_state:
        if filename not in original_state:
            send_alert(filename, "ADDED")
            changes_found = True

    # Check for DELETED files
    for filename in original_state:
        if filename not in current_state:
            send_alert(filename, "DELETED")
            changes_found = True

    # Check for MODIFIED files
    for filename in original_state:
        if filename in current_state:
            if original_state[filename] != current_state[filename]:
                send_alert(filename, "MODIFIED")
                changes_found = True

    return changes_found


def save_baseline(state, baseline_file=BASELINE_FILE):
    # Write to a temp file first so a crash never leaves a half-written baseline
    temp_file = baseline_file + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(state, file, indent=2, sort_keys=True)

    os.replace(temp_file, baseline_file)


def load_baseline(baseline_file=BASELINE_FILE):
    # Returns None if there is no usable saved baseline
    if not os.path.isfile(baseline_file):
        return None

    try:
        with open(baseline_file) as file:
            state = json.load(file)
    except (OSError, ValueError):
        print(f"[WARNING] Could not read {baseline_file}; creating a new baseline")
        return None

    if not isinstance(state, dict):
        print(f"[WARNING] {baseline_file} is not a valid baseline; creating a new baseline")
        return None

    return state
