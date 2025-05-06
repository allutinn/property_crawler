from pathlib import Path
from datetime import datetime
import shutil

RAW_DIR = Path("/app/data/raw")  # Adjust if needed
LATEST_PATH = RAW_DIR / "latest.ndjson"

def get_latest_daily_file(raw_dir: Path) -> Path | None:
    # Get all subfolders that match a YYYY-MM-DD date pattern
    candidates = [
        p for p in raw_dir.iterdir()
        if p.is_dir() and p.name[:4].isdigit() and (p / f"{p.name}.ndjson").exists()
    ]
    if not candidates:
        return None

    # Sort folders descending by name (newest date first)
    latest_folder = sorted(candidates, reverse=True)[0]
    return latest_folder / f"{latest_folder.name}.ndjson"

def update_latest():
    latest_file = get_latest_daily_file(RAW_DIR)
    if latest_file is None:
        print("❌ No daily NDJSON files found.")
        return

    shutil.copy2(latest_file, LATEST_PATH)
    print(f"✅ Copied {latest_file} → {LATEST_PATH}")

if __name__ == "__main__":
    update_latest()
