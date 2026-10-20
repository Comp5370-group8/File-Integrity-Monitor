from datetime import datetime
import hashlib
import os

TEST_FOLDER = "test"


def send_alert(filename, change_type):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"[ALERT] {filename} was {change_type} at {current_time}"

    # Show alert in Terminal
    print(message)

    # Save alert to activity log
    with open("activity_log.txt", "a") as log:
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
