from pathlib import Path
import json
import re
import time
from datetime import datetime


SUBJECTS_DIR = Path("subjects")
READING_DIR = Path("reading")
RESOURCES_DIR = Path("resources")

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

HISTORY_CATEGORIES = [
    "science-history",
    "math-history",
    "philosophy-history"
]

HISTORY_TIMELINE_FILES = {
    "science-history": "science_timeline.txt",
    "math-history": "math_timeline.txt",
    "philosophy-history": "philosophy_timeline.txt"
}


# 자동 판별 결과를 특정 과목에서 강제로 덮어쓰고 싶을 때 사용한다.
CHAPTER_FORMAT_OVERRIDES = {
    "biology": "campbell",
    "physics": "physics",
    "cosmology": "classic"
}


# 기존 과목들이 Subject TXT로 전환되는 동안 사용하는 임시 정보다.
# 각 폴더에 <subject>-subject.txt가 생기면 해당 TXT가 이 값을 대체한다.
SUBJECT_FALLBACK_METADATA = {
    "calculus": {
        "title": "미분적분학 I·II",
        "englishTitle": "Calculus I·II",
        "displayOrder": 1
    },
    "chemistry": {
        "title": "일반화학 I",
        "englishTitle": "General Chemistry I",
        "displayOrder": 2
    },
    "physics": {
        "title": "대학물리학",
        "englishTitle": "University Physics",
        "displayOrder": 3
    },
    "biology": {
        "title": "캠벨 생명과학",
        "englishTitle": "Campbell Biology",
        "displayOrder": 4
    },
    "engineering-math": {
        "title": "공업수학",
        "englishTitle": "Engineering Mathematics",
        "displayOrder": 5
    },
    "python": {
        "title": "파이썬",
        "englishTitle": "Python",
        "displayOrder": 6
    },
    "tlcl": {
        "title": "TLCL",
        "englishTitle": "The Linux Command Line",
        "displayOrder": 7
    },
    "cosmology": {
        "title": "우주의 구조",
        "englishTitle": "The Structure of the Universe",
        "displayOrder": 8
    }
}

SUBJECT_CATALOG_PATH = SUBJECTS_DIR / "subjects-index.json"

SUBJECT_FIELD_ALIASES = {
    "id": "id",
    "title": "title",
    "englishtitle": "englishTitle",
    "displayorder": "displayOrder",
    "level": "level",
    "startdate": "startDate",
    "status": "status",
    "description": "description",
    "field": "field",
    "keytopics": "keyTopics",
    "goal": "goal",
    "textbook": "textbook",
    "objectives": "objectives",
    "resources": "resources",
    "bibliography": "bibliography"
}

SUBJECT_SINGLE_FIELDS = {
    "id", "title", "englishTitle", "displayOrder",
    "level", "startDate", "status", "field",
    "keyTopics", "goal", "textbook"
}

SUBJECT_MULTILINE_FIELDS = {
    "description", "objectives", "resources", "bibliography"
}


def discover_subjects():
    """
    기존 SUBJECTS 순서를 보존하면서 subjects 아래의 새 폴더도 자동 발견한다.
    따라서 새 과목을 만들 때 Python 목록을 다시 수정할 필요가 없다.
    """

    discovered = list(SUBJECTS)

    if not SUBJECTS_DIR.exists():
        return discovered

    for path in sorted(SUBJECTS_DIR.iterdir()):
        if not path.is_dir():
            continue

        subject = path.name

        if subject.startswith(".") or subject == "__pycache__":
            continue

        has_subject_files = any((
            (path / f"{subject}-subject.txt").exists(),
            (path / f"{subject}-chapters.txt").exists(),
            (path / f"{subject}-index.json").exists(),
            (path / "records").exists()
        ))

        if has_subject_files and subject not in discovered:
            discovered.append(subject)

    return discovered


def create_empty_subject_info():
    return {
        "id": "",
        "title": "",
        "englishTitle": "",
        "displayOrder": None,
        "level": "",
        "startDate": "",
        "status": "",
        "description": [],
        "field": "",
        "keyTopics": [],
        "goal": "",
        "textbook": None,
        "objectives": [],
        "resources": [],
        "bibliography": []
    }


def split_subject_values(value):
    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


def parse_subject_textbook(value):
    parts = [
        part.strip()
        for part in str(value).split("|", 2)
    ]

    while len(parts) < 3:
        parts.append("")

    title, author, edition = parts

    if not any(parts):
        return None

    return {
        "title": title,
        "author": author,
        "edition": edition
    }


def parse_subject_resource(value):
    parts = str(value).split("|", 1)
    url = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else url

    if not url:
        return None

    return {
        "url": url,
        "title": title
    }


def set_subject_value(data, field_name, value):
    value = str(value).strip()

    if field_name == "displayOrder":
        try:
            data[field_name] = int(value)
        except (TypeError, ValueError):
            data[field_name] = None
        return

    if field_name == "keyTopics":
        data[field_name] = split_subject_values(value)
        return

    if field_name == "textbook":
        data[field_name] = parse_subject_textbook(value)
        return

    data[field_name] = value


def append_subject_block_value(data, field_name, value):
    value = str(value).strip()

    if not value:
        return

    if field_name == "resources":
        resource = parse_subject_resource(value)

        if resource:
            data[field_name].append(resource)

        return

    data[field_name].append(value)


def read_subject_info(subject_path):
    data = create_empty_subject_info()

    try:
        lines = subject_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return data

    current_field = None

    for raw_line in lines:
        trimmed = raw_line.strip()

        if not trimmed:
            current_field = None
            continue

        if trimmed.startswith("#"):
            continue

        field_match = re.match(
            r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$",
            trimmed
        )

        if field_match:
            raw_field_name = field_match.group(1).lower()
            inline_value = field_match.group(2).strip()
            field_name = SUBJECT_FIELD_ALIASES.get(raw_field_name)

            if field_name:
                current_field = field_name

                if inline_value:
                    if field_name in SUBJECT_MULTILINE_FIELDS:
                        append_subject_block_value(
                            data,
                            field_name,
                            inline_value
                        )
                    else:
                        set_subject_value(
                            data,
                            field_name,
                            inline_value
                        )

                continue

        if current_field in SUBJECT_MULTILINE_FIELDS:
            append_subject_block_value(
                data,
                current_field,
                raw_line
            )

        elif current_field in SUBJECT_SINGLE_FIELDS:
            current_value = data.get(current_field)

            if current_value in ("", None, []):
                set_subject_value(
                    data,
                    current_field,
                    raw_line
                )

    data["sourceFile"] = subject_path.name

    return data


def print_subject_info_warning(subject, message):
    print("[WARNING]")
    print(f"  Subject : {subject}")
    print(f"  Problem : {message}")
    print()
    return 1


def validate_subject_info(subject, subject_info):
    warning_count = 0

    for field_name in ("id", "title", "displayOrder", "startDate"):
        if subject_info.get(field_name) in {"", None}:
            warning_count += print_subject_info_warning(
                subject,
                f"필수 항목이 비어 있습니다: {field_name}"
            )

    display_order = subject_info.get("displayOrder")

    if display_order is not None and display_order < 1:
        warning_count += print_subject_info_warning(
            subject,
            f"displayOrder는 1 이상의 정수여야 합니다: {display_order}"
        )

    start_date = subject_info.get("startDate")

    if start_date and not is_valid_iso_date(start_date):
        warning_count += print_subject_info_warning(
            subject,
            f"시작일 형식이 올바르지 않습니다: {start_date}"
        )

    return warning_count


def load_subject_info(subject):
    subject_path = (
        SUBJECTS_DIR
        / subject
        / f"{subject}-subject.txt"
    )

    if not subject_path.exists():
        return None, 0

    subject_info = read_subject_info(subject_path)
    warning_count = validate_subject_info(
        subject,
        subject_info
    )

    return subject_info, warning_count


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

    subject_info, subject_warning_count = load_subject_info(
        subject
    )

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
    warning_count = subject_warning_count
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
        "subjectInfo": subject_info,

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
    print(
        "  subject : "
        + (subject_info.get("title") if subject_info else "legacy")
    )
    print(f"  -> {index_path}")

    if unused_media:
        print()
        print("  Unused Media")

        for filename in unused_media:
            print(f"    - {filename}")

    print()

    return warning_count


def get_subject_catalog_entry(subject):
    index_path = (
        SUBJECTS_DIR
        / subject
        / f"{subject}-index.json"
    )

    index_data = read_existing_index(index_path)
    subject_info = index_data.get("subjectInfo")

    if isinstance(subject_info, dict) and subject_info.get("title"):
        display_order = subject_info.get("displayOrder")

        return {
            "subject": subject,
            "id": subject_info.get("id") or f"{subject}-subject",
            "title": subject_info.get("title") or subject,
            "englishTitle": subject_info.get("englishTitle") or "",
            "displayOrder": display_order,
            "level": subject_info.get("level") or "",
            "startDate": subject_info.get("startDate") or "",
            "status": subject_info.get("status") or "",
            "href": f"/subjects/subject.html?subject={subject}",
            "legacy": False,
            "subjectInfo": subject_info
        }

    fallback = SUBJECT_FALLBACK_METADATA.get(subject, {})

    fallback_info = {
        "id": f"{subject}-subject",
        "title": fallback.get("title") or subject,
        "englishTitle": fallback.get("englishTitle") or "",
        "displayOrder": fallback.get("displayOrder"),
        "level": "",
        "startDate": "",
        "status": "legacy",
        "description": [],
        "field": "",
        "keyTopics": [],
        "goal": "",
        "textbook": None,
        "objectives": [],
        "resources": [],
        "bibliography": []
    }

    return {
        "subject": subject,
        "id": fallback_info["id"],
        "title": fallback_info["title"],
        "englishTitle": fallback_info["englishTitle"],
        "displayOrder": fallback_info["displayOrder"],
        "level": "",
        "startDate": "",
        "status": "legacy",
        "href": f"/subjects/{subject}/{subject}.html",
        "legacy": True,
        "subjectInfo": fallback_info
    }


def build_subject_catalog_index(subjects, build_cache):
    entries = [
        get_subject_catalog_entry(subject)
        for subject in subjects
        if (SUBJECTS_DIR / subject).is_dir()
    ]

    entries.sort(
        key=lambda item: (
            item.get("displayOrder")
            if isinstance(item.get("displayOrder"), int)
            else 999999,
            item.get("title") or item.get("subject") or ""
        )
    )

    warning_count = 0
    order_subjects = {}
    id_subjects = {}

    for item in entries:
        order_value = item.get("displayOrder")
        item_id = item.get("id")

        if order_value is None:
            warning_count += print_subject_info_warning(
                item["subject"],
                "displayOrder가 없어 목록의 마지막에 표시됩니다."
            )
        else:
            order_subjects.setdefault(order_value, []).append(
                item["subject"]
            )

        if item_id:
            id_subjects.setdefault(item_id, []).append(
                item["subject"]
            )

    for order_value, matched_subjects in sorted(order_subjects.items()):
        if len(matched_subjects) > 1:
            warning_count += print_subject_info_warning(
                ", ".join(matched_subjects),
                f"중복 displayOrder입니다: {order_value}"
            )

    for item_id, matched_subjects in sorted(id_subjects.items()):
        if len(matched_subjects) > 1:
            warning_count += print_subject_info_warning(
                ", ".join(matched_subjects),
                f"중복 과목 id입니다: {item_id}"
            )

    catalog_data = {
        "cacheVersion": build_cache,
        "indexType": "subject-catalog",
        "subjectCount": len(entries),
        "subjects": entries,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    SUBJECT_CATALOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    SUBJECT_CATALOG_PATH.write_text(
        json.dumps(
            catalog_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("[OK] Subject Catalog Index")
    print(f"  subjects: {len(entries)}")
    print(
        "  modern  : "
        f"{sum(1 for item in entries if not item['legacy'])}"
    )
    print(
        "  legacy  : "
        f"{sum(1 for item in entries if item['legacy'])}"
    )
    print(f"  -> {SUBJECT_CATALOG_PATH}")
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

    has_physics_heading = any(
        re.match(
            r"^part\s*([A-Z0-9]+)\s+.+$",
            line,
            re.IGNORECASE
        )
        or re.match(
            r"^chapter\s*\d+\s+.+$",
            line,
            re.IGNORECASE
        )
        for line in lines
    )

    if has_physics_heading:
        return "physics"

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
        # Physics 형식의 Part
        # 예:
        # Part 1 역학
        # part1 역학
        # ----------------------------------------------------
        physics_part_match = re.match(
            r"^part\s*([A-Z0-9]+)\s+(.+)$",
            line,
            re.IGNORECASE
        )

        if (
            chapter_format == "physics"
            and physics_part_match
        ):
            part_number = physics_part_match.group(1)
            part_title = physics_part_match.group(2).strip()

            current_group = create_group(
                "part",
                part_number,
                part_title
            )

            groups.append(current_group)
            current_chapter = None
            continue


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
        # Physics 형식의 Chapter
        # 예:
        # Chapter 1 물리학과 측정
        # ----------------------------------------------------
        physics_chapter_match = re.match(
            r"^chapter\s*(\d+)\s+(.+)$",
            line,
            re.IGNORECASE
        )

        if (
            chapter_format == "physics"
            and physics_chapter_match
        ):
            chapter_number = (
                physics_chapter_match.group(1)
            )

            chapter_title = (
                physics_chapter_match
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
            r"^(?:(unit)\s*)?(\d+)\s+(.+)$",
            line,
            re.IGNORECASE
        )

        if numbered_chapter_match:
            chapter_prefix = numbered_chapter_match.group(1)
            chapter_number = numbered_chapter_match.group(2)

            chapter_title = (
                numbered_chapter_match
                .group(3)
                .strip()
            )

            current_chapter = create_chapter(
                chapter_number,
                chapter_title,
                current_group
            )

            if chapter_prefix:
                current_chapter["displayNumber"] = (
                    f"Unit {chapter_number}"
                )
            else:
                current_chapter["displayNumber"] = (
                    chapter_number
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
    "id",
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
        "id": "",
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
      id
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

    # id:reading-cosmos
    # id: reading-cosmos
    # id : reading-cosmos
    # 모두 허용한다.
        id_match = re.match(
            r"^id\s*:\s*(.*)$",
            trimmed,
            re.IGNORECASE
        )

        if id_match:
            current_section = "id"

            inline_id = id_match.group(1).strip()

            if inline_id:
                data["id"] = inline_id

            continue

        # "title:", "author:" 등의 섹션 시작
        if trimmed.endswith(":"):
            section_name = trimmed[:-1].strip().lower()

            if section_name in READING_SECTION_NAMES:
                current_section = section_name
                continue

        if not trimmed:
            continue

        if current_section == "id":
            if not data["id"]:
                data["id"] = trimmed

        elif current_section == "title":
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
    used_ids = set()

    for record_path in record_files:
        parsed = read_reading_record(
            record_path,
            media_dir
        )

        # TXT의 id를 사용하고,
        # id가 없으면 파일명을 임시 id로 사용한다.
        
        record_id = parsed["id"] or record_path.stem

        if not parsed["id"]:
            warning_count += print_reading_record_warning(
                category,
                record_path.name,
                "id가 비어 있어 파일명을 임시 id로 사용합니다."
            )

        # 중복 id 검사
        if record_id in used_ids:
            warning_count += print_reading_record_warning(
                category,
                record_path.name,
                f"중복 id입니다: {record_id}"
            )
            continue

        used_ids.add(record_id)

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
            "id": record_id,

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
# History Library Index
# ============================================================

HISTORY_SECTION_NAMES = {
    "id", "type", "name", "korean", "years",
    "country", "field", "keywords", "summary",
    "achievements", "related", "files", "sources"
}

HISTORY_LIST_FIELDS = {
    "field", "keywords", "related", "sources"
}

HISTORY_MULTILINE_FIELDS = {"summary", "achievements", "files"}
HISTORY_VALID_TYPES = {"person", "theory", "concept", "document"}


def create_empty_history_record():
    return {
        "id": "",
        "type": "",
        "name": "",
        "korean": "",
        "years": "",
        "country": "",
        "fields": [],
        "keywords": [],
        "summary": [],
        "achievements": [],
        "related": [],
        "sources": [],
        "media": []
    }


def split_comma_values(value):
    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


def append_unique(target, values):
    for value in values:
        if value not in target:
            target.append(value)


def add_history_media_item(data, line, media_dir):
    parts = line.split("|", 1)
    filename = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    if not filename:
        return

    data["media"].append({
        "file": filename,
        "title": title,
        "exists": (media_dir / filename).exists()
    })


def read_history_record(record_path, media_dir):
    """
    빈 줄은 자유롭게 사용할 수 있다.

    한 줄 값:
      id, type, name, korean, years, country

    쉼표 구분:
      field, keywords, related

    여러 줄:
      summary, achievements, files
    """

    data = create_empty_history_record()

    try:
        lines = record_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return data

    current_section = None

    for raw_line in lines:
        trimmed = raw_line.strip()

        if not trimmed:
            continue

        field_match = re.match(
            r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$",
            trimmed
        )

        if field_match:
            section_name = field_match.group(1).lower()
            inline_value = field_match.group(2).strip()

            if section_name in HISTORY_SECTION_NAMES:
                current_section = section_name

                if inline_value:
                    if section_name in HISTORY_LIST_FIELDS:
                        target_name = (
                            "fields"
                            if section_name == "field"
                            else section_name
                        )
                        append_unique(
                            data[target_name],
                            split_comma_values(inline_value)
                        )

                    elif section_name == "files":
                        add_history_media_item(
                            data,
                            inline_value,
                            media_dir
                        )

                    elif section_name in {"summary", "achievements"}:
                        data[section_name].append(inline_value)

                    else:
                        if not data[section_name]:
                            data[section_name] = inline_value

                continue

        if current_section is None:
            continue

        if current_section in HISTORY_LIST_FIELDS:
            target_name = (
                "fields"
                if current_section == "field"
                else current_section
            )
            append_unique(
                data[target_name],
                split_comma_values(trimmed)
            )

        elif current_section == "files":
            add_history_media_item(
                data,
                trimmed,
                media_dir
            )

        elif current_section in {"summary", "achievements"}:
            data[current_section].append(trimmed)

        elif not data[current_section]:
            data[current_section] = trimmed

    return data


def read_history_timeline(timeline_path):
    """
    형식:
      -624|thales|탈레스|Thales|자연철학의 출발점
    """

    timeline = []
    warnings = []
    seen_ids = set()

    try:
        lines = timeline_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return timeline, warnings

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        parts = [
            part.strip()
            for part in line.split("|", 4)
        ]

        if len(parts) != 5:
            warnings.append((
                line_number,
                "항목 수가 5개가 아닙니다.",
                raw_line
            ))
            continue

        year_text, item_id, korean, name, description = parts

        try:
            year = int(year_text)
        except ValueError:
            warnings.append((
                line_number,
                f"연도가 정수가 아닙니다: {year_text}",
                raw_line
            ))
            continue

        if not item_id:
            warnings.append((
                line_number,
                "id가 비어 있습니다.",
                raw_line
            ))
            continue

        if item_id in seen_ids:
            warnings.append((
                line_number,
                f"중복 id입니다: {item_id}",
                raw_line
            ))
            continue

        seen_ids.add(item_id)

        timeline.append({
            "year": year,
            "id": item_id,
            "korean": korean,
            "name": name,
            "description": description
        })

    timeline.sort(
        key=lambda item: (
            item["year"],
            item["korean"],
            item["id"]
        )
    )

    return timeline, warnings


def print_history_record_warning(category, record_file, message):
    print("[WARNING]")
    print(f"  History : {category}")
    print(f"  Record  : {record_file}")
    print(f"  Problem : {message}")
    print()
    return 1


def print_history_media_warning(category, record_file, media_items):
    missing = [
        item for item in media_items
        if not item["exists"]
    ]

    if not missing:
        return 0

    print("[WARNING]")
    print(f"  History : {category}")
    print(f"  Record  : {record_file}")
    print("  Missing media:")

    for item in missing:
        print(f"    - {item['file']}")

    print()
    return len(missing)


def print_history_timeline_warnings(
    category,
    timeline_file,
    warnings
):
    if not warnings:
        return 0

    print("[WARNING]")
    print(f"  History  : {category}")
    print(f"  Timeline : {timeline_file}")
    print("  Problems:")

    for line_number, message, raw_line in warnings:
        print(f"    - line {line_number}: {message}")
        print(f"      {raw_line}")

    print()
    return len(warnings)


def build_history_index(category, build_cache):
    category_dir = RESOURCES_DIR / category
    records_dir = category_dir / "records"
    media_dir = category_dir / "media"

    timeline_filename = HISTORY_TIMELINE_FILES.get(category)
    timeline_path = (
        category_dir / timeline_filename
        if timeline_filename
        else None
    )

    index_path = category_dir / f"{category}-index.json"

    if not category_dir.exists():
        print(f"[SKIP] History Index : {category} 폴더 없음")
        print()
        return 0

    warning_count = 0
    timeline = []

    if timeline_path and timeline_path.exists():
        timeline, timeline_warnings = read_history_timeline(
            timeline_path
        )
        warning_count += print_history_timeline_warnings(
            category,
            timeline_path.name,
            timeline_warnings
        )
    else:
        print(
            f"[SKIP] History Timeline : "
            f"{category}/{timeline_filename} 없음"
        )
        print()

    record_files = (
        sorted(records_dir.glob("*.txt"))
        if records_dir.exists()
        else []
    )

    media_files = (
        {
            file.name
            for file in media_dir.iterdir()
            if file.is_file()
        }
        if media_dir.exists()
        else set()
    )

    archives = []
    archive_ids = set()
    used_media = set()

    for record_path in record_files:
        parsed = read_history_record(
            record_path,
            media_dir
        )

        record_id = parsed["id"] or record_path.stem

        if not parsed["id"]:
            warning_count += print_history_record_warning(
                category,
                record_path.name,
                "id가 비어 있어 파일명을 임시 id로 사용합니다."
            )

        if record_id in archive_ids:
            warning_count += print_history_record_warning(
                category,
                record_path.name,
                f"중복 id입니다: {record_id}"
            )
            continue

        archive_ids.add(record_id)

        if not parsed["type"]:
            warning_count += print_history_record_warning(
                category,
                record_path.name,
                "type이 비어 있습니다."
            )
        elif parsed["type"] not in HISTORY_VALID_TYPES:
            warning_count += print_history_record_warning(
                category,
                record_path.name,
                f"지원하지 않는 type입니다: {parsed['type']}"
            )

        if not parsed["korean"] and not parsed["name"]:
            warning_count += print_history_record_warning(
                category,
                record_path.name,
                "korean과 name이 모두 비어 있습니다."
            )

        for media in parsed["media"]:
            used_media.add(media["file"])

        warning_count += print_history_media_warning(
            category,
            record_path.name,
            parsed["media"]
        )

        archives.append({
            "id": record_id,
            "file": record_path.name,
            "type": parsed["type"],
            "name": parsed["name"],
            "korean": parsed["korean"],
            "years": parsed["years"],
            "country": parsed["country"],
            "fields": parsed["fields"],
            "keywords": parsed["keywords"],
            "summary": parsed["summary"],
            "achievements": parsed["achievements"],
            "related": parsed["related"],
            "sources": parsed["sources"],
            "media": parsed["media"]
        })

    archives.sort(
        key=lambda item: (
            item.get("korean")
            or item.get("name")
            or item.get("id")
            or ""
        )
    )

    timeline_ids = {item["id"] for item in timeline}
    linked_ids = timeline_ids & archive_ids
    unlinked_timeline_ids = sorted(timeline_ids - archive_ids)
    archives_without_timeline = sorted(archive_ids - timeline_ids)
    unused_media = sorted(media_files - used_media)

    type_counts = {
        record_type: sum(
            1 for item in archives
            if item.get("type") == record_type
        )
        for record_type in sorted(HISTORY_VALID_TYPES)
    }

    index_data = {
        "cacheVersion": build_cache,
        "historyCategory": category,
        "timelineSource": (
            timeline_path.name
            if timeline_path and timeline_path.exists()
            else None
        ),
        "timelineCount": len(timeline),
        "archiveCount": len(archives),
        "mediaCount": sum(
            len(item["media"])
            for item in archives
        ),
        "linkedTimelineCount": len(linked_ids),
        "unlinkedTimelineIds": unlinked_timeline_ids,
        "archivesWithoutTimeline": archives_without_timeline,
        "typeCounts": type_counts,
        "fields": sorted({
            field
            for item in archives
            for field in item.get("fields", [])
        }),
        "keywords": sorted({
            keyword
            for item in archives
            for keyword in item.get("keywords", [])
        }),
        "timeline": timeline,
        "archives": archives,
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

    print(f"[OK] History Index : {category}")
    print(f"  timeline : {len(timeline)}")
    print(f"  archives : {len(archives)}")
    print(f"  linked   : {len(linked_ids)}")
    print(f"  media    : {index_data['mediaCount']}")
    print(f"  unused   : {len(unused_media)}")
    print(f"  -> {index_path}")

    if unlinked_timeline_ids:
        print()
        print("  Timeline Without Archive")
        for item_id in unlinked_timeline_ids:
            print(f"    - {item_id}")

    if archives_without_timeline:
        print()
        print("  Archive Without Timeline")
        for item_id in archives_without_timeline:
            print(f"    - {item_id}")

    if unused_media:
        print()
        print("  Unused Media")
        for filename in unused_media:
            print(f"    - {filename}")

    print()
    return warning_count


# ============================================================
# Computer Library Index
# ============================================================

COMPUTER_SECTION_NAMES = {
    "id", "title", "english", "aliases", "type", "field",
    "years", "keywords", "summary", "content", "related",
    "files", "sources"
}

COMPUTER_LIST_FIELDS = {
    "aliases", "field", "keywords", "related", "sources"
}

COMPUTER_VALID_TYPES = {
    "person", "organization", "machine", "theory", "language",
    "software", "concept", "event", "document"
}

COMPUTER_REQUIRED_FIELDS = {
    "id", "title", "keywords", "summary", "content"
}


def create_empty_computer_record():
    return {
        "id": "",
        "title": "",
        "english": "",
        "aliases": [],
        "type": "",
        "fields": [],
        "years": "",
        "keywords": [],
        "summary": [],
        "content": [],
        "related": [],
        "media": [],
        "sources": []
    }


def add_computer_media_item(data, line, media_dir):
    parts = line.split("|", 1)
    filename = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    if not filename:
        return

    data["media"].append({
        "file": filename,
        "title": title,
        "exists": (media_dir / filename).exists()
    })


def read_computer_record(record_path, media_dir):
    data = create_empty_computer_record()

    try:
        lines = record_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return data

    current_section = None

    for raw_line in lines:
        trimmed = raw_line.strip()

        if not trimmed or trimmed.startswith("#"):
            continue

        field_match = re.match(
            r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$",
            trimmed
        )

        if field_match:
            section_name = field_match.group(1).lower()
            inline_value = field_match.group(2).strip()

            if section_name in COMPUTER_SECTION_NAMES:
                current_section = section_name

                if inline_value:
                    if section_name in COMPUTER_LIST_FIELDS:
                        target_name = (
                            "fields"
                            if section_name == "field"
                            else section_name
                        )
                        append_unique(
                            data[target_name],
                            split_comma_values(inline_value)
                        )

                    elif section_name == "files":
                        add_computer_media_item(
                            data,
                            inline_value,
                            media_dir
                        )

                    elif section_name in {"summary", "content"}:
                        data[section_name].append(inline_value)

                    elif not data[section_name]:
                        data[section_name] = inline_value

                continue

        if current_section is None:
            continue

        if current_section in COMPUTER_LIST_FIELDS:
            target_name = (
                "fields"
                if current_section == "field"
                else current_section
            )
            append_unique(
                data[target_name],
                split_comma_values(trimmed)
            )

        elif current_section == "files":
            add_computer_media_item(
                data,
                trimmed,
                media_dir
            )

        elif current_section in {"summary", "content"}:
            data[current_section].append(trimmed)

        elif not data[current_section]:
            data[current_section] = trimmed

    return data


def read_computer_timeline(timeline_path):
    timeline = []
    warnings = []
    seen_ids = set()

    try:
        lines = timeline_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return timeline, warnings

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split("|", 4)]

        if len(parts) != 5:
            warnings.append((
                line_number,
                "항목 수가 5개가 아닙니다.",
                raw_line
            ))
            continue

        year_text, item_id, title, english, description = parts

        try:
            year = int(year_text)
        except ValueError:
            warnings.append((
                line_number,
                f"연도가 정수가 아닙니다: {year_text}",
                raw_line
            ))
            continue

        if not item_id:
            warnings.append((
                line_number,
                "id가 비어 있습니다.",
                raw_line
            ))
            continue

        if item_id in seen_ids:
            warnings.append((
                line_number,
                f"중복 id입니다: {item_id}",
                raw_line
            ))
            continue

        seen_ids.add(item_id)

        timeline.append({
            "year": year,
            "id": item_id,
            "title": title,
            "english": english,
            "description": description
        })

    timeline.sort(
        key=lambda item: (
            item["year"],
            item["title"],
            item["id"]
        )
    )

    return timeline, warnings


def print_computer_record_warning(record_file, message):
    print("[WARNING]")
    print("  Computer Archive")
    print(f"  Record  : {record_file}")
    print(f"  Problem : {message}")
    print()
    return 1


def print_computer_media_warning(record_file, media_items):
    missing = [
        item for item in media_items
        if not item["exists"]
    ]

    if not missing:
        return 0

    print("[WARNING]")
    print("  Computer Archive")
    print(f"  Record  : {record_file}")
    print("  Missing media:")

    for item in missing:
        print(f"    - {item['file']}")

    print()
    return len(missing)


def print_computer_timeline_warnings(timeline_file, warnings):
    if not warnings:
        return 0

    print("[WARNING]")
    print("  Computer Archive")
    print(f"  Timeline : {timeline_file}")
    print("  Problems:")

    for line_number, message, raw_line in warnings:
        print(f"    - line {line_number}: {message}")
        print(f"      {raw_line}")

    print()
    return len(warnings)


def validate_computer_required_fields(record_path, parsed):
    warning_count = 0

    for field_name in sorted(COMPUTER_REQUIRED_FIELDS):
        value = parsed.get(field_name)

        if not value:
            warning_count += print_computer_record_warning(
                record_path.name,
                f"필수 항목이 비어 있습니다: {field_name}"
            )

    return warning_count


def validate_computer_related_ids(records):
    record_ids = {
        record["id"]
        for record in records
        if record.get("id")
    }

    warnings = []

    for record in records:
        source_id = record.get("id") or record.get("file")

        for related_id in record.get("related", []):
            if related_id not in record_ids:
                warnings.append({
                    "sourceId": source_id,
                    "relatedId": related_id
                })

    return warnings


def build_computer_index(build_cache):
    computer_dir = RESOURCES_DIR / "computer"
    records_dir = computer_dir / "records"
    media_dir = computer_dir / "media"
    timeline_path = computer_dir / "computer_timeline.txt"
    index_path = computer_dir / "computer-index.json"

    if not computer_dir.exists():
        print(
            "[SKIP] Computer Index : "
            "resources/computer 폴더 없음"
        )
        print()
        return 0

    warning_count = 0
    timeline = []

    if timeline_path.exists():
        timeline, timeline_warnings = read_computer_timeline(
            timeline_path
        )
        warning_count += print_computer_timeline_warnings(
            timeline_path.name,
            timeline_warnings
        )
    else:
        print(
            "[SKIP] Computer Timeline : "
            "computer_timeline.txt 없음"
        )
        print()

    record_files = (
        sorted(records_dir.glob("*.txt"))
        if records_dir.exists()
        else []
    )

    media_files = (
        {
            file.name
            for file in media_dir.iterdir()
            if file.is_file()
        }
        if media_dir.exists()
        else set()
    )

    records = []
    record_ids = set()
    used_media = set()

    for record_path in record_files:
        parsed = read_computer_record(
            record_path,
            media_dir
        )

        warning_count += validate_computer_required_fields(
            record_path,
            parsed
        )

        record_id = parsed["id"] or record_path.stem

        if not parsed["id"]:
            warning_count += print_computer_record_warning(
                record_path.name,
                "id가 비어 있어 파일명을 임시 id로 사용합니다."
            )

        if record_id in record_ids:
            warning_count += print_computer_record_warning(
                record_path.name,
                f"중복 id입니다: {record_id}"
            )
            continue

        record_ids.add(record_id)

        record_type = parsed["type"]

        if (
            record_type
            and record_type not in COMPUTER_VALID_TYPES
        ):
            warning_count += print_computer_record_warning(
                record_path.name,
                f"지원하지 않는 type입니다: {record_type}"
            )

        for media in parsed["media"]:
            used_media.add(media["file"])

        warning_count += print_computer_media_warning(
            record_path.name,
            parsed["media"]
        )

        records.append({
            "id": record_id,
            "file": record_path.name,
            "title": parsed["title"],
            "english": parsed["english"],
            "aliases": parsed["aliases"],
            "type": parsed["type"],
            "fields": parsed["fields"],
            "years": parsed["years"],
            "keywords": parsed["keywords"],
            "summary": parsed["summary"],
            "content": parsed["content"],
            "related": parsed["related"],
            "media": parsed["media"],
            "sources": parsed["sources"]
        })

    records.sort(
        key=lambda item: (
            item.get("title")
            or item.get("english")
            or item.get("id")
            or ""
        )
    )

    # related ID는 History·Notes·Reading까지 모두 생성된 뒤
    # Integrated Search 단계에서 전역 기준으로 검사한다.
    related_warnings = []

    timeline_ids = {item["id"] for item in timeline}
    linked_timeline_ids = timeline_ids & record_ids
    timeline_without_record = sorted(timeline_ids - record_ids)
    records_without_timeline = sorted(record_ids - timeline_ids)
    unused_media = sorted(media_files - used_media)

    index_data = {
        "cacheVersion": build_cache,
        "archiveType": "knowledge-link",
        "archiveCategory": "computer",
        "timelineSource": (
            timeline_path.name
            if timeline_path.exists()
            else None
        ),
        "timelineCount": len(timeline),
        "recordCount": len(records),
        "mediaCount": sum(
            len(item["media"])
            for item in records
        ),
        "linkedTimelineCount": len(linked_timeline_ids),
        "timelineWithoutRecord": timeline_without_record,
        "recordsWithoutTimeline": records_without_timeline,
        "missingRelated": related_warnings,
        "typeCounts": {
            record_type: sum(
                1 for item in records
                if item.get("type") == record_type
            )
            for record_type in sorted(COMPUTER_VALID_TYPES)
        },
        "types": sorted({
            item["type"]
            for item in records
            if item.get("type")
        }),
        "fields": sorted({
            field
            for item in records
            for field in item.get("fields", [])
        }),
        "keywords": sorted({
            keyword
            for item in records
            for keyword in item.get("keywords", [])
        }),
        "timeline": timeline,
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

    print("[OK] Computer Knowledge Archive")
    print(f"  timeline : {len(timeline)}")
    print(f"  records  : {len(records)}")
    print(f"  linked   : {len(linked_timeline_ids)}")
    print(f"  related  : {len(related_warnings)} missing")
    print(f"  media    : {index_data['mediaCount']}")
    print(f"  unused   : {len(unused_media)}")
    print(f"  -> {index_path}")

    if timeline_without_record:
        print()
        print("  Timeline Without Record")
        for item_id in timeline_without_record:
            print(f"    - {item_id}")

    if records_without_timeline:
        print()
        print("  Record Without Timeline")
        for item_id in records_without_timeline:
            print(f"    - {item_id}")

    if unused_media:
        print()
        print("  Unused Media")
        for filename in unused_media:
            print(f"    - {filename}")

    print()
    return warning_count


# ============================================================
# Notes Library Index
# ============================================================

NOTES_SECTIONS = [
    "archive",
    "books",
    "media",
    "papers",
    "reference",
    "theory",
    "treasure"
]

NOTES_SECTION_NAMES = {
    "id", "title", "date", "type", "author", "published",
    "field", "fields", "keywords", "summary", "files",
    "source", "sources", "related"
}

NOTES_SINGLE_FIELDS = {
    "id", "title", "date", "type", "author", "published"
}

NOTES_LIST_FIELDS = {
    "field", "fields", "keywords", "related"
}

NOTES_REQUIRED_FIELDS = {
    "id", "title", "date", "type", "field", "summary", "keywords"
}

NOTES_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
NOTES_EXTERNAL_FILE_PATTERN = re.compile(
    r"^[a-z][a-z0-9+.-]*://",
    re.IGNORECASE
)


def create_empty_note_record():
    return {
        "id": "",
        "title": "",
        "date": "",
        "type": "",
        "author": "",
        "published": "",
        "fields": [],
        "keywords": [],
        "summary": [],
        "files": [],
        "sources": [],
        "related": []
    }


def normalize_note_section_name(section_name):
    if section_name == "fields":
        return "field"

    if section_name == "sources":
        return "source"

    return section_name


def get_note_file_format(filename):
    if NOTES_EXTERNAL_FILE_PATTERN.match(filename):
        return "link"

    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or "unknown"


def add_note_file_item(
    data,
    line,
    section,
    data_dir
):
    parts = line.split("|", 1)
    filename = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    if not filename:
        return

    is_external = bool(
        NOTES_EXTERNAL_FILE_PATTERN.match(filename)
    )

    if is_external:
        exists = True
        href = filename
        flat_name = True
    else:
        exists = (data_dir / filename).is_file()
        href = f"notes/{section}/data/{filename}"
        flat_name = Path(filename).name == filename

    data["files"].append({
        "file": filename,
        "title": title,
        "format": get_note_file_format(filename),
        "path": href,
        "exists": exists,
        "external": is_external,
        "flatName": flat_name
    })


def read_note_record(
    record_path,
    section,
    data_dir
):
    """
    Notes TXT 레코드 하나를 읽는다.

    공백 사용은 자유롭다.

      id:test
      id: test
      id :test
      id : test

    위 네 형식을 모두 동일하게 처리한다.

    한 줄 값:
      id, title, date, type, author, published

    쉼표 구분:
      field, keywords, related

    여러 줄:
      summary, files, source
    """

    data = create_empty_note_record()

    try:
        lines = record_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except Exception:
        return data

    current_section = None

    for raw_line in lines:
        trimmed = raw_line.strip()

        if not trimmed or trimmed.startswith("#"):
            continue

        field_match = re.match(
            r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$",
            trimmed
        )

        if field_match:
            section_name = field_match.group(1).lower()
            inline_value = field_match.group(2).strip()

            if section_name in NOTES_SECTION_NAMES:
                current_section = normalize_note_section_name(
                    section_name
                )

                if inline_value:
                    if current_section in {"field", "keywords", "related"}:
                        target_name = (
                            "fields"
                            if current_section == "field"
                            else current_section
                        )

                        append_unique(
                            data[target_name],
                            split_comma_values(inline_value)
                        )

                    elif current_section == "files":
                        add_note_file_item(
                            data,
                            inline_value,
                            section,
                            data_dir
                        )

                    elif current_section == "summary":
                        data["summary"].append(inline_value)

                    elif current_section == "source":
                        data["sources"].append(inline_value)

                    elif not data[current_section]:
                        data[current_section] = inline_value

                continue

        if current_section is None:
            continue

        if current_section in {"field", "keywords", "related"}:
            target_name = (
                "fields"
                if current_section == "field"
                else current_section
            )

            append_unique(
                data[target_name],
                split_comma_values(trimmed)
            )

        elif current_section == "files":
            add_note_file_item(
                data,
                trimmed,
                section,
                data_dir
            )

        elif current_section == "summary":
            data["summary"].append(trimmed)

        elif current_section == "source":
            data["sources"].append(trimmed)

        elif not data[current_section]:
            data[current_section] = trimmed

    data["fields"] = list(dict.fromkeys(data["fields"]))
    data["keywords"] = list(dict.fromkeys(data["keywords"]))
    data["sources"] = list(dict.fromkeys(data["sources"]))
    data["related"] = list(dict.fromkeys(data["related"]))

    return data


def print_note_record_warning(
    section,
    record_file,
    message
):
    print("[WARNING]")
    print(f"  Notes   : {section}")
    print(f"  Record  : {record_file}")
    print(f"  Problem : {message}")
    print()
    return 1


def print_note_file_warning(
    section,
    record_file,
    files
):
    missing = [
        item
        for item in files
        if not item["exists"]
    ]

    invalid_paths = [
        item
        for item in files
        if not item["external"]
        and not item["flatName"]
    ]

    warning_count = 0

    if missing:
        print("[WARNING]")
        print(f"  Notes   : {section}")
        print(f"  Record  : {record_file}")
        print("  Missing files:")

        for item in missing:
            print(f"    - {item['file']}")

        print()
        warning_count += len(missing)

    if invalid_paths:
        print("[WARNING]")
        print(f"  Notes   : {section}")
        print(f"  Record  : {record_file}")
        print("  files에는 data 폴더 안의 파일명만 적습니다:")

        for item in invalid_paths:
            print(f"    - {item['file']}")

        print()
        warning_count += len(invalid_paths)

    return warning_count


def print_note_loose_file_warning(
    section,
    filenames
):
    if not filenames:
        return 0

    print("[WARNING]")
    print(f"  Notes   : {section}")
    print("  Files outside data folder:")

    for filename in filenames:
        print(f"    - {filename}")

    print("  Move these files into the section/data folder.")
    print()

    return len(filenames)


def validate_note_required_fields(
    section,
    record_path,
    parsed
):
    warning_count = 0

    field_values = {
        "id": parsed["id"],
        "title": parsed["title"],
        "date": parsed["date"],
        "type": parsed["type"],
        "field": parsed["fields"],
        "summary": parsed["summary"],
        "keywords": parsed["keywords"]
    }

    for field_name in sorted(NOTES_REQUIRED_FIELDS):
        if not field_values[field_name]:
            warning_count += print_note_record_warning(
                section,
                record_path.name,
                f"필수 항목이 비어 있습니다: {field_name}"
            )

    if parsed["date"] and not is_valid_iso_date(parsed["date"]):
        warning_count += print_note_record_warning(
            section,
            record_path.name,
            f"날짜 형식이 올바르지 않습니다: {parsed['date']}"
        )

    if (
        parsed["id"]
        and not NOTES_ID_PATTERN.fullmatch(parsed["id"])
    ):
        warning_count += print_note_record_warning(
            section,
            record_path.name,
            (
                "id는 영문 소문자, 숫자, 하이픈 사용을 권장합니다: "
                f"{parsed['id']}"
            )
        )

    return warning_count


def collect_note_data_files(data_dir):
    if not data_dir.exists():
        return set()

    return {
        path.name
        for path in data_dir.iterdir()
        if path.is_file()
    }


def collect_note_loose_files(section_dir):
    return sorted(
        path.name
        for path in section_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() != ".txt"
    )


def build_notes_index(build_cache):
    notes_dir = RESOURCES_DIR / "notes"
    index_path = notes_dir / "notes-index.json"

    if not notes_dir.exists():
        print(
            "[SKIP] Notes Index : "
            "resources/notes 폴더 없음"
        )
        print()
        return 0

    records = []
    record_ids = set()
    warning_count = 0

    section_counts = {
        section: 0
        for section in NOTES_SECTIONS
    }

    section_file_counts = {
        section: 0
        for section in NOTES_SECTIONS
    }

    section_unused_files = {
        section: []
        for section in NOTES_SECTIONS
    }

    section_loose_files = {
        section: []
        for section in NOTES_SECTIONS
    }

    for section in NOTES_SECTIONS:
        section_dir = notes_dir / section
        data_dir = section_dir / "data"

        if not section_dir.exists():
            print(
                f"[SKIP] Notes Section : "
                f"{section} 폴더 없음"
            )
            print()
            continue

        # 섹션 바로 아래의 TXT만 읽는다.
        # data 폴더 내부는 재귀적으로 탐색하지 않는다.
        record_files = sorted(
            section_dir.glob("*.txt")
        )

        data_files = collect_note_data_files(data_dir)
        used_files = set()

        loose_files = collect_note_loose_files(section_dir)
        section_loose_files[section] = loose_files
        warning_count += print_note_loose_file_warning(
            section,
            loose_files
        )

        for record_path in record_files:
            parsed = read_note_record(
                record_path,
                section,
                data_dir
            )

            warning_count += validate_note_required_fields(
                section,
                record_path,
                parsed
            )

            record_id = parsed["id"] or record_path.stem

            if not parsed["id"]:
                warning_count += print_note_record_warning(
                    section,
                    record_path.name,
                    (
                        "id가 비어 있어 파일명을 "
                        "임시 id로 사용합니다."
                    )
                )

            if record_id in record_ids:
                warning_count += print_note_record_warning(
                    section,
                    record_path.name,
                    f"중복 id입니다: {record_id}"
                )
                continue

            record_ids.add(record_id)

            warning_count += print_note_file_warning(
                section,
                record_path.name,
                parsed["files"]
            )

            for item in parsed["files"]:
                if not item["external"]:
                    used_files.add(item["file"])

            summary_text = " ".join(
                line.strip()
                for line in parsed["summary"]
                if line.strip()
            )

            records.append({
                "id": record_id,
                "section": section,
                "file": record_path.name,
                "title": parsed["title"],
                "date": parsed["date"],
                "type": parsed["type"],
                "author": parsed["author"],
                "published": parsed["published"],
                "fields": parsed["fields"],
                "keywords": parsed["keywords"],
                "summary": summary_text,
                "files": [
                    {
                        "file": item["file"],
                        "title": item["title"],
                        "format": item["format"],
                        "path": item["path"],
                        "exists": item["exists"]
                    }
                    for item in parsed["files"]
                ],
                "source": parsed["sources"],
                "related": parsed["related"]
            })

        section_counts[section] = len(record_files)
        section_file_counts[section] = sum(
            len(record["files"])
            for record in records
            if record["section"] == section
        )

        unused_files = sorted(data_files - used_files)
        section_unused_files[section] = unused_files

    records.sort(
        key=lambda item: (
            item.get("date") or "",
            item.get("title") or "",
            item.get("id") or ""
        ),
        reverse=True
    )

    all_files = [
        item
        for record in records
        for item in record["files"]
    ]

    existing_file_count = sum(
        1
        for item in all_files
        if item["exists"]
    )

    missing_file_count = sum(
        1
        for item in all_files
        if not item["exists"]
    )

    type_counts = {
        record_type: sum(
            1
            for record in records
            if record.get("type") == record_type
        )
        for record_type in sorted({
            record["type"]
            for record in records
            if record.get("type")
        })
    }

    root_txt_files = sorted(
        path.name
        for path in notes_dir.glob("*.txt")
    )

    index_data = {
        "cacheVersion": build_cache,
        "archiveType": "notes",
        "sections": NOTES_SECTIONS,
        "recordCount": len(records),
        "fileCount": len(all_files),
        "existingFileCount": existing_file_count,
        "missingFileCount": missing_file_count,
        "sectionCounts": section_counts,
        "sectionFileCounts": section_file_counts,
        "typeCounts": type_counts,
        "types": sorted({
            record["type"]
            for record in records
            if record.get("type")
        }),
        "authors": sorted({
            record["author"]
            for record in records
            if record.get("author")
        }),
        "fields": sorted({
            field
            for record in records
            for field in record.get("fields", [])
        }),
        "keywords": sorted({
            keyword
            for record in records
            for keyword in record.get("keywords", [])
        }),
        "rootTxtFilesIgnored": root_txt_files,
        "unusedDataFiles": section_unused_files,
        "filesOutsideDataFolder": section_loose_files,
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

    print("[OK] Notes Knowledge Archive")
    print(f"  records  : {len(records)}")
    print(f"  files    : {len(all_files)}")
    print(f"  existing : {existing_file_count}")
    print(f"  missing  : {missing_file_count}")
    print(f"  -> {index_path}")

    print()
    print("  Section Records")
    for section in NOTES_SECTIONS:
        print(
            f"    - {section:<9}: "
            f"{section_counts[section]}"
        )

    unused_total = sum(
        len(files)
        for files in section_unused_files.values()
    )

    if unused_total:
        print()
        print("  Unused Data Files")

        for section in NOTES_SECTIONS:
            for filename in section_unused_files[section]:
                print(f"    - {section}/data/{filename}")

    if root_txt_files:
        print()
        print("  Root TXT Files Ignored")

        for filename in root_txt_files:
            print(f"    - {filename}")

    print()
    return warning_count



# ============================================================
# Integrated Search Index
# ============================================================

SEARCH_INDEX_PATH = RESOURCES_DIR / "search-index.json"

SEARCH_CATEGORY_TITLES = {
    "science-history": "과학사",
    "math-history": "수학사",
    "philosophy-history": "철학사",
    "computer": "컴퓨터",
    "notes": "노트",
    "science": "과학 서적",
    "philosophy": "철학 서적",
    "fiction": "소설과 에세이",
    "humanities": "인문·교양",
    "subjects": "교과목"
}


def read_search_source(index_path):
    if not index_path.exists():
        print(f"[SKIP] Search Source : {index_path} 없음")
        return None

    try:
        data = json.loads(
            index_path.read_text(encoding="utf-8")
        )
    except Exception as error:
        print("[WARNING]")
        print(f"  Search Source : {index_path}")
        print(f"  Problem       : JSON 읽기 실패: {error}")
        print()
        return None

    if not isinstance(data, dict):
        print("[WARNING]")
        print(f"  Search Source : {index_path}")
        print("  Problem       : JSON 최상위 값이 객체가 아닙니다.")
        print()
        return None

    return data


def search_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        values = value
    else:
        values = [value]

    result = []

    for item in values:
        text = str(item).strip()

        if text and text not in result:
            result.append(text)

    return result


def merge_search_lists(*values):
    merged = []

    for value in values:
        append_unique(merged, search_list(value))

    return merged


def make_search_record(
    *,
    record_id,
    source,
    category,
    location,
    kind,
    record_type,
    title,
    subtitle="",
    aliases=None,
    date="",
    fields=None,
    keywords=None,
    summary=None,
    content=None,
    related=None,
    href=""
):
    return {
        "id": str(record_id or "").strip(),
        "source": source,
        "category": category,
        "categoryTitle": SEARCH_CATEGORY_TITLES.get(
            category,
            category
        ),
        "location": location,
        "kind": kind,
        "type": str(record_type or "").strip(),
        "title": str(title or record_id or "제목 없는 자료").strip(),
        "subtitle": str(subtitle or "").strip(),
        "aliases": search_list(aliases),
        "date": str(date or "").strip(),
        "fields": search_list(fields),
        "keywords": search_list(keywords),
        "summary": search_list(summary),
        "content": search_list(content),
        "related": search_list(related),
        "href": href
    }


def build_history_search_records(category, data):
    timeline_items = (
        data.get("timeline")
        if isinstance(data.get("timeline"), list)
        else []
    )

    archive_items = (
        data.get("archives")
        if isinstance(data.get("archives"), list)
        else []
    )

    timeline_by_id = {
        str(item.get("id") or "").strip(): item
        for item in timeline_items
        if str(item.get("id") or "").strip()
    }

    archive_by_id = {
        str(item.get("id") or "").strip(): item
        for item in archive_items
        if str(item.get("id") or "").strip()
    }

    ordered_ids = list(timeline_by_id)
    append_unique(
        ordered_ids,
        [
            item_id
            for item_id in archive_by_id
            if item_id not in timeline_by_id
        ]
    )

    records = []

    for item_id in ordered_ids:
        timeline_item = timeline_by_id.get(item_id, {})
        archive_item = archive_by_id.get(item_id, {})

        korean = (
            archive_item.get("korean")
            or timeline_item.get("korean")
            or ""
        )

        original_name = (
            archive_item.get("name")
            or timeline_item.get("name")
            or ""
        )

        title = korean or original_name or item_id
        subtitle = original_name if original_name != title else ""

        if timeline_item and archive_item:
            location = "연대기 · 상세 자료"
        elif timeline_item:
            location = "연대기"
        else:
            location = "상세 자료"

        date_value = (
            archive_item.get("years")
            or timeline_item.get("year")
            or ""
        )

        records.append(
            make_search_record(
                record_id=item_id,
                source="library",
                category=category,
                location=location,
                kind="history",
                record_type=(
                    archive_item.get("type")
                    or "timeline"
                ),
                title=title,
                subtitle=subtitle,
                aliases=merge_search_lists(
                    korean,
                    original_name
                ),
                date=date_value,
                fields=archive_item.get("fields"),
                keywords=archive_item.get("keywords"),
                summary=merge_search_lists(
                    timeline_item.get("description"),
                    archive_item.get("summary")
                ),
                content=archive_item.get("achievements"),
                related=archive_item.get("related"),
                href=(
                    "/resources/library.html"
                    f"?category={category}&id={item_id}"
                )
            )
        )

    return records


def build_computer_search_records(data):
    category = "computer"

    timeline_items = (
        data.get("timeline")
        if isinstance(data.get("timeline"), list)
        else []
    )

    detail_items = (
        data.get("records")
        if isinstance(data.get("records"), list)
        else []
    )

    timeline_by_id = {
        str(item.get("id") or "").strip(): item
        for item in timeline_items
        if str(item.get("id") or "").strip()
    }

    detail_by_id = {
        str(item.get("id") or "").strip(): item
        for item in detail_items
        if str(item.get("id") or "").strip()
    }

    ordered_ids = list(timeline_by_id)
    append_unique(
        ordered_ids,
        [
            item_id
            for item_id in detail_by_id
            if item_id not in timeline_by_id
        ]
    )

    records = []

    for item_id in ordered_ids:
        timeline_item = timeline_by_id.get(item_id, {})
        detail_item = detail_by_id.get(item_id, {})

        title = (
            detail_item.get("title")
            or timeline_item.get("title")
            or detail_item.get("english")
            or timeline_item.get("english")
            or item_id
        )

        english = (
            detail_item.get("english")
            or timeline_item.get("english")
            or ""
        )

        if timeline_item and detail_item:
            location = "연대기 · 상세 자료"
        elif timeline_item:
            location = "연대기"
        else:
            location = "상세 자료"

        records.append(
            make_search_record(
                record_id=item_id,
                source="library",
                category=category,
                location=location,
                kind="computer",
                record_type=(
                    detail_item.get("type")
                    or "timeline"
                ),
                title=title,
                subtitle=(
                    english
                    if english != title
                    else ""
                ),
                aliases=merge_search_lists(
                    detail_item.get("aliases"),
                    english,
                    timeline_item.get("title")
                ),
                date=(
                    detail_item.get("years")
                    or timeline_item.get("year")
                    or ""
                ),
                fields=detail_item.get("fields"),
                keywords=detail_item.get("keywords"),
                summary=merge_search_lists(
                    timeline_item.get("description"),
                    detail_item.get("summary")
                ),
                content=detail_item.get("content"),
                related=detail_item.get("related"),
                href=(
                    "/resources/library.html"
                    f"?category=computer&id={item_id}"
                )
            )
        )

    return records


def build_notes_search_records(data):
    source_items = (
        data.get("records")
        if isinstance(data.get("records"), list)
        else []
    )

    records = []

    for item in source_items:
        item_id = str(item.get("id") or "").strip()

        if not item_id:
            continue

        section = str(
            item.get("section") or "archive"
        ).strip()

        file_text = []

        for file_item in search_list(item.get("files")):
            file_text.append(file_item)

        if isinstance(item.get("files"), list):
            file_text = []

            for file_item in item["files"]:
                if not isinstance(file_item, dict):
                    file_text.extend(search_list(file_item))
                    continue

                file_text.extend(
                    merge_search_lists(
                        file_item.get("title"),
                        file_item.get("file"),
                        file_item.get("format")
                    )
                )

        subtitle = (
            item.get("author")
            or item.get("type")
            or ""
        )

        records.append(
            make_search_record(
                record_id=item_id,
                source="notes",
                category="notes",
                location=section,
                kind="note",
                record_type=item.get("type"),
                title=item.get("title") or item_id,
                subtitle=subtitle,
                aliases=merge_search_lists(
                    item.get("author"),
                    item.get("published")
                ),
                date=item.get("date"),
                fields=item.get("fields"),
                keywords=item.get("keywords"),
                summary=item.get("summary"),
                content=file_text,
                related=item.get("related"),
                href=(
                    "/resources/library.html"
                    f"?category=notes&section={section}&id={item_id}"
                )
            )
        )

    return records


def build_reading_search_records(category, data):
    source_items = (
        data.get("books")
        if isinstance(data.get("books"), list)
        else []
    )

    records = []

    for item in source_items:
        item_id = str(item.get("id") or "").strip()

        if not item_id:
            continue

        book_field = str(item.get("category") or "").strip()

        records.append(
            make_search_record(
                record_id=item_id,
                source="reading",
                category=category,
                location=book_field or "독서 기록",
                kind="reading",
                record_type=item.get("status"),
                title=item.get("title") or item_id,
                subtitle=item.get("author"),
                aliases=item.get("author"),
                date=(
                    item.get("finishDate")
                    or item.get("startDate")
                    or item.get("date")
                    or ""
                ),
                fields=book_field,
                keywords=item.get("keywords"),
                summary=item.get("summary"),
                content=item.get("reflection"),
                related=[],
                href=(
                    "/reading/reading.html"
                    f"?category={category}&id={item_id}"
                )
            )
        )

    return records


def build_subject_search_records(data):
    source_items = (
        data.get("subjects")
        if isinstance(data.get("subjects"), list)
        else []
    )

    records = []

    for item in source_items:
        subject_key = str(
            item.get("subject") or ""
        ).strip()

        subject_info = item.get("subjectInfo")

        if not isinstance(subject_info, dict):
            subject_info = {}

        item_id = str(
            item.get("id")
            or subject_info.get("id")
            or f"{subject_key}-subject"
        ).strip()

        if not item_id or not subject_key:
            continue

        textbook = subject_info.get("textbook")
        textbook_text = []

        if isinstance(textbook, dict):
            textbook_text = [
                textbook.get("title"),
                textbook.get("author"),
                textbook.get("edition")
            ]
        elif textbook:
            textbook_text = [textbook]

        resources = []

        for resource in search_list(
            subject_info.get("resources")
        ):
            resources.append(resource)

        if isinstance(subject_info.get("resources"), list):
            resources = []

            for resource in subject_info["resources"]:
                if isinstance(resource, dict):
                    resources.extend(
                        merge_search_lists(
                            resource.get("title"),
                            resource.get("url")
                        )
                    )
                else:
                    resources.extend(search_list(resource))

        records.append(
            make_search_record(
                record_id=item_id,
                source="subject",
                category="subjects",
                location=(
                    subject_info.get("field")
                    or "교과목 소개"
                ),
                kind="subject",
                record_type=(
                    item.get("status")
                    or subject_info.get("status")
                    or "subject"
                ),
                title=(
                    item.get("title")
                    or subject_info.get("title")
                    or subject_key
                ),
                subtitle=(
                    item.get("englishTitle")
                    or subject_info.get("englishTitle")
                    or ""
                ),
                aliases=merge_search_lists(
                    subject_key,
                    item.get("englishTitle"),
                    subject_info.get("englishTitle")
                ),
                date=(
                    item.get("startDate")
                    or subject_info.get("startDate")
                    or ""
                ),
                fields=merge_search_lists(
                    item.get("level"),
                    subject_info.get("field"),
                    subject_info.get("level")
                ),
                keywords=subject_info.get("keyTopics"),
                summary=merge_search_lists(
                    subject_info.get("description"),
                    subject_info.get("goal")
                ),
                content=merge_search_lists(
                    subject_info.get("objectives"),
                    textbook_text,
                    subject_info.get("bibliography"),
                    resources
                ),
                related=[],
                href=(
                    item.get("href")
                    or f"/subjects/subject.html?subject={subject_key}"
                )
            )
        )

    return records


def print_global_id_warnings(records):
    locations_by_id = {}

    for record in records:
        item_id = record.get("id")

        if not item_id:
            continue

        location_key = (
            record.get("category"),
            record.get("location")
        )

        locations_by_id.setdefault(item_id, [])

        if location_key not in locations_by_id[item_id]:
            locations_by_id[item_id].append(location_key)

    duplicates = {
        item_id: locations
        for item_id, locations in locations_by_id.items()
        if len({category for category, _ in locations}) > 1
    }

    if not duplicates:
        return 0

    print("[WARNING]")
    print("  Integrated Search")
    print("  Duplicate global IDs:")

    for item_id, locations in sorted(duplicates.items()):
        location_text = ", ".join(
            f"{category}/{location}"
            for category, location in locations
        )
        print(f"    - {item_id}: {location_text}")

    print()
    return len(duplicates)


def print_global_related_warnings(records):
    known_ids = {
        record.get("id")
        for record in records
        if record.get("id")
    }

    missing_links = []

    for record in records:
        source_id = record.get("id")

        for related_id in record.get("related", []):
            if related_id not in known_ids:
                missing_links.append((source_id, related_id))

    missing_links = list(dict.fromkeys(missing_links))

    if not missing_links:
        return 0

    print("[WARNING]")
    print("  Integrated Search")
    print("  Missing related IDs:")

    for source_id, related_id in missing_links:
        print(f"    - {source_id} -> {related_id}")

    print()
    return len(missing_links)


def build_integrated_search_index(build_cache):
    records = []
    source_counts = {}
    warning_count = 0

    subject_data = read_search_source(
        SUBJECT_CATALOG_PATH
    )

    if subject_data is not None:
        subject_records = build_subject_search_records(
            subject_data
        )
        records.extend(subject_records)
        source_counts["subjects"] = len(subject_records)

    for category in HISTORY_CATEGORIES:
        index_path = (
            RESOURCES_DIR
            / category
            / f"{category}-index.json"
        )

        data = read_search_source(index_path)

        if data is None:
            continue

        category_records = build_history_search_records(
            category,
            data
        )

        records.extend(category_records)
        source_counts[category] = len(category_records)

    computer_data = read_search_source(
        RESOURCES_DIR / "computer" / "computer-index.json"
    )

    if computer_data is not None:
        computer_records = build_computer_search_records(
            computer_data
        )
        records.extend(computer_records)
        source_counts["computer"] = len(computer_records)

    notes_data = read_search_source(
        RESOURCES_DIR / "notes" / "notes-index.json"
    )

    if notes_data is not None:
        note_records = build_notes_search_records(notes_data)
        records.extend(note_records)
        source_counts["notes"] = len(note_records)

    for category in READING_CATEGORIES:
        index_path = (
            READING_DIR
            / category
            / f"{category}-index.json"
        )

        data = read_search_source(index_path)

        if data is None:
            continue

        category_records = build_reading_search_records(
            category,
            data
        )

        records.extend(category_records)
        source_counts[f"reading-{category}"] = len(
            category_records
        )

    records.sort(
        key=lambda item: (
            item.get("categoryTitle") or "",
            item.get("location") or "",
            item.get("title") or "",
            item.get("id") or ""
        )
    )

    warning_count += print_global_id_warnings(records)
    warning_count += print_global_related_warnings(records)

    index_data = {
        "cacheVersion": build_cache,
        "indexType": "integrated-search",
        "recordCount": len(records),
        "sourceCounts": source_counts,
        "records": records,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    SEARCH_INDEX_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    SEARCH_INDEX_PATH.write_text(
        json.dumps(
            index_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("[OK] Integrated Search Index")
    print(f"  records : {len(records)}")
    print(f"  sources : {len(source_counts)}")
    print(f"  -> {SEARCH_INDEX_PATH}")
    print()

    return warning_count


# ============================================================
# Main Build
# ============================================================

def main():
    build_cache = int(time.time())

    print("===================================")
    print("LOGIA Build v1.6")
    print("===================================")
    print()

    total_warnings = 0
    subjects = discover_subjects()

    print("-----------------------------------")
    print("Building Study Indexes")
    print("-----------------------------------")
    print()

    for subject in subjects:
        total_warnings += build_subject_index(
            subject,
            build_cache
        )

    print("-----------------------------------")
    print("Building Subject Catalog")
    print("-----------------------------------")
    print()

    total_warnings += build_subject_catalog_index(
        subjects,
        build_cache
    )

    print("-----------------------------------")
    print("Building Chapter Indexes")
    print("-----------------------------------")
    print()

    for subject in subjects:
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

    print("-----------------------------------")
    print("Building History Library Indexes")
    print("-----------------------------------")
    print()

    for category in HISTORY_CATEGORIES:
        total_warnings += build_history_index(
            category,
            build_cache
        )

    # Computer와 Notes는 자료 형식이 확정된 뒤
    # 각각의 독립 Builder를 main()에 연결한다.
    total_warnings += build_computer_index(
        build_cache
    )

    total_warnings += build_notes_index(
        build_cache
    )

    print("-----------------------------------")
    print("Building Integrated Search Index")
    print("-----------------------------------")
    print()

    total_warnings += build_integrated_search_index(
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