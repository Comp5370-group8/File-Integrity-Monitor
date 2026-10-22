
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from alerts import (BASELINE_FILE, TEST_FOLDER, calculate_hash, check_integrity,
                    get_folder_state, load_baseline, save_baseline, send_alert)
import time
import os


class FileMonitor(FileSystemEventHandler):

    def __init__(self, folder=TEST_FOLDER, baseline_file=BASELINE_FILE):
        super().__init__()
        self.folder = folder
        self.baseline_file = baseline_file

        current_state = get_folder_state(folder)
        saved_state = load_baseline(baseline_file)

        if saved_state is None:
            print("No saved baseline found. Creating a new one.")
        else:
            # Report anything that changed while the monitor was not running
            print("Checking for changes since the last run...")
            if not check_integrity(saved_state, current_state):
                print("No changes found.")

        # Start monitoring from the current state of the folder
        self.previous_state = current_state
        self.save()

    def on_created(self, event):
        if event.is_directory:
            return

        self.handle_created(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if filename.startswith("."):
            return

        current_hash = self.hash_file(event.src_path)

        if current_hash is None:
            return

        previous_hash = self.previous_state.get(filename)

        if previous_hash is not None and previous_hash != current_hash:
            send_alert(filename, "MODIFIED")

        if previous_hash != current_hash:
            self.previous_state[filename] = current_hash
            self.save()

    def on_deleted(self, event):
        if event.is_directory:
            return

        self.handle_deleted(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        # Treat renaming as deletion + creation
        self.handle_deleted(event.src_path)

        # Ignore files moved out of the monitored folder
        if self.in_folder(event.dest_path):
            self.handle_created(event.dest_path)

    def handle_created(self, filepath):
        filename = os.path.basename(filepath)

        if filename.startswith("."):
            return

        new_hash = self.hash_file(filepath)
        previous_hash = self.previous_state.get(filename)

        if previous_hash is None:
            # Record creation even if the file disappears quickly
            send_alert(filename, "CREATED")
        elif new_hash is not None and new_hash != previous_hash:
            # Many editors save by replacing the file, which shows up
            # as a new file with the same name but different contents
            send_alert(filename, "MODIFIED")

        # Store the hash if the file still exists
        if new_hash is not None and new_hash != previous_hash:
            self.previous_state[filename] = new_hash
            self.save()

    def handle_deleted(self, filepath):
        filename = os.path.basename(filepath)

        if filename.startswith("."):
            return

        # macOS can report a deletion for a file that was replaced
        # (e.g. by an editor's atomic save) but still exists
        if os.path.exists(filepath):
            return

        send_alert(filename, "DELETED")

        # Remove deleted file from stored state
        if self.previous_state.pop(filename, None) is not None:
            self.save()

    def hash_file(self, filepath):
        # Returns None if the file is gone or cannot be read
        if not os.path.isfile(filepath):
            return None

        try:
            return calculate_hash(filepath)
        except (OSError, IOError):
            return None

    def in_folder(self, filepath):
        folder = os.path.realpath(self.folder)
        return os.path.dirname(os.path.realpath(filepath)) == folder

    def save(self):
        save_baseline(self.previous_state, self.baseline_file)


if __name__ == "__main__":
    print("Real-time File Integrity Monitor")
    print("--------------------------------")

    monitor = FileMonitor()

    print("Monitoring files:",
          list(monitor.previous_state.keys()))

    observer = Observer()
    observer.schedule(monitor, TEST_FOLDER, recursive=False)
    observer.start()

    print("Real-time monitoring started.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
