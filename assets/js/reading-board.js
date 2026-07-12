"use strict";


/* =========================================================
   LOGIA Reading Board
   ========================================================= */

const ReadingBoard = (() => {

  let readingData = null;
  let books = [];
  let selectedBookId = null;

  const urlParams =
    new URLSearchParams(window.location.search);

  const requestedCategory =
    urlParams.get("category");

  let currentCategory =
    READING_CONFIG.categories?.[requestedCategory]
      ? requestedCategory
      : READING_CONFIG.defaultCategory || "science";

  let currentMediaPath = "";
  let loadRequestId = 0;


  /* ---------------------------------------------------------
     DOM
     --------------------------------------------------------- */

  const completedCount = document.getElementById("completed-count");
  const readingCount = document.getElementById("reading-count");

  const completedList = document.getElementById("completed-list");
  const readingList = document.getElementById("reading-list");

  const bookDetail = document.getElementById("book-detail");

  const searchForm = document.getElementById("search-form");
  const searchTitle = document.getElementById("search-title");
  const searchAuthor = document.getElementById("search-author");
  const searchDate = document.getElementById("search-date");
  const searchWord = document.getElementById("search-word");

  const searchReset = document.getElementById("search-reset");
  const searchStatus = document.getElementById("search-status");
  const searchCount = document.getElementById("search-count");
  const searchResults = document.getElementById("search-results");

  const categoryButtons = document.querySelectorAll(
    ".reading-category[data-category]"
  );
  const selectedCategory = document.getElementById(
    "selected-category"
  );


  /* ---------------------------------------------------------
     공통 유틸리티
     --------------------------------------------------------- */

  function normalizeText(value) {
    return String(value ?? "")
      .trim()
      .toLowerCase();
  }


  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }


  function joinText(value) {
    if (Array.isArray(value)) {
      return value.join("\n");
    }

    return String(value ?? "");
  }


  function formatDateRange(book) {
    const startDate = book.startDate || "";
    const finishDate = book.finishDate || "";

    if (startDate && finishDate) {
      return `${startDate} ~ ${finishDate}`;
    }

    if (startDate) {
      return `${startDate} ~ 읽는 중`;
    }

    return "-";
  }


  function getDisplayDate(book) {
    if (book.status === "completed") {
      return book.finishDate || book.startDate || "";
    }

    return book.startDate || "";
  }


  function getBookById(bookId) {
    return books.find(book => book.id === bookId) || null;
  }


  /* ---------------------------------------------------------
     데이터 불러오기
     --------------------------------------------------------- */

  async function loadReadingData(categoryKey = currentCategory) {

    const categoryConfig =
        READING_CONFIG.categories[categoryKey];

    if (!categoryConfig) {
        console.error(
        `Reading Category Error : ${categoryKey}`
        );
        return;
    }

    currentCategory = categoryKey;
    currentMediaPath = categoryConfig.mediaPath;

    try {

        const separator =
            categoryConfig.dataFile.includes("?")
                ? "&"
                : "?";

        const dataUrl =
            `${categoryConfig.dataFile}${separator}v=${Date.now()}`;

        const response = await fetch(
            dataUrl,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `Reading JSON을 불러오지 못했습니다. HTTP ${response.status}`
            );
        }

        readingData = await response.json();

        books = Array.isArray(readingData.books)
            ? readingData.books
            : [];

        selectedBookId = null;

        initializeBoard();

    }

    catch (error) {

        console.error(error);

        completedList.innerHTML = createErrorMessage(
        "완독 목록을 불러오지 못했습니다."
        );

        readingList.innerHTML = createErrorMessage(
        "읽는 중 목록을 불러오지 못했습니다."
        );

        searchResults.innerHTML = createErrorMessage(
        "검색 데이터를 불러오지 못했습니다."
        );

        bookDetail.innerHTML = createErrorMessage(
        "도서 정보를 불러오지 못했습니다."
        );

    }

  }

    function createErrorMessage(message) {
        return `
            <p class="empty-message">
            ${escapeHtml(message)}
            </p>
        `;
    }

    function updateCategoryButtons() {

        categoryButtons.forEach(button => {

            const active =
            button.dataset.category === currentCategory;

            button.classList.toggle(
            "active",
            active
            );

            button.setAttribute(
            "aria-selected",
            String(active)
            );

        });

        const categoryTitle =
            READING_CONFIG.categories[currentCategory]?.title
            || "";

        selectedCategory.textContent =
            categoryTitle
            ? `(${categoryTitle})`
            : "";

    }


    function handleCategoryChange(event) {

        const category =
            event.currentTarget.dataset.category;

        if (
            !category
            || category === currentCategory
        ) {
            return;
        }
        
        const newUrl =
          `${window.location.pathname}?category=${category}`;

        window.history.replaceState(
          null,
          "",
          newUrl
        );

        loadReadingData(category);
        updateCategoryButtons();

    }

    /* ---------------------------------------------------------
        초기 화면
        --------------------------------------------------------- */

    function initializeBoard() {
        renderCompletedBooks();
        renderReadingBooks();
        renderSearchResults(books, "전체 도서");

        const firstBook =
        getCompletedBooks()[0]
        || getReadingBooks()[0]
        || books[0]
        || null;

        if (firstBook) {
        selectBook(firstBook.id);
        } else {
        renderEmptyDetail();
        }
    }


  /* ---------------------------------------------------------
     도서 분류
     --------------------------------------------------------- */

  function getCompletedBooks() {
    return books
      .filter(book => book.status === "completed")
      .sort((a, b) => {
        const dateA = a.finishDate || "";
        const dateB = b.finishDate || "";

        return dateB.localeCompare(dateA);
      });
  }


  function getReadingBooks() {
    return books
      .filter(book => book.status === "reading")
      .sort((a, b) => {
        const dateA = a.startDate || "";
        const dateB = b.startDate || "";

        return dateB.localeCompare(dateA);
      });
  }


  /* ---------------------------------------------------------
     완독 목록
     --------------------------------------------------------- */

  function renderCompletedBooks() {
    const completedBooks = getCompletedBooks();

    completedCount.textContent = `${completedBooks.length}권`;

    if (completedBooks.length === 0) {
      completedList.innerHTML = `
        <p class="empty-message">
          완독한 책이 없습니다.
        </p>
      `;

      return;
    }

    completedList.innerHTML = completedBooks
      .map(book => createBookListButton(book))
      .join("");

    bindBookButtons(completedList);
  }


  /* ---------------------------------------------------------
     읽는 중 목록
     --------------------------------------------------------- */

  function renderReadingBooks() {
    const readingBooks = getReadingBooks();

    readingCount.textContent = `${readingBooks.length}권`;

    if (readingBooks.length === 0) {
      readingList.innerHTML = `
        <p class="empty-message">
          현재 읽고 있는 책이 없습니다.
        </p>
      `;

      return;
    }

    readingList.innerHTML = readingBooks
      .map(book => createBookListButton(book))
      .join("");

    bindBookButtons(readingList);
  }


  function createBookListButton(book) {
    const selectedClass =
      book.id === selectedBookId
        ? " selected"
        : "";

    return `
      <button
        type="button"
        class="book-item${selectedClass}"
        data-book-id="${escapeHtml(book.id)}"
      >
        <span class="book-item-date">
          ${escapeHtml(getDisplayDate(book))}
        </span>

        <span class="book-item-title">
          ${escapeHtml(book.title || "제목 없음")}
        </span>
      </button>
    `;
  }


  function bindBookButtons(container) {
    const buttons = container.querySelectorAll(
      "[data-book-id]"
    );

    buttons.forEach(button => {
      button.addEventListener("click", () => {
        selectBook(button.dataset.bookId);
      });
    });
  }


  /* ---------------------------------------------------------
     도서 선택
     --------------------------------------------------------- */

  function selectBook(bookId) {
    const book = getBookById(bookId);

    if (!book) {
      return;
    }

    selectedBookId = book.id;

    renderBookDetail(book);
    updateSelectedBookStyles();
  }


  function updateSelectedBookStyles() {
    const buttons = document.querySelectorAll(
      "[data-book-id]"
    );

    buttons.forEach(button => {
      const isSelected =
        button.dataset.bookId === selectedBookId;

      button.classList.toggle(
        "selected",
        isSelected
      );
    });
  }


  /* ---------------------------------------------------------
     상세 정보
     --------------------------------------------------------- */

  function renderBookDetail(book) {
    const keywords = Array.isArray(book.keywords)
      ? book.keywords
      : [];

    const summary = joinText(book.summary);
    const reflection = joinText(book.reflection);

    bookDetail.innerHTML = `
      <dl class="book-meta">

        <dt>제목</dt>
        <dd>
          ${escapeHtml(book.title || "-")}
        </dd>

        <dt>저자</dt>
        <dd>
          ${escapeHtml(book.author || "-")}
        </dd>

        <dt>독서 기간</dt>
        <dd>
          ${escapeHtml(formatDateRange(book))}
        </dd>

        <dt>상태</dt>
        <dd>
          ${
            book.status === "completed"
              ? "완독"
              : "읽는 중"
          }
        </dd>

        <dt>분야</dt>
        <dd>
          ${escapeHtml(book.category || "-")}
        </dd>

        <dt>키워드</dt>
        <dd>
          ${createKeywordMarkup(keywords)}
        </dd>

      </dl>

      <section class="book-section">
        <h3>내용</h3>

        ${createParagraphMarkup(
          summary,
          "등록된 내용이 없습니다."
        )}
      </section>

      <section class="book-section">
        <h3>감상</h3>

        ${createParagraphMarkup(
          reflection,
          "등록된 감상이 없습니다."
        )}
      </section>

      <section class="book-section">
        <h3>첨부 자료</h3>

        ${createMediaMarkup(book.media)}
      </section>
    `;
  }


  function renderEmptyDetail() {
    bookDetail.innerHTML = `
      <p class="empty-message">
        목록 또는 검색 결과에서 도서를 선택해 주세요.
      </p>
    `;
  }


  function createKeywordMarkup(keywords) {
    if (keywords.length === 0) {
      return "-";
    }

    return `
      <div class="book-keywords">
        ${keywords
          .map(keyword => `
            <span class="book-keyword">
              ${escapeHtml(keyword)}
            </span>
          `)
          .join("")}
      </div>
    `;
  }


  function createParagraphMarkup(text, emptyMessage) {
    const trimmedText = String(text ?? "").trim();

    if (!trimmedText) {
      return `
        <p class="empty-message">
          ${escapeHtml(emptyMessage)}
        </p>
      `;
    }

    return trimmedText
      .split("\n")
      .filter(line => line.trim())
      .map(line => `
        <p>
          ${escapeHtml(line)}
        </p>
      `)
      .join("");
  }


  function createMediaMarkup(mediaItems) {
    if (
      !Array.isArray(mediaItems)
      || mediaItems.length === 0
    ) {
      return `
        <p class="empty-message">
          첨부 자료가 없습니다.
        </p>
      `;
    }

    return mediaItems
      .map(item => {
        const filename = item.file || "";
        const title = item.title || filename;

        if (!item.exists) {
          return `
            <p>
              ${escapeHtml(title)}
              <span class="empty-message">
                (파일 없음)
              </span>
            </p>
          `;
        }

        const encodedFilename = encodeURIComponent(filename);

        return `
          <p>
            <a
              class="book-media-link"
              href="${currentMediaPath}${encodedFilename}"
              target="_blank"
              rel="noopener noreferrer"
            >
              ${escapeHtml(title)}
            </a>
          </p>
        `;
      })
      .join("");
  }


  /* ---------------------------------------------------------
     검색
     --------------------------------------------------------- */

  function handleSearch(event) {
    event.preventDefault();

    const titleQuery = normalizeText(
      searchTitle.value
    );

    const authorQuery = normalizeText(
      searchAuthor.value
    );

    const dateQuery = normalizeText(
      searchDate.value
    );

    const wordQuery = normalizeText(
      searchWord.value
    );

    const hasSearchQuery =
      titleQuery
      || authorQuery
      || dateQuery
      || wordQuery;

    if (!hasSearchQuery) {
      renderSearchResults(
        books,
        "전체 도서"
      );

      return;
    }

    const matchedBooks = books.filter(book => {
      const title = normalizeText(book.title);
      const author = normalizeText(book.author);

      const dateText = normalizeText([
        book.date,
        book.startDate,
        book.finishDate
      ].filter(Boolean).join(" "));

      const wordText = normalizeText([
        book.title,
        book.author,
        book.category,
        ...(book.keywords || []),
        ...toArray(book.summary),
        ...toArray(book.reflection)
      ].join(" "));

      return (
        title.includes(titleQuery)
        && author.includes(authorQuery)
        && dateText.includes(dateQuery)
        && wordText.includes(wordQuery)
      );
    });

    renderSearchResults(
      matchedBooks,
      "검색 결과"
    );
  }


  function toArray(value) {
    if (Array.isArray(value)) {
      return value;
    }

    if (value === null || value === undefined) {
      return [];
    }

    return [String(value)];
  }


  function resetSearch() {
    searchForm.reset();

    renderSearchResults(
      books,
      "전체 도서"
    );

    searchTitle.focus();
  }


  /* ---------------------------------------------------------
     검색 결과
     --------------------------------------------------------- */

  function renderSearchResults(
    resultBooks,
    statusText
  ) {
    const sortedBooks = [...resultBooks]
      .sort((a, b) => {
        const dateA =
          a.finishDate
          || a.startDate
          || "";

        const dateB =
          b.finishDate
          || b.startDate
          || "";

        return dateB.localeCompare(dateA);
      });

    searchStatus.textContent = statusText;
    searchCount.textContent = `${sortedBooks.length}권`;

    if (sortedBooks.length === 0) {
      searchResults.innerHTML = `
        <p class="empty-message">
          조건에 맞는 도서가 없습니다.
        </p>
      `;

      return;
    }

    searchResults.innerHTML = sortedBooks
      .map(book => {
        const selectedClass =
          book.id === selectedBookId
            ? " selected"
            : "";

        return `
          <button
            type="button"
            class="search-result-item${selectedClass}"
            data-book-id="${escapeHtml(book.id)}"
          >
            <span class="search-result-date">
              ${escapeHtml(getDisplayDate(book))}
            </span>

            <span class="search-result-title">
              ${escapeHtml(book.title || "제목 없음")}
            </span>

            <span class="search-result-author">
              ${escapeHtml(book.author || "저자 없음")}
            </span>
          </button>
        `;
      })
      .join("");

    bindBookButtons(searchResults);
    updateSelectedBookStyles();
  }


  /* ---------------------------------------------------------
     이벤트
     --------------------------------------------------------- */

  function bindEvents() {
    searchForm.addEventListener(
      "submit",
      handleSearch
    );

    searchReset.addEventListener(
      "click",
      resetSearch
    );

    categoryButtons.forEach(button => {

        button.addEventListener(
        "click",
        handleCategoryChange
        );

    });

  }


  /* ---------------------------------------------------------
     실행
     --------------------------------------------------------- */

    function init() {

        bindEvents();

        updateCategoryButtons();

        loadReadingData(currentCategory);

    }


  return {
    init
  };

})();


document.addEventListener(
  "DOMContentLoaded",
  ReadingBoard.init
);