# File Integrity Monitor

COMP 5370 – Computer and Network Security  
Group 8

## Project Description

This project is a Python-based File Integrity Monitor that detects when files are created, modified, or deleted. It uses SHA-256 hashing to identify file modifications and Python's Watchdog library to monitor file changes automatically.

The program displays alerts in the terminal and records detected events in `activity_log.txt`.

## Features

- SHA-256 file hashing
- Real-time file monitoring using Watchdog
- Detection of created, modified, and deleted files
- Timestamped alerts and event logging
- Detection of rapid file creation and deletion

## Requirements

- Python 3
- Watchdog library

Install Watchdog using:

`python3 -m pip install watchdog`

## How to Run

1. Download the Python files from this repository.
2. Place `alerts.py` and `realtime_monitor.py` in the same folder.
3. Create a folder named `test` in that same location.
4. Open Terminal and navigate to the project folder.
5. Run the program:

   `python3 realtime_monitor.py`

6. Add, modify, or delete files inside the `test` folder to test the monitor.
7. Press `Ctrl+C` to stop monitoring.

Detected events will appear in Terminal and be saved to `activity_log.txt`.
