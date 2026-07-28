"use strict";


/* =========================================================
   LOGIA Subject Page
   ========================================================= */

const SubjectPage = (() => {

  const urlParams = new URLSearchParams(
    window.location.search
  );

  const subjectKey = String(
    urlParams.get("subject") || ""
  ).trim();

  const validSubjectKey = /^[a-z0-9-]+$/;

  let subjectInfo = null;
  let chapterIndex = null;
  let currentView = (
    urlParams.get("view") === "board"
      ? "board"
      : "introduction"
  );


  /* ---------------------------------------------------------
     DOM
     --------------------------------------------------------- */

  const viewButtons = document.querySelectorAll(
    ".subject-category[data-subject-view]"
  );

  const introductionView = document.getElementById(
    "subject-introduction-view"
  );

  const boardView = document.getElementById(
    "subject-board-view"
  );

  const subjectTabTitle = document.getElementById(
    "subject-tab-title"
  );

  const subjectTabSubtitle = document.getElementById(
    "subject-tab-subtitle"
  );

  const subjectTitle = document.getElementById(
    "subject-title"
  );

  const subjectEnglishTitle = document.getElementById(
    "subject-english-title"
  );

  const subjectDescription = document.getElementById(
    "subject-description"
  );

  const subjectOverview = document.getElementById(
    "subject-overview"
  );

  const subjectObjectivesSection = document.getElementById(
    "subject-objectives-section"
  );

  const subjectObjectives = document.getElementById(
    "subject-objectives"
  );

  const subjectResourcesSection = document.getElementById(
    "subject-resources-section"
  );

  const subjectResources = document.getElementById(
    "subject-resources"
  );

  const subjectBibliographySection = document.getElementById(
    "subject-bibliography-section"
  );

  const subjectBibliography = document.getElementById(
    "subject-bibliography"
  );

  const subjectChapterCount = document.getElementById(
    "subject-chapter-count"
  );

  const subjectChapterList = document.getElementById(
    "subject-chapter-list"
  );

  const boardHeading = document.getElementById(
    "board-heading"
  );


  /* ---------------------------------------------------------
     Utilities
     --------------------------------------------------------- */

  function toArray(value) {
    if (Array.isArray(value)) {
      return value;
    }

    if (value === null || value === undefined) {
      return [];
    }

    return [value];
  }


  function createTextElement(tagName, text, className = "") {
    const element = document.createElement(tagName);

    if (className) {
      element.className = className;
    }

    element.textContent = String(text ?? "");

    return element;
  }


  function createErrorMessage(message) {
    const paragraph = createTextElement(
      "p",
      message,
      "empty-message"
    );

    return paragraph;
  }


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


  function getTextbookText(textbook) {
    if (!textbook) {
      return "-";
    }

    if (typeof textbook === "string") {
      return textbook;
    }

    const parts = [
      textbook.author,
      textbook.title,
      textbook.edition
    ].filter(Boolean);

    return parts.length ? parts.join(", ") : "-";
  }


  function getKeyTopicsText(value) {
    const topics = toArray(value)
      .map(item => String(item).trim())
      .filter(Boolean);

    return topics.length ? topics.join(", ") : "-";
  }


  /* ---------------------------------------------------------
     View Tabs
     --------------------------------------------------------- */

  function updateViewButtons() {
    viewButtons.forEach(button => {
      const active =
        button.dataset.subjectView === currentView;

      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });

    introductionView.hidden = currentView !== "introduction";
    boardView.hidden = currentView !== "board";
  }


  function updateViewUrl() {
    const params = new URLSearchParams(
      window.location.search
    );

    if (currentView === "board") {
      params.set("view", "board");
    } else {
      params.delete("view");
    }

    const query = params.toString();
    const nextUrl = query
      ? `${window.location.pathname}?${query}`
      : window.location.pathname;

    window.history.replaceState(
      { subjectView: currentView },
      "",
      nextUrl
    );
  }


  function selectView(viewName, updateUrl = true) {
    if (!['introduction', 'board'].includes(viewName)) {
      return;
    }

    currentView = viewName;
    updateViewButtons();

    if (updateUrl) {
      updateViewUrl();
    }
  }


  function bindViewEvents() {
    viewButtons.forEach(button => {
      button.addEventListener("click", () => {
        selectView(button.dataset.subjectView);
      });
    });

    window.addEventListener("popstate", () => {
      const params = new URLSearchParams(
        window.location.search
      );

      selectView(
        params.get("view") === "board"
          ? "board"
          : "introduction",
        false
      );
    });
  }


  /* ---------------------------------------------------------
     Subject Information
     --------------------------------------------------------- */

  function renderDescription() {
    subjectDescription.innerHTML = "";

    const lines = toArray(subjectInfo.description)
      .map(line => String(line).trim())
      .filter(Boolean);

    if (!lines.length) {
      subjectDescription.appendChild(
        createErrorMessage("등록된 과목 설명이 없습니다.")
      );
      return;
    }

    const paragraph = document.createElement("p");

    lines.forEach((line, index) => {
      if (index > 0) {
        paragraph.appendChild(document.createElement("br"));
      }

      paragraph.appendChild(
        document.createTextNode(line.replaceAll("\\n", "\n"))
      );
    });

    subjectDescription.appendChild(paragraph);
  }


  function appendOverviewRow(label, value) {
    const dt = createTextElement("dt", label);
    const dd = createTextElement("dd", value || "-");

    subjectOverview.append(dt, dd);
  }


  function renderOverview() {
    subjectOverview.innerHTML = "";

    appendOverviewRow(
      "과목명",
      subjectInfo.title
    );

    appendOverviewRow(
      "분야",
      subjectInfo.field
    );

    appendOverviewRow(
      "핵심 주제",
      getKeyTopicsText(subjectInfo.keyTopics)
    );

    appendOverviewRow(
      "목표",
      subjectInfo.goal
    );

    appendOverviewRow(
      "교재",
      getTextbookText(subjectInfo.textbook)
    );
  }


  function renderTextList(container, values, ordered = false) {
    container.innerHTML = "";

    const items = toArray(values)
      .map(value => String(value).trim())
      .filter(Boolean);

    if (!items.length) {
      return false;
    }

    items.forEach(value => {
      const item = createTextElement(
        "li",
        value.replaceAll("\\n", "\n")
      );

      item.style.whiteSpace = "pre-line";
      container.appendChild(item);
    });

    return true;
  }


  function renderResources() {
    subjectResources.innerHTML = "";

    const resources = toArray(subjectInfo.resources)
      .filter(Boolean);

    if (!resources.length) {
      subjectResourcesSection.hidden = true;
      return;
    }

    subjectResourcesSection.hidden = false;

    resources.forEach(resource => {
      const item = document.createElement("li");

      if (
        resource
        && typeof resource === "object"
        && resource.url
      ) {
        const link = createTextElement(
          "a",
          resource.title || resource.url
        );

        link.href = resource.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";

        item.appendChild(link);
      } else {
        item.textContent = String(resource);
      }

      subjectResources.appendChild(item);
    });
  }


  function renderSubjectInformation() {
    const title = subjectInfo.title || subjectKey;
    const englishTitle = subjectInfo.englishTitle || "";

    document.title = `${title} - LOGIA School`;

    subjectTabTitle.textContent = title;
    subjectTabSubtitle.textContent =
      englishTitle || "Subject Introduction";

    subjectTitle.textContent = title;
    subjectEnglishTitle.textContent = englishTitle;
    subjectEnglishTitle.hidden = !englishTitle;

    boardHeading.textContent = `${title} <학습 보드>`;

    renderDescription();
    renderOverview();

    subjectObjectivesSection.hidden = !renderTextList(
      subjectObjectives,
      subjectInfo.objectives,
      true
    );

    renderResources();

    subjectBibliographySection.hidden = !renderTextList(
      subjectBibliography,
      subjectInfo.bibliography
    );
  }


  /* ---------------------------------------------------------
     Chapters
     --------------------------------------------------------- */

  function renderChapters() {
    const chapters = Array.isArray(chapterIndex?.chapters)
      ? chapterIndex.chapters
      : [];

    subjectChapterCount.textContent =
      `${chapters.length}개 단원`;

    subjectChapterList.innerHTML = "";

    if (!chapters.length) {
      subjectChapterList.appendChild(
        createErrorMessage("등록된 단원 구성이 없습니다.")
      );
      return;
    }

    const list = document.createElement("ol");
    list.className = "chapter-list-items";

    chapters.forEach(chapter => {
      const item = document.createElement("li");

      const number = createTextElement(
        "span",
        chapter.number || "",
        "chapter-number"
      );

      const title = createTextElement(
        "span",
        chapter.title || "제목 없음",
        "chapter-title"
      );

      item.append(number, title);
      list.appendChild(item);
    });

    subjectChapterList.appendChild(list);
  }


  /* ---------------------------------------------------------
     Loading
     --------------------------------------------------------- */

  async function loadSubjectData() {
    if (!subjectKey || !validSubjectKey.test(subjectKey)) {
      throw new Error("올바른 subject 주소가 아닙니다.");
    }

    const indexFile =
      `${subjectKey}/${subjectKey}-index.json`;

    const chapterFile =
      `${subjectKey}/${subjectKey}-chapters.json`;

    const [studyIndex, loadedChapterIndex] =
      await Promise.all([
        fetchJsonNoCache(indexFile),
        fetchJsonNoCache(chapterFile)
      ]);

    subjectInfo = studyIndex?.subjectInfo || null;
    chapterIndex = loadedChapterIndex;

    if (!subjectInfo) {
      throw new Error(
        `${subjectKey}-subject.txt가 아직 인덱스에 포함되지 않았습니다.`
      );
    }
  }


  function renderLoadError(error) {
    console.error(error);

    subjectTitle.textContent = "교과목 정보를 불러오지 못했습니다.";
    subjectEnglishTitle.hidden = true;

    subjectDescription.innerHTML = "";
    subjectDescription.appendChild(
      createErrorMessage(error.message || "데이터 로딩 오류")
    );

    subjectOverview.innerHTML = "";
    subjectObjectivesSection.hidden = true;
    subjectResourcesSection.hidden = true;
    subjectBibliographySection.hidden = true;

    subjectChapterList.innerHTML = "";
    subjectChapterList.appendChild(
      createErrorMessage("단원 정보를 표시할 수 없습니다.")
    );
  }


  async function init() {
    bindViewEvents();
    updateViewButtons();

    try {
      await loadSubjectData();
      renderSubjectInformation();
      renderChapters();
    } catch (error) {
      renderLoadError(error);
    }
  }


  return {
    init
  };

})();


document.addEventListener(
  "DOMContentLoaded",
  SubjectPage.init
);
