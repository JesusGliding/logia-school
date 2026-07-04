  const SUBJECT = BOARD_CONFIG.subject;  // 과목명 
  const START_DATE = BOARD_CONFIG.startDate;  // 학습 시작일
  const INDEX_FILE = `${SUBJECT}-index.json`; // 학습 데이터 (JSON)
  let studyIndex = null;
  const CHAPTER_FILE = `${SUBJECT}-chapters.txt`; // 챕터 데이터 (txt)
  let chapterList = [];  
  const CHAPTER_FORMAT = SUBJECT === "biology" ? "campbell" : "standard"; // 챕터 형식 (campbell or standard)
  const CHAPTER_SEPARATOR = BOARD_CONFIG.separator ?? " | "; // 챕터 제목 구분자 (기본값: " | ")

  const calendarTitle = document.getElementById("calendar-title");
  const calendarGrid = document.getElementById("calendar-grid");
  const prevMonthButton = document.getElementById("prev-month");
  const nextMonthButton = document.getElementById("next-month");
  let calendarYear = null;
  let calendarMonth = null;

  const dateInput = document.getElementById("study-date");
  const memoText = document.getElementById("memo-text");
  const progressText = document.getElementById("progress-text");
  const progressFill = document.getElementById("progress-fill");
  const filesList = document.getElementById("files-list");
  const startDateText = document.getElementById("start-date");
  const elapsedText = document.getElementById("elapsed-text");
  const studytimeText = document.getElementById("studytime-text");
  const recentDateText = document.getElementById("recent-date");
  const studyDaysText = document.getElementById("study-days-text");
  const chapterText = document.getElementById("chapter-text");

  init();

  async function init() {

    const TODAY = getKoreaToday();

    startDateText.textContent = START_DATE;
    dateInput.value = TODAY;
    elapsedText.textContent = `(${getElapsedDays(START_DATE, TODAY)}일 경과)`;

    await loadChapterList();  
    await loadStudyIndex();

    dateInput.addEventListener("change", function () {
        loadStudyRecord(dateInput.value);
        selectCalendarDay(dateInput.value);
    });

    prevMonthButton.addEventListener("click", function () {
      calendarMonth--;

      if (calendarMonth < 0) {
        calendarMonth = 11;
        calendarYear--;
      }

      buildCalendar();
      markRecordedDates();
      selectCalendarDay(dateInput.value);
    });

    nextMonthButton.addEventListener("click", function () {
      calendarMonth++;

      if (calendarMonth > 11) {
        calendarMonth = 0;
        calendarYear++;
      }

      buildCalendar();
      markRecordedDates();
      selectCalendarDay(dateInput.value);
    });
  }

  async function loadStudyIndex() {
    const response = await fetch(INDEX_FILE, {cache: "no-cache"});

    if (!response.ok) {
      throw new Error("index json not found");
    }

    studyIndex = await response.json();

    recentDateText.textContent = studyIndex.lastRecord || "-";
    studyDaysText.textContent = studyIndex.studyDays
      ? `(학습일 ${studyIndex.studyDays}일)`
      : "";

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

  function loadStudyRecord(date) {
    if (!studyIndex || !studyIndex.records) {
      memoText.value = "학습 데이터베이스를 불러오지 못했습니다.";
      updateProgress("-");
      studytimeText.textContent = "-";
      filesList.innerHTML = "";
      return;
    }

    const record = studyIndex.records.find(item => item.date === date);

    if (!record) {
      memoText.value = "이 날짜에는 학습 기록이 없습니다.";
      updateProgress("-");
      studytimeText.textContent = "-";
      chapterText.textContent = "-";
      filesList.innerHTML = "";
      return;
    }

    memoText.value = record.memo && record.memo.length > 0
      ? record.memo.join("\n")
      : "메모가 없습니다.";

    updateProgress(record.progress || "-");
    chapterText.textContent = getChapterTitle(record.progress);

    studytimeText.textContent = record.studytime || "-";

    filesList.innerHTML = "";

    if (record.media && record.media.length > 0) {
      record.media.forEach(media => {
        const li = document.createElement("li");

        const link = document.createElement("a");
        link.href = `media/${media.file}`;
        link.target = "_blank";
        link.textContent = media.title || media.file;

        li.appendChild(link);
        filesList.appendChild(li);
      });
    }
  }

  function getKoreaToday() {
      const now = new Date();
     
      return new Intl.DateTimeFormat("en-ca", {
          timeZone: "Asia/Seoul",
          year: "numeric",
          month: "2-digit",
          day: "2-digit"
      }).format(now);
  }

  function getElapsedDays(startDate, endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const diff = end - start;

      return Math.floor(diff / (1000 * 60 * 60 * 24)) + 1;
  }

  function updateProgress(progress) {
    const parts = progress.split("/");

    if (parts.length !== 2) {
      progressText.textContent = progress;
      progressFill.style.width = "0%";
      return;
    }

    const currentText = parts[0].trim();
    const total = Number(parts[1].trim());

    const currentParts = currentText.split(".");
    let currentValue = Number(currentText);

    if (currentParts.length === 2) {
      const chapter = Number(currentParts[0]);
      const sectionText = currentParts[1];
      const section = Number(sectionText);

      if (!isNaN(chapter) && !isNaN(section) && section >= 10) {
        currentValue = chapter + 0.99;
      }
    }

    if (isNaN(currentValue) || isNaN(total) || total <= 0) {
      progressText.textContent = "-";
      progressFill.style.width = "0%";
      return;
    }

    const percent = ((currentValue / (total + 1)) * 100).toFixed(1); // chapter.section/chapter+1

    progressText.textContent = `${percent}% (${progress})`;
    progressFill.style.width = percent + "%";
  }

  function markRecordedDates() {
    if (!studyIndex || !studyIndex.records) return;

    studyIndex.records.forEach(record => {
      const cell = document.querySelector(`[data-date="${record.date}"]`);
      if (cell) {
        cell.classList.add("has-record");
      }
    });
  }

  function buildCalendar() {
    calendarGrid.innerHTML = "";

    calendarTitle.textContent = `${calendarYear}년 ${calendarMonth + 1}월`;

    const firstDay = new Date(calendarYear, calendarMonth, 1);
    const lastDay = new Date(calendarYear, calendarMonth + 1, 0);

    const startWeekday = firstDay.getDay();
    const lastDate = lastDay.getDate();

    for (let i = 0; i < startWeekday; i++) {
      const empty = document.createElement("div");
      empty.className = "calendar-day empty";
      calendarGrid.appendChild(empty);
    }

    const today = getKoreaToday();

    for (let day = 1; day <= lastDate; day++) {
      const date = `${calendarYear}-${String(calendarMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

      const cell = document.createElement("div");
      cell.className = "calendar-day";
      cell.dataset.date = date;
      cell.textContent = day;

      if (date === today) {
        cell.classList.add("today");
      }

      cell.addEventListener("click", function () {
        dateInput.value = date;
        loadStudyRecord(date);
        selectCalendarDay(date);
      });

      calendarGrid.appendChild(cell);
    }
  }

  function selectCalendarDay(date) {
    document.querySelectorAll(".calendar-day.selected").forEach(cell => {
      cell.classList.remove("selected");
    });

    const selectedCell = document.querySelector(`[data-date="${date}"]`);

    if (selectedCell) {
      selectedCell.classList.add("selected");
    }
  }

  async function loadChapterList() {
    const response = await fetch(CHAPTER_FILE, {cache: "no-cache"});

    if (!response.ok) {
      chapterList = [];
      return;
    }

    const text = await response.text();
    
    chapterList = text
      .split("\n")
      .map(line => line.trim())
      .filter(line => line !== "");
  }

  function getProgressUnit(progress) {
    return String(progress).split("/")[0].trim();
  }

  function getStandardChapterTitle(progress) {
    if (!progress || !chapterList.length) return "-";

    const unit = getProgressUnit(progress);
    const mainNumber = unit.split(".")[0];

    const mainTitle = chapterList.find(line => 
      line.startsWith(mainNumber + " ")
    );
     
    const subTitle = chapterList.find(line => 
      line.startsWith(unit + " ")
    );

    if (!mainTitle || !subTitle) return "-";

    return `${mainTitle}${CHAPTER_SEPARATOR}${subTitle}`;
  }

  function getChapterTitle(progress) {
    if (CHAPTER_FORMAT === "campbell") {
      return getCampbellChapterTitle(progress);
    } else {
      return getStandardChapterTitle(progress);
    }
  }

  function getCampbellChapterTitle(progress) {
    if (!progress || !chapterList.length) return "-";

    const unit = getProgressUnit(progress);
    const detailIndex = chapterList.findIndex(line =>
      line.startsWith(unit + " ")
    );

    if (detailIndex === -1) return "-";

    const detailTitle = chapterList[detailIndex];
    const mainNumber = unit.split(".")[0];

    let chapterTitle = "";
    let partTitle = "";

    for (let i = detailIndex - 1; i >= 0; i--) {
      const line = chapterList[i];

      if (!chapterTitle && line.startsWith(mainNumber + " ")) {
        chapterTitle = line;
      }

      if (/^\d+단원\s+/.test(line)) {
        partTitle = line;
        break;
      }
    }

    if (!chapterTitle) return detailTitle;

    if (!partTitle) {
      return `${chapterTitle}\n(${detailTitle})`;
    }

    return `${partTitle} | ${chapterTitle}\n(${detailTitle})`;
}