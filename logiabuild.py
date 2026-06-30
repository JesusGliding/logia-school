from pathlib import Path
import json
from datetime import datetime, date

SUBJECTS_DIR = Path("subjects")

SUBJECTS = [
    "calculus",
    "chemistry",
    "physics",
    "biology",
    "engineering-math",
    "python",
    "tlcl",
    "cosmology"
]


def extract_date_from_record(filename, subject):
    prefix = subject + "_"

    if filename.startswith(prefix) and filename.endswith(".txt"):
        return filename[len(prefix):-4]

    return None


def read_existing_index(index_path):
    if not index_path.exists():
        return {}

    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_record_file(record_path, media_dir):
    data = {
        "memo": [],
        "progress": None,
        "media": []
    }

    try:
        lines = record_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return data

    current_section = None

    for line in lines:
        trimmed = line.strip()

        if trimmed == "memo:":
            current_section = "memo"
            continue

        if trimmed == "progress:":
            current_section = "progress"
            continue

        if trimmed == "files:":
            current_section = "files"
            continue

        if current_section == "memo":
            if trimmed:
                data["memo"].append(line)

        elif current_section == "progress":
            if trimmed and data["progress"] is None:
                data["progress"] = trimmed

        elif current_section == "files":
            if trimmed:
                parts = line.split("|", 1)

                filename = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else ""

                exists = (media_dir / filename).exists()

                data["media"].append({
                    "file": filename,
                    "title": title,
                    "exists": exists
                })

    return data


def calculate_study_days(first_record, last_record):
    if not first_record or not last_record:
        return 0

    try:
        start = date.fromisoformat(first_record)
        end = date.fromisoformat(last_record)
        return (end - start).days + 1
    except Exception:
        return 0


def print_missing_media_warning(subject, record_file, media_items):
    missing = [item for item in media_items if not item["exists"]]

    if not missing:
        return 0

    print("[WARNING]")
    print(f"  Subject : {subject}")
    print(f"  Record  : {record_file}")
    print("  Missing media:")

    for item in missing:
        print(f"    - {item['file']}")

    print()

    return len(missing)


def build_subject_index(subject):
    subject_dir = SUBJECTS_DIR / subject
    records_dir = subject_dir / "records"
    media_dir = subject_dir / "media"
    index_path = subject_dir / f"{subject}-index.json"

    if not subject_dir.exists():
        print(f"[SKIP] {subject} 폴더 없음")
        return 0

    existing_index = read_existing_index(index_path)

    record_files = []

    media_files = set()

    if media_dir.exists():
        media_files = {
            file.name
            for file in media_dir.iterdir()
            if file.is_file()
        }   

    if records_dir.exists():
        record_files = sorted(records_dir.glob("*.txt"))

    records = []
    record_dates = []
    warning_count = 0

    used_media = set()

    for record_path in record_files:
        record_date = extract_date_from_record(record_path.name, subject)

        if not record_date:
            continue

        parsed = read_record_file(record_path, media_dir)

        record_dates.append(record_date)

        record_data = {
            "date": record_date,
            "file": record_path.name,
            "progress": parsed["progress"],
            "memo": parsed["memo"],
            "media": parsed["media"]
        }

        for media in parsed["media"]:
            used_media.add(media["file"])

        records.append(record_data)

        warning_count += print_missing_media_warning(
            subject,
            record_path.name,
            parsed["media"]
        )

    first_record = record_dates[0] if record_dates else None
    last_record = record_dates[-1] if record_dates else None
    study_days = calculate_study_days(first_record, last_record)

    media_count = sum(len(record["media"]) for record in records)

    unused_media = sorted(media_files - used_media)

    latest_progress = existing_index.get("latestProgress", "0/0")

    if records:
        last_progress = records[-1].get("progress")

        if last_progress:
            latest_progress = last_progress

    index_data = {
        "subject": subject,

        "recordCount": len(records),
        "mediaCount": media_count,

        "firstRecord": first_record,
        "lastRecord": last_record,
        "studyDays": study_days,

        "latestProgress": latest_progress,

        "recordDates": record_dates,
        "records": records,

        "updated": datetime.now().isoformat(timespec="seconds")
    }

    index_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] {subject}")
    print(f"  records : {len(records)}")
    print(f"  media   : {media_count}")
    print(f"  unused  : {len(unused_media)}")
    print(f"  first   : {first_record}")
    print(f"  last    : {last_record}")
    print(f"  days    : {study_days}")
    print(f"  progress: {latest_progress}")
    print(f"  -> {index_path}")
    print()

    if unused_media:
        print()

        print("   Unused Media")

        for filename in unused_media:
            print(f"    - {filename}")

    return warning_count


def main():
    print("===================================")
    print("LOGIA Build v1.0")
    print("===================================")
    print()

    total_warnings = 0

    for subject in SUBJECTS:
        total_warnings += build_subject_index(subject)

    print("===================================")
    print("LOGIA Build Complete")
    print(f"Warnings: {total_warnings}")
    print("===================================")


if __name__ == "__main__":
    main()