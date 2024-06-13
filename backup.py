
import os
import sqlite3
from datetime import datetime

def copy_and_manage_db(source_db, destination_folder, max_versions):
  """
  Copies the source database to a specified destination folder and manages version history.

  Args:
      source_db (str): Path to the source SQLite database.
      destination_folder (str): Path to the destination folder for backups.
      max_versions (int, optional): Maximum number of versions to keep. Defaults to 5.
  """
  # Get current date in YYYY-MM-DD format
  current_date = datetime.now().strftime("%Y-%m-%d")

  # Create versioned filename for the copy
  filename = os.path.basename(source_db)  # Extract filename from source path
  versioned_filename = f"{filename}_{current_date}.db"
  destination_path = os.path.join(destination_folder, versioned_filename)

  # Copy the database
  try:
    with sqlite3.connect(source_db) as conn:
      with sqlite3.connect(destination_path) as copy_conn:
        copy_conn.executescript(conn.iterdump())
    print(f"Database copied to: {destination_path}")
  except sqlite3.Error as e:
    print(f"Error copying database: {e}")
    return

  # Manage version history (keep max_versions)
  filelist = [f for f in os.listdir(destination_folder)
              if f.startswith(filename) and f.endswith(".db")]
  filelist.sort(reverse=True)  # Sort by date (newest first)

  if len(filelist) > max_versions:
    # Delete the oldest version
    oldest_file = filelist.pop()
    os.remove(os.path.join(destination_folder, oldest_file))
    print(f"Deleted oldest version: {oldest_file}")

# Example usage
source_db = "db.sqlite3"
destination_folder = "../../backups"
max_versions = 30
copy_and_manage_db(source_db, destination_folder, max_versions)
