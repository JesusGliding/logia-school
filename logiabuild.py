from pathlib import Path
import json
import re
import time
from datetime import datetime


SUBJECTS_DIR = Path("subjects")
READING_DIR = Path("reading")

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

READING_CATEGORIES = [
    "science",
    "philosophy",
    "fiction",
    "humanities"
]


# 자동 판별 결과를 특정 과목에서 강제로 덮어쓰고 싶을 때 사용한다.
CHAPTER_FORMAT_OVERRIDES = {
    "biology": "campbell",
    "cosmology": "classic"
}


# ============================================================
# Study Record Index
# ============================================================

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
        "studytime": None,
        "media": []
    }

    try:
        lines = record_path.read_text(
            encoding="utf-8"
        ).splitlines()
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

        if trimmed == "studytime:":
            current_section = "studytime"
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

        elif current_section == "studytime":
            if trimmed and data["studytime"] is None:
                data["studytime"] = trimmed

        elif current_section == "files":
            if trimmed:
                parts = line.split("|", 1)

                filename = parts[0].strip()
                title = (
                    parts[1].strip()
                    if len(parts) > 1
                    else ""
                )

                exists = (media_dir / filename).exists()

                data["media"].append({
                    "file": filename,
                    "title": title,
                    "exists": exists
                })

    return data


def calculate_study_days(records):
    return len({
        record["date"]
        for record in records
        if record.get("progress")
    })


def print_missing_media_warning(
    subject,
    record_file,
    media_items
):
    missing = [
        item
        for item in media_items
        if not item["exists"]
    ]

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


def build_subject_index(subject, build_cache):
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
        record_files = sorted(
            records_dir.glob("*.txt")
        )

    records = []
    record_dates = []
    warning_count = 0
    used_media = set()

    for record_path in record_files:
        record_date = extract_date_from_record(
            record_path.name,
            subject
        )

        if not record_date:
            continue

        parsed = read_record_file(
            record_path,
            media_dir
        )

        record_dates.append(record_date)

        record_data = {
            "date": record_date,
            "file": record_path.name,
            "progress": parsed["progress"],
            "studytime": parsed["studytime"],
            "memo": parsed["memo"],
            "media": parsed["media"]
        }

        for media in parsed["media"]:
            used_media.add(media["file"])

        records.append(record_data)

        warning_count += (
            print_missing_media_warning(
                subject,
                record_path.name,
                parsed["media"]
            )
        )

    first_record = (
        record_dates[0]
        if record_dates
        else None
    )

    last_record = (
        record_dates[-1]
        if record_dates
        else None
    )

    study_days = calculate_study_days(records)

    media_count = sum(
        len(record["media"])
        for record in records
    )

    unused_media = sorted(
        media_files - used_media
    )

    latest_progress = existing_index.get(
        "latestProgress",
        "0/0"
    )

    # 마지막 레코드에 progress가 없더라도,
    # 가장 최근의 progress를 찾아 보존한다.
    for record in reversed(records):
        if record.get("progress"):
            latest_progress = record["progress"]
            break

    index_data = {
        "cacheVersion": build_cache,
        "subject": subject,

        "recordCount": len(records),
        "mediaCount": media_count,

        "firstRecord": first_record,
        "lastRecord": last_record,
        "studyDays": study_days,

        "latestProgress": latest_progress,

        "recordDates": record_dates,
        "records": records,

        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    index_path.write_text(
        json.dumps(
            index_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"[OK] Study Index : {subject}")
    print(f"  records : {len(records)}")
    print(f"  media   : {media_count}")
    print(f"  unused  : {len(unused_media)}")
    print(f"  first   : {first_record}")
    print(f"  last    : {last_record}")
    print(f"  days    : {study_days}")
    print(f"  progress: {latest_progress}")
    print(f"  -> {index_path}")

    if unused_media:
        print()
        print("  Unused Media")

        for filename in unused_media:
            print(f"    - {filename}")

    print()

    return warning_count


# ============================================================
# Chapter Index
# ============================================================

def read_chapter_lines(chapter_path):
    try:
        raw_lines = chapter_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return []

    lines = []

    for raw_line in raw_lines:
        line = raw_line.strip()

        if not line:
            continue

        # 주석 행은 목차 데이터에서 제외한다.
        if line.startswith("#"):
            continue

        lines.append(line)

    return lines


def detect_chapter_format(subject, lines):
    override = CHAPTER_FORMAT_OVERRIDES.get(
        subject
    )

    if override:
        return override

    has_campbell_unit = any(
        re.match(r"^\d+\s*단원(?:\s+.*)?$", line)
        for line in lines
    )

    if has_campbell_unit:
        return "campbell"

    has_classic_heading = any(
        re.match(
            r"^[IVXLCDM]+\s+.+$",
            line,
            re.IGNORECASE
        )
        or re.match(
            r"^제?\s*\d+\s*장\s+.+$",
            line
        )
        for line in lines
    )

    if has_classic_heading:
        return "classic"

    has_section = any(
        re.match(
            r"^\d+(?:\.\d+)+\s+.+$",
            line
        )
        for line in lines
    )

    if has_section:
        return "general"

    return "simple"


def create_group(group_type, number, title):
    return {
        "type": group_type,
        "number": number,
        "title": title
    }


def create_chapter(
    number,
    title,
    group=None
):
    return {
        "number": number,
        "title": title,
        "group": group.copy() if group else None,
        "sections": []
    }


def create_section(number, title):
    return {
        "number": number,
        "title": title
    }


def append_continuation(
    text,
    current_group,
    current_chapter
):
    """
    번호 없이 이어지는 줄은 바로 앞 제목의 연속으로 처리한다.

    우선순위:
      1. 마지막 소단원
      2. 현재 장
      3. 현재 그룹
    """

    if current_chapter:
        sections = current_chapter["sections"]

        if sections:
            sections[-1]["title"] += f" {text}"
        else:
            current_chapter["title"] += f" {text}"

        return True

    if current_group:
        current_group["title"] += f" {text}"
        return True

    return False


def parse_chapter_lines(lines, chapter_format):
    chapters = []
    groups = []
    unparsed_lines = []

    current_group = None
    current_chapter = None

    for line in lines:

        # ----------------------------------------------------
        # Campbell 형식의 단원
        # 예:
        # 1단원 생물학에서 화학의 역할
        # ----------------------------------------------------
        unit_match = re.match(
            r"^(\d+)\s*단원(?:\s+(.+))?$",
            line
        )

        if (
            chapter_format == "campbell"
            and unit_match
        ):
            unit_number = unit_match.group(1)
            unit_title = (
                unit_match.group(2) or ""
            ).strip()

            current_group = create_group(
                "unit",
                unit_number,
                unit_title
            )

            groups.append(current_group)
            current_chapter = None
            continue

        # ----------------------------------------------------
        # Classic 형식의 로마 숫자 부
        # 예:
        # III 시공간과 우주론
        # ----------------------------------------------------
        roman_match = re.match(
            r"^([IVXLCDM]+)\s+(.+)$",
            line,
            re.IGNORECASE
        )

        if (
            chapter_format == "classic"
            and roman_match
        ):
            part_number = roman_match.group(1)
            part_title = roman_match.group(2).strip()

            current_group = create_group(
                "part",
                part_number,
                part_title
            )

            groups.append(current_group)
            current_chapter = None
            continue

        # ----------------------------------------------------
        # Classic 형식의 장
        # 예:
        # 제10장 빅뱅의 재구성
        # 10장 빅뱅의 재구성
        # ----------------------------------------------------
        classic_chapter_match = re.match(
            r"^제?\s*(\d+)\s*장\s+(.+)$",
            line
        )

        if (
            chapter_format == "classic"
            and classic_chapter_match
        ):
            chapter_number = (
                classic_chapter_match.group(1)
            )

            chapter_title = (
                classic_chapter_match
                .group(2)
                .strip()
            )

            current_chapter = create_chapter(
                chapter_number,
                chapter_title,
                current_group
            )

            chapters.append(current_chapter)
            continue

        # ----------------------------------------------------
        # 소단원
        # 예:
        # 1.1 함수의 네 가지 표현 방법
        # 2.3.1 세부 항목
        # ----------------------------------------------------
        section_match = re.match(
            r"^(\d+(?:\.\d+)+)\s+(.+)$",
            line
        )

        if section_match:
            section_number = section_match.group(1)
            section_title = section_match.group(2).strip()

            if current_chapter is None:
                parent_number = section_number.split(".")[0]

                current_chapter = create_chapter(
                    parent_number,
                    "",
                    current_group
                )

                chapters.append(current_chapter)

            current_chapter["sections"].append(
                create_section(
                    section_number,
                    section_title
                )
            )

            continue

        # ----------------------------------------------------
        # 일반 및 Campbell 형식의 장
        # 예:
        # 1 함수와 모델
        # 2 원자와 분자
        # ----------------------------------------------------
        numbered_chapter_match = re.match(
            r"^(\d+)\s+(.+)$",
            line
        )

        if numbered_chapter_match:
            chapter_number = (
                numbered_chapter_match.group(1)
            )

            chapter_title = (
                numbered_chapter_match
                .group(2)
                .strip()
            )

            current_chapter = create_chapter(
                chapter_number,
                chapter_title,
                current_group
            )

            chapters.append(current_chapter)
            continue

        # ----------------------------------------------------
        # 번호 없이 다음 줄로 이어진 제목
        # ----------------------------------------------------
        appended = append_continuation(
            line,
            current_group,
            current_chapter
        )

        if not appended:
            unparsed_lines.append(line)

    return {
        "groups": groups,
        "chapters": chapters,
        "unparsedLines": unparsed_lines
    }


def build_chapter_index(subject, build_cache):
    subject_dir = SUBJECTS_DIR / subject

    chapter_path = (
        subject_dir
        / f"{subject}-chapters.txt"
    )

    chapter_index_path = (
        subject_dir
        / f"{subject}-chapters.json"
    )

    if not subject_dir.exists():
        return 0

    if not chapter_path.exists():
        print(
            f"[SKIP] Chapter Index : "
            f"{subject} 목차 파일 없음"
        )
        print()
        return 0

    lines = read_chapter_lines(chapter_path)

    chapter_format = detect_chapter_format(
        subject,
        lines
    )

    parsed = parse_chapter_lines(
        lines,
        chapter_format
    )

    groups = parsed["groups"]
    chapters = parsed["chapters"]
    unparsed_lines = parsed["unparsedLines"]

    section_count = sum(
        len(chapter["sections"])
        for chapter in chapters
    )

    chapter_index_data = {
        "cacheVersion": build_cache,

        "subject": subject,
        "format": chapter_format,

        "sourceFile": chapter_path.name,

        "groupCount": len(groups),
        "chapterCount": len(chapters),
        "sectionCount": section_count,

        "groups": groups,
        "chapters": chapters,

        "unparsedLines": unparsed_lines,

        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    chapter_index_path.write_text(
        json.dumps(
            chapter_index_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"[OK] Chapter Index : {subject}")
    print(f"  format  : {chapter_format}")
    print(f"  groups  : {len(groups)}")
    print(f"  chapters: {len(chapters)}")
    print(f"  sections: {section_count}")
    print(f"  unparsed: {len(unparsed_lines)}")
    print(f"  -> {chapter_index_path}")
    print()

    if unparsed_lines:
        print("[WARNING]")
        print(f"  Subject : {subject}")
        print("  Unparsed chapter lines:")

        for line in unparsed_lines:
            print(f"    - {line}")

        print()

    return len(unparsed_lines)

# ============================================================
# Reading Index
# ============================================================

READING_SECTION_NAMES = {
    "title",
    "author",
    "date",
    "category",
    "keywords",
    "summary",
    "reflection",
    "files"
}


def create_empty_reading_record():
    return {
        "title": "",
        "author": "",
        "date": "",
        "category": "",
        "keywords": [],
        "summary": [],
        "reflection": [],
        "media": []
    }


def read_reading_record(record_path, media_dir):
    """
    독서 레코드 TXT 파일 하나를 읽는다.

    지원 항목:
      title
      author
      date
      category
      keywords
      summary
      reflection
      files
    """

    data = create_empty_reading_record()

    try:
        lines = record_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return data

    current_section = None

    for line in lines:
        trimmed = line.strip()

        # "title:", "author:" 등의 섹션 시작
        if trimmed.endswith(":"):
            section_name = trimmed[:-1].strip().lower()

            if section_name in READING_SECTION_NAMES:
                current_section = section_name
                continue

        if not trimmed:
            continue

        if current_section == "title":
            if not data["title"]:
                data["title"] = trimmed

        elif current_section == "author":
            if not data["author"]:
                data["author"] = trimmed

        elif current_section == "date":
            if not data["date"]:
                data["date"] = trimmed

        elif current_section == "category":
            if not data["category"]:
                data["category"] = trimmed

        elif current_section == "keywords":
            keywords = [
                keyword.strip()
                for keyword in trimmed.split(",")
                if keyword.strip()
            ]

            data["keywords"].extend(keywords)

        elif current_section == "summary":
            data["summary"].append(line)

        elif current_section == "reflection":
            data["reflection"].append(line)

        elif current_section == "files":
            parts = line.split("|", 1)

            filename = parts[0].strip()

            title = (
                parts[1].strip()
                if len(parts) > 1
                else ""
            )

            if not filename:
                continue

            exists = (media_dir / filename).exists()

            data["media"].append({
                "file": filename,
                "title": title,
                "exists": exists
            })

    # 같은 키워드가 중복 입력되었을 경우 순서를 유지하며 제거
    data["keywords"] = list(
        dict.fromkeys(data["keywords"])
    )

    return data


def parse_reading_date(date_value):
    """
    date 형식:

      2026-06-18/2026-06-24
      2026-07-02/

    반환:

      start_date
      finish_date
      status
    """

    if not date_value:
        return None, None, "unknown"

    parts = date_value.split("/", 1)

    start_date = parts[0].strip() or None

    finish_date = None

    if len(parts) > 1:
        finish_date = parts[1].strip() or None

    status = (
        "completed"
        if finish_date
        else "reading"
    )

    return start_date, finish_date, status


def is_valid_iso_date(date_text):
    if not date_text:
        return True

    try:
        datetime.strptime(
            date_text,
            "%Y-%m-%d"
        )

        return True

    except ValueError:
        return False


def print_reading_media_warning(
    category,
    record_file,
    media_items
):
    missing = [
        item
        for item in media_items
        if not item["exists"]
    ]

    if not missing:
        return 0

    print("[WARNING]")
    print(f"  Reading : {category}")
    print(f"  Record  : {record_file}")
    print("  Missing media:")

    for item in missing:
        print(f"    - {item['file']}")

    print()

    return len(missing)


def print_reading_record_warning(
    category,
    record_file,
    message
):
    print("[WARNING]")
    print(f"  Reading : {category}")
    print(f"  Record  : {record_file}")
    print(f"  Problem : {message}")
    print()

    return 1


def build_reading_index(category, build_cache):
    category_dir = READING_DIR / category
    records_dir = category_dir / "records"
    media_dir = category_dir / "media"

    index_path = (
        category_dir
        / f"{category}-index.json"
    )

    if not category_dir.exists():
        print(
            f"[SKIP] Reading Index : "
            f"{category} 폴더 없음"
        )
        print()

        return 0

    if not records_dir.exists():
        print(
            f"[SKIP] Reading Index : "
            f"{category}/records 폴더 없음"
        )
        print()

        return 0

    record_files = sorted(
        records_dir.glob("*.txt")
    )

    media_files = set()

    if media_dir.exists():
        media_files = {
            file.name
            for file in media_dir.iterdir()
            if file.is_file()
        }

    books = []
    warning_count = 0
    used_media = set()

    for record_path in record_files:
        parsed = read_reading_record(
            record_path,
            media_dir
        )

        start_date, finish_date, status = (
            parse_reading_date(
                parsed["date"]
            )
        )

        # 필수 데이터 검사
        if not parsed["title"]:
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    "title이 비어 있습니다."
                )
            )

        if not parsed["author"]:
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    "author가 비어 있습니다."
                )
            )

        if not start_date:
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    "독서 시작일이 없습니다."
                )
            )

        elif not is_valid_iso_date(start_date):
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    (
                        "시작일 형식이 올바르지 않습니다: "
                        f"{start_date}"
                    )
                )
            )

        if (
            finish_date
            and not is_valid_iso_date(finish_date)
        ):
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    (
                        "완독일 형식이 올바르지 않습니다: "
                        f"{finish_date}"
                    )
                )
            )

        if (
            start_date
            and finish_date
            and is_valid_iso_date(start_date)
            and is_valid_iso_date(finish_date)
            and finish_date < start_date
        ):
            warning_count += (
                print_reading_record_warning(
                    category,
                    record_path.name,
                    "완독일이 시작일보다 빠릅니다."
                )
            )

        for media in parsed["media"]:
            used_media.add(media["file"])

        warning_count += (
            print_reading_media_warning(
                category,
                record_path.name,
                parsed["media"]
            )
        )

        book_data = {
            "id": record_path.stem,

            "file": record_path.name,

            "title": parsed["title"],
            "author": parsed["author"],

            "date": parsed["date"],
            "startDate": start_date,
            "finishDate": finish_date,
            "status": status,

            "category": parsed["category"],
            "keywords": parsed["keywords"],

            "summary": parsed["summary"],
            "reflection": parsed["reflection"],

            "media": parsed["media"]
        }

        books.append(book_data)

    # 최근 시작한 책부터 정렬
    books.sort(
        key=lambda book: (
            book.get("startDate") or "",
            book.get("title") or ""
        ),
        reverse=True
    )

    completed_books = [
        book
        for book in books
        if book["status"] == "completed"
    ]

    reading_books = [
        book
        for book in books
        if book["status"] == "reading"
    ]

    # 완독 목록은 완독일 기준 최신순
    completed_books.sort(
        key=lambda book: (
            book.get("finishDate") or "",
            book.get("title") or ""
        ),
        reverse=True
    )

    # 읽는 중 목록은 시작일 기준 최신순
    reading_books.sort(
        key=lambda book: (
            book.get("startDate") or "",
            book.get("title") or ""
        ),
        reverse=True
    )

    media_count = sum(
        len(book["media"])
        for book in books
    )

    unused_media = sorted(
        media_files - used_media
    )

    start_dates = [
        book["startDate"]
        for book in books
        if book.get("startDate")
    ]

    finish_dates = [
        book["finishDate"]
        for book in completed_books
        if book.get("finishDate")
    ]

    first_started = (
        min(start_dates)
        if start_dates
        else None
    )

    latest_started = (
        max(start_dates)
        if start_dates
        else None
    )

    latest_completed = (
        max(finish_dates)
        if finish_dates
        else None
    )

    authors = sorted({
        book["author"]
        for book in books
        if book.get("author")
    })

    categories = sorted({
        book["category"]
        for book in books
        if book.get("category")
    })

    keywords = sorted({
        keyword
        for book in books
        for keyword in book.get("keywords", [])
    })

    index_data = {
        "cacheVersion": build_cache,

        "readingCategory": category,

        "bookCount": len(books),
        "completedCount": len(completed_books),
        "readingCount": len(reading_books),
        "mediaCount": media_count,

        "firstStarted": first_started,
        "latestStarted": latest_started,
        "latestCompleted": latest_completed,

        "authors": authors,
        "categories": categories,
        "keywords": keywords,

        "books": books,

        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    index_path.write_text(
        json.dumps(
            index_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"[OK] Reading Index : {category}")
    print(f"  books     : {len(books)}")
    print(f"  completed : {len(completed_books)}")
    print(f"  reading   : {len(reading_books)}")
    print(f"  media     : {media_count}")
    print(f"  unused    : {len(unused_media)}")
    print(f"  first     : {first_started}")
    print(f"  latest    : {latest_started}")
    print(f"  completed : {latest_completed}")
    print(f"  -> {index_path}")

    if unused_media:
        print()
        print("  Unused Media")

        for filename in unused_media:
            print(f"    - {filename}")

    print()

    return warning_count

# ============================================================
# Main Build
# ============================================================

def main():
    build_cache = int(time.time())

    print("===================================")
    print("LOGIA Build v1.2")
    print("===================================")
    print()

    total_warnings = 0

    print("-----------------------------------")
    print("Building Study Indexes")
    print("-----------------------------------")
    print()

    for subject in SUBJECTS:
        total_warnings += build_subject_index(
            subject,
            build_cache
        )

    print("-----------------------------------")
    print("Building Chapter Indexes")
    print("-----------------------------------")
    print()

    for subject in SUBJECTS:
        total_warnings += build_chapter_index(
            subject,
            build_cache
        )

    print("-----------------------------------")
    print("Building Reading Indexes")
    print("-----------------------------------")
    print()

    for category in READING_CATEGORIES:
        total_warnings += build_reading_index(
            category,
            build_cache
        )

    print("===================================")
    print("LOGIA Build Complete")
    print()
    print(f"Build Cache : {build_cache}")
    print(f"Warnings    : {total_warnings}")
    print("===================================")


if __name__ == "__main__":
    main()