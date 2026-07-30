"use strict";


/* =========================================================
   LOGIA Study Board
   ========================================================= */

const StudyBoard = (() => {

  const CONFIG = window.BOARD_CONFIG || {};

  const SUBJECT = String(
    CONFIG.subject || ""
  ).trim();

  const BASE_PATH = String(
    CONFIG.basePath || ""
  );

  const INDEX_FILE =
    `${BASE_PATH}${SUBJECT}-index.json`;

  const CHAPTER_FILE =
    `${BASE_PATH}${SUBJECT}-chapters.json`;

  const CHAPTER_SEPARATOR =
    CONFIG.separator ?? " | ";

  const CHAPTER_TITLE_LAYOUT =
    CONFIG.chapterTitleLayout ?? "inline";

  let startDate = String(
    CONFIG.startDate || ""
  ).trim();

  let studyIndex = null;
  let chapterIndex = null;

  let calendarYear = null;
  let calendarMonth = null;


  /* ---------------------------------------------------------
     DOM
     --------------------------------------------------------- */

  const calendarTitle = document.getElementById(
    "calendar-title"
  );

  const calendarGrid = document.getElementById(
    "calendar-grid"
  );

  const prevMonthButton = document.getElementById(
    "prev-month"
  );

  const nextMonthButton = document.getElementById(
    "next-month"
  );

  const dateInput = document.getElementById(
    "study-date"
  );

  const memoText = document.getElementById(
    "memo-text"
  );

  const progressText = document.getElementById(
    "progress-text"
  );

  const progressFill = document.getElementById(
    "progress-fill"
  );

  const filesList = document.getElementById(
    "files-list"
  );

  const startDateText = document.getElementById(
    "start-date"
  );

  const elapsedText = document.getElementById(
    "elapsed-text"
  );

  const studytimeText = document.getElementById(
    "studytime-text"
  );

  const recentDateText = document.getElementById(
    "recent-date"
  );

  const studyDaysText = document.getElementById(
    "study-days-text"
  );

  const chapterText = document.getElementById(
    "chapter-text"
  );


  /* ---------------------------------------------------------
     Loading
     --------------------------------------------------------- */

  async function fetchJsonNoCache(url) {
    const separator = url.includes("?") ? "&" : "?";

    const response = await fetch(
      `${url}${separator}v=${Date.now()}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(`${url}: HTTP ${response.status}`);
    }

    return response.json();
  }


  async function loadStudyIndex() {
    studyIndex = await fetchJsonNoCache(INDEX_FILE);

    startDate = String(
      studyIndex?.subjectInfo?.startDate
      || startDate
      || studyIndex?.firstRecord
      || ""
    ).trim();
  }


  async function loadChapterIndex() {
    chapterIndex = await fetchJsonNoCache(CHAPTER_FILE);
  }


  /* ---------------------------------------------------------
     Initialization
     --------------------------------------------------------- */

  function hasRequiredDom() {
    return Boolean(
      calendarTitle
      && calendarGrid
      && prevMonthButton
      && nextMonthButton
      && dateInput
      && memoText
      && progressText
      && progressFill
      && filesList
      && startDateText
      && elapsedText
      && studytimeText
      && recentDateText
      && studyDaysText
      && chapterText
    );
  }


  async function init() {
    if (!hasRequiredDom()) {
      return;
    }

    if (!SUBJECT || !/^[a-z0-9-]+$/.test(SUBJECT)) {
      showBoardError("과목 설정을 확인할 수 없습니다.");
      return;
    }

    try {
      await Promise.all([
        loadChapterIndex(),
        loadStudyIndex()
      ]);

      initializeStatus();
      initializeCalendar();
      bindEvents();

    } catch (error) {
      console.error(error);
      showBoardError("학습 데이터를 불러오지 못했습니다.");
    }
  }


  function initializeStatus() {
    const today = getKoreaToday();

    startDateText.textContent = startDate || "-";

    elapsedText.textContent = startDate
      ? `(${getElapsedDays(startDate, today)}일 경과)`
      : "";

    recentDateText.textContent =
      studyIndex?.lastRecord || "-";

    studyDaysText.textContent = studyIndex?.studyDays
      ? `(학습일 ${studyIndex.studyDays}일)`
      : "";
  }


  function initializeCalendar() {
    const today = getKoreaToday();
    const [year, month] = today.split("-").map(Number);

    calendarYear = year;
    calendarMonth = month - 1;
    dateInput.value = today;

    buildCalendar();
    markRecordedDates();
    loadStudyRecord(today);
    selectCalendarDay(today);
  }


  function bindEvents() {
    dateInput.addEventListener("change", () => {
      loadStudyRecord(dateInput.value);
      selectCalendarDay(dateInput.value);
    });

    prevMonthButton.addEventListener("click", () => {
      calendarMonth--;

      if (calendarMonth < 0) {
        calendarMonth = 11;
        calendarYear--;
      }

      rebuildCalendarState();
    });

    nextMonthButton.addEventListener("click", () => {
      calendarMonth++;

      if (calendarMonth > 11) {
        calendarMonth = 0;
        calendarYear++;
      }

      rebuildCalendarState();
    });
  }


  function rebuildCalendarState() {
    buildCalendar();
    markRecordedDates();
    selectCalendarDay(dateInput.value);
  }


  function showBoardError(message) {
    memoText.value = message;
    updateProgress("-");
    studytimeText.textContent = "-";
    chapterText.textContent = "-";
    filesList.innerHTML = "";
  }

  function renderMath(container) {
    if (
      !container ||
      typeof renderMathInElement !== "function"
    ) {
      return;
    }

    renderMathInElement(container, {
      delimiters: [
        {
          left: "\\(",
          right: "\\)",
          display: false
        },
        {
          left: "\\[",
          right: "\\]",
          display: true
        }
      ],
      throwOnError: false
    });
  }

  /* ---------------------------------------------------------
     Study Record
     --------------------------------------------------------- */

  function loadStudyRecord(date) {
    if (!Array.isArray(studyIndex?.records)) {
      showBoardError("학습 데이터베이스를 불러오지 못했습니다.");
      return;
    }

    const record = studyIndex.records.find(
      item => item.date === date
    );

    const progress = getProgressForDate(date);

    updateProgress(progress);
    chapterText.textContent = getChapterTitle(progress);
    renderMath(chapterText);

    if (!record) {
      memoText.value = "이 날짜에는 학습 기록이 없습니다.";
      studytimeText.textContent = "-";
      filesList.innerHTML = "";
      return;
    }

    memoText.value = Array.isArray(record.memo)
      && record.memo.length
        ? record.memo
            .join("\n")
            .replaceAll("\\n", "\n")
        : "메모가 없습니다.";

    studytimeText.textContent = record.studytime || "-";

    renderMedia(record.media);
  }


  function renderMedia(mediaItems) {
    filesList.innerHTML = "";

    if (!Array.isArray(mediaItems) || !mediaItems.length) {
      return;
    }

    mediaItems.forEach(media => {
      const listItem = document.createElement("li");

      if (media.exists === false) {
        listItem.textContent =
          `${media.title || media.file} (파일 없음)`;

        filesList.appendChild(listItem);
        return;
      }

      const link = document.createElement("a");

      link.href =
        `${BASE_PATH}media/${encodeURIComponent(media.file)}`;

      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = media.title || media.file;

      listItem.appendChild(link);
      filesList.appendChild(listItem);
    });
  }


  function getProgressForDate(date) {
    if (!Array.isArray(studyIndex?.records)) {
      return "-";
    }

    if (startDate && date < startDate) {
      return "-";
    }

    const record = [...studyIndex.records]
      .filter(item => item.date <= date && item.progress)
      .sort((first, second) =>
        second.date.localeCompare(first.date)
      )[0];

    return record ? record.progress : "-";
  }


  /* ---------------------------------------------------------
     Progress Calculation
     --------------------------------------------------------- */

  function getProgressUnit(progress) {
    return String(progress || "")
      .split("/")[0]
      .trim();
  }


  function getChapterFormat() {
    return String(
      CONFIG.chapterFormat
      || chapterIndex?.format
      || "general"
    );
  }


  function getChapters() {
    return Array.isArray(chapterIndex?.chapters)
      ? chapterIndex.chapters
      : [];
  }


  function getSectionUnits() {
    return getChapters().flatMap(chapter => {
      const sections = Array.isArray(chapter.sections)
        ? chapter.sections
        : [];

      return sections.map(section => ({
        ...section,
        chapter
      }));
    });
  }


  function usesSectionProgress() {
    const format = getChapterFormat();
    const sections = getSectionUnits();

    if (!sections.length) {
      return false;
    }

    return !["classic", "simple"].includes(format);
  }


  function getStudyUnits() {
    return usesSectionProgress()
      ? getSectionUnits()
      : getChapters();
  }


  function getTotalStudyUnitCount() {
    return getStudyUnits().length;
  }


  function getCurrentStudyUnitCount(progress) {
    const unit = getProgressUnit(progress);

    if (!unit) {
      return 0;
    }

    const studyUnits = getStudyUnits();

    if (usesSectionProgress()) {
      const index = studyUnits.findIndex(
        item => String(item.number) === unit
      );

      return index >= 0 ? index + 1 : 0;
    }

    const chapterNumber = unit.split(".")[0];

    const index = studyUnits.findIndex(
      item => String(item.number) === chapterNumber
    );

    return index >= 0 ? index + 1 : 0;
  }


  function updateProgress(progress) {
    const parts = String(progress).split("/");

    if (parts.length !== 2) {
      progressText.textContent = progress;
      progressFill.style.width = "0%";
      return;
    }

    const currentCount = getCurrentStudyUnitCount(progress);
    const totalCount = getTotalStudyUnitCount();

    if (currentCount <= 0 || totalCount <= 0) {
      progressText.textContent = "-";
      progressFill.style.width = "0%";
      return;
    }

    const percent = (
      (currentCount / totalCount) * 100
    ).toFixed(1);

    progressText.textContent = `${percent}% (${progress})`;
    progressFill.style.width = `${percent}%`;
  }


  /* ---------------------------------------------------------
     Chapter Title
     --------------------------------------------------------- */

  function getChapterByNumber(number) {
    return getChapters().find(
      chapter => String(chapter.number) === String(number)
    ) || null;
  }


  function getSectionByNumber(chapter, number) {
    if (!chapter || !Array.isArray(chapter.sections)) {
      return null;
    }

    return chapter.sections.find(
      section => String(section.number) === String(number)
    ) || null;
  }


  function formatChapterTitle(chapter) {
    if (!chapter) {
      return "-";
    }

    const format = getChapterFormat();

    if (format === "classic") {
      return `제${chapter.number}장 ${chapter.title}`;
    }

    if (format === "physics") {
      return `Chapter ${chapter.number} ${chapter.title}`;
    }

    return `${chapter.number} ${chapter.title}`;
  }

  function formatGroupTitle(group) {
    if (!group) {
      return "";
    }

    if (group.type === "unit") {
      return `${group.number}단원 ${group.title}`.trim();
    }

    if (group.type === "part") {
      return `Part ${group.number} ${group.title}`.trim();
    }

    return `${group.number} ${group.title}`.trim();
  }

  function getChapterTitle(progress) {
    const unit = getProgressUnit(progress);

    if (!unit || !getChapters().length) {
      return "-";
    }

    const chapterNumber = unit.split(".")[0];
    const chapter = getChapterByNumber(chapterNumber);

    if (!chapter) {
      return "-";
    }

    const format = getChapterFormat();
    const chapterTitle = formatChapterTitle(chapter);
    const section = getSectionByNumber(chapter, unit);

    if (format === "simple") {
      return chapterTitle;
    }

    if (format === "classic") {
      const groupTitle = formatGroupTitle(chapter.group);

      if (!groupTitle) {
        return chapterTitle;
      }

      if (CHAPTER_TITLE_LAYOUT === "newline") {
        return `${groupTitle}\n${chapterTitle}`;
      }

      return `${groupTitle}${CHAPTER_SEPARATOR}${chapterTitle}`;
    }
    
    if (["campbell", "physics"].includes(format)) {
      const groupTitle = formatGroupTitle(chapter.group);
      const sectionTitle = section
        ? `${section.number} ${section.title}`
        : "";

      const firstLine = groupTitle
        ? `${groupTitle}${CHAPTER_SEPARATOR}${chapterTitle}`
        : chapterTitle;

      return sectionTitle
        ? `${firstLine}\n(${sectionTitle})`
        : firstLine;
    }

    if (!section) {
      return chapterTitle;
    }

    return (
      `${chapterTitle}${CHAPTER_SEPARATOR}`
      + `${section.number} ${section.title}`
    );
  }


  /* ---------------------------------------------------------
     Calendar
     --------------------------------------------------------- */

  function getKoreaToday() {
    const now = new Date();

    return new Intl.DateTimeFormat("en-ca", {
      timeZone: "Asia/Seoul",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).format(now);
  }


  function getElapsedDays(firstDate, lastDate) {
    const start = new Date(`${firstDate}T00:00:00`);
    const end = new Date(`${lastDate}T00:00:00`);
    const difference = end - start;

    if (!Number.isFinite(difference)) {
      return 0;
    }

    return Math.floor(
      difference / (1000 * 60 * 60 * 24)
    ) + 1;
  }


  function buildCalendar() {
    calendarGrid.innerHTML = "";

    calendarTitle.textContent =
      `${calendarYear}년 ${calendarMonth + 1}월`;

    const firstDay = new Date(
      calendarYear,
      calendarMonth,
      1
    );

    const lastDay = new Date(
      calendarYear,
      calendarMonth + 1,
      0
    );

    const startWeekday = firstDay.getDay();
    const lastDate = lastDay.getDate();

    for (let index = 0; index < startWeekday; index++) {
      const emptyCell = document.createElement("div");
      emptyCell.className = "calendar-day empty";
      calendarGrid.appendChild(emptyCell);
    }

    const today = getKoreaToday();

    for (let day = 1; day <= lastDate; day++) {
      const date = [
        calendarYear,
        String(calendarMonth + 1).padStart(2, "0"),
        String(day).padStart(2, "0")
      ].join("-");

      const cell = document.createElement("div");

      cell.className = "calendar-day";
      cell.dataset.date = date;
      cell.textContent = day;

      if (date === today) {
        cell.classList.add("today");
      }

      cell.addEventListener("click", () => {
        dateInput.value = date;
        loadStudyRecord(date);
        selectCalendarDay(date);
      });

      calendarGrid.appendChild(cell);
    }
  }


  function markRecordedDates() {
    if (!Array.isArray(studyIndex?.records)) {
      return;
    }

    studyIndex.records.forEach(record => {
      const cell = document.querySelector(
        `[data-date="${record.date}"]`
      );

      if (cell) {
        cell.classList.add("has-record");
      }
    });
  }


  function selectCalendarDay(date) {
    document
      .querySelectorAll(".calendar-day.selected")
      .forEach(cell => {
        cell.classList.remove("selected");
      });

    const selectedCell = document.querySelector(
      `[data-date="${date}"]`
    );

    if (selectedCell) {
      selectedCell.classList.add("selected");
    }
  }


  return {
    init
  };

})();


document.addEventListener(
  "DOMContentLoaded",
  StudyBoard.init
);
