
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from alerts import get_folder_state, calculate_hash, send_alert
import time
import os

TEST_FOLDER = "test"


def log_event(filename, event_type):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"[EVENT] {filename} was {event_type} at {current_time}"

    print(message)

    with open("activity_log.txt", "a") as log:
        log.write(message + "\n")


class FileMonitor(FileSystemEventHandler):

    def __init__(self):
        super().__init__()
        self.previous_state = get_folder_state(TEST_FOLDER)

    def on_created(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if filename.startswith("."):
            return

        # Record creation even if the file disappears quickly
        log_event(filename, "CREATED")

        # Store the hash if the file still exists
        self.update_file(filename, event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if filename.startswith("."):
            return

        if not os.path.isfile(event.src_path):
            return

        try:
            current_hash = calculate_hash(event.src_path)
        except (OSError, IOError):
            return

        previous_hash = self.previous_state.get(filename)

        if previous_hash is None:
            # File was not previously recorded
            self.previous_state[filename] = current_hash
            return

        if previous_hash != current_hash:
            send_alert(filename, "MODIFIED")
            self.previous_state[filename] = current_hash

    def on_deleted(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if filename.startswith("."):
            return

        log_event(filename, "DELETED")

        # Remove deleted file from stored state
        self.previous_state.pop(filename, None)

    def on_moved(self, event):
        if event.is_directory:
            return

        # Treat renaming as deletion + creation
        self.on_deleted(event)

        if hasattr(event, "dest_path"):
            class NewEvent:
                is_directory = False
                src_path = event.dest_path

            self.on_created(NewEvent())

    def update_file(self, filename, filepath):
        if not os.path.isfile(filepath):
            return

        try:
            self.previous_state[filename] = calculate_hash(filepath)
        except (OSError, IOError):
            pass


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

