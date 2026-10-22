from collections import Counter
from pathlib import Path
import re

#read shared log format
LOG_FILE = Path(__file__).resolve().parent / "activity_log.txt"

#match entire line
EVENT_PATTERN = re.compile(
   r"^\[(?:EVENT|ALERT)\]\s+(.+?)\s+was\s+"     #filename
   r"(CREATED|ADDED|MODIFIED|DELETED)\s+at\s+"  #event type
   r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$",   #time
   re.IGNORECASE,
   )
   
#show notice if one file has 10 or more recorded events
NOTICE_THRESHOLD = 10

#read event and print summary
def analyze_log(log_file=LOG_FILE):
   counts = Counter()
   files = Counter()
   ignored = 0
   
   if not log_file.is_file():
      print(f"Log file not found: {log_file}")
      print("Run realtime_monitor.py first to generate activity_log.txt")
      return
      
   #open log
   with log_file.open("r", encoding="utf-8", errors="replace") as log:
      for line in log:
         line = line.strip()
         if not line:
            continue #ignore empty line
         #extract filename and event type
         match = EVENT_PATTERN.fullmatch(line)
         if not match: 
            ignored += 1
            continue
         filename, event_type = match.groups()
         event_type = event_type.upper()
         if event_type =="ADDED":
            event_type = "CREATED"
         counts[event_type] += 1
         files[filename] += 1
         
   #display event total
   print("\n" + "=" * 48)
   print("           SECURITY ACTIVITY SUMMARY")
   print("=" * 48)
   print(f"Created/Added: {counts['CREATED']}")
   print(f"Modified:      {counts['MODIFIED']}")
   print(f"Deleted:       {counts['DELETED']}")
   print(f"Total events:  {sum(counts.values())}")
   
   if files:
      #display 5 most recorded events
      print("\n [5 Files with the Most Events]")
      for filename, count in files.most_common(5):
         print(f" {filename}: {count} event(s)")
         
      top_filename, top_count = files.most_common(1)[0]
      if top_count >= NOTICE_THRESHOLD:
         print(f"\n[NOTICE] High event count for: {top_filename} "
               f"({top_count} recorded events)")
   else:
      print("\nNo valid file events found.")
       
   #report any nonempty lines that could not be parsed
   if ignored:
      print(f"\nSkipped {ignored} unrecognized log line(s).")
   print("=" * 48)
   
if __name__ == "__main__":
   analyze_log()