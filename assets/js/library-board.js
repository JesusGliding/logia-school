"use strict";


/* =========================================================
   LOGIA Library Board - Initial Draft
   ========================================================= */

const LibraryBoard = (() => {

  let currentCategory =
    LIBRARY_CONFIG.defaultCategory || "science-history";

  let timeline = [];
  let archives = [];

  let recommendationPool = [];
  let recommendationPoolLoaded = false; 
  const RECOMMENDATION_CATEGORIES = [
    "science-history",
    "math-history",
    "philosophy-history",
    "computer"
  ];

  let selectedTimelineIndex = 0;
  let selectedArchiveId = null;
  let currentMediaPath = "";


  /* ---------------------------------------------------------
     DOM
     --------------------------------------------------------- */

  const categoryButtons = document.querySelectorAll(
    ".library-category[data-category]"
  );

  const timelineTitle =
    document.getElementById("timeline-title");

  const timelineCount =
    document.getElementById("timeline-count");

  const timelineList =
    document.getElementById("timeline-list");

  const selectedCategory =
    document.getElementById("selected-category");

  const archiveDetail =
    document.getElementById("archive-detail");

  const archiveSearchTitle =
    document.getElementById("archive-search-title");

  const timelineSearchForm =
    document.getElementById("timeline-search-form");

  const timelineSearchWord =
    document.getElementById("timeline-search-word");

  const timelineSearchReset =
    document.getElementById("timeline-search-reset");

  const timelineSearchMessage =
    document.getElementById("timeline-search-message");

  const archiveSearchForm =
    document.getElementById("archive-search-form");

  const archiveSearchName =
    document.getElementById("archive-search-name");

  const archiveSearchType =
    document.getElementById("archive-search-type");

  const archiveSearchField =
    document.getElementById("archive-search-field");

  const archiveSearchWord =
    document.getElementById("archive-search-word");

  const archiveSearchReset =
    document.getElementById("archive-search-reset");

  const archiveSearchStatus =
    document.getElementById("archive-search-status");

  const archiveSearchCount =
    document.getElementById("archive-search-count");

  const archiveSearchResults =
    document.getElementById("archive-search-results");


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


  function toArray(value) {
    if (Array.isArray(value)) {
      return value;
    }

    if (value === null || value === undefined) {
      return [];
    }

    return [String(value)];
  }


  function formatYear(year) {
    const numericYear = Number(year);

    if (!Number.isFinite(numericYear)) {
      return String(year ?? "-");
    }

    if (numericYear < 0) {
      return `BC ${Math.abs(numericYear)}`;
    }

    return String(numericYear);
  }


  function getTypeLabel(type) {
    const labels = {
      person: "인물",
      organization: "조직",
      machine: "기계",
      theory: "이론",
      language: "언어",
      software: "소프트웨어",
      concept: "개념",
      event: "사건",
      document: "문서",
      note: "노트"
    };

    return labels[type] || type || "-";
  }


  function isComputerCategory() {
    return currentCategory === "computer";
  }


  function isComputerItem(item) {
    return Boolean(
      item
      && (
        isComputerCategory()
        || Object.prototype.hasOwnProperty.call(item, "title")
        || Object.prototype.hasOwnProperty.call(item, "english")
        || Object.prototype.hasOwnProperty.call(item, "aliases")
      )
    );
  }


  function getArchiveById(id) {
    return archives.find(item => item.id === id) || null;
  }

  function getIndexFile(category) {

    return `${category}/${category}-index.json`;
    
  }

  function getRecordsFromIndex(category, data) {
    const sourceItems =
      category === "computer"
        ? data.records
        : data.archives;

    if (!Array.isArray(sourceItems)) {
      return [];
    }

    return sourceItems.map(item => ({
      ...item,
      libraryCategory: category
    }));
  }


  async function loadRecommendationPool() {
    if (recommendationPoolLoaded) {
      return;
    }

    const results = await Promise.allSettled(
      RECOMMENDATION_CATEGORIES.map(
        async category => {
          const dataUrl =
            `${getIndexFile(category)}?v=${Date.now()}`;

          const response = await fetch(dataUrl, {
            cache: "no-store"
          });

          if (!response.ok) {
            throw new Error(
              `${category} 추천 데이터 로딩 실패: `
              + `HTTP ${response.status}`
            );
          }

          const data = await response.json();

          return getRecordsFromIndex(
            category,
            data
          );
        }
      )
    );

    recommendationPool = results
      .filter(result =>
        result.status === "fulfilled"
      )
      .flatMap(result =>
        result.value
      );

    recommendationPoolLoaded = true;

    const failedResults = results.filter(
      result => result.status === "rejected"
    );

    failedResults.forEach(result => {
      console.warn(result.reason);
    });
  }

  function getItemTitle(item) {
    return (
      item.title
      || item.korean
      || item.name
      || item.english
      || item.id
      || "이름 없는 자료"
    );
  }


  function normalizeValueArray(value) {
    return toArray(value)
      .map(item => normalizeText(item))
      .filter(Boolean);
  }


  function getCommonValues(firstValues, secondValues) {
    const firstSet =
      new Set(normalizeValueArray(firstValues));

    return normalizeValueArray(secondValues)
      .filter(value => firstSet.has(value));
  }


  function getItemBodyText(item) {
    return normalizeText([
      item.id,
      item.title,
      item.korean,
      item.name,
      item.english,
      item.country,
      item.years,

      ...toArray(item.aliases),
      ...toArray(item.fields),
      ...toArray(item.keywords),
      ...toArray(item.summary),
      ...toArray(item.achievements),
      ...toArray(item.content)
    ].join(" "));
  }

  function calculateRecommendationScore(
    currentItem,
    candidateItem
  ) {
    let score = 0;
    const reasons = [];

    const currentRelated =
      normalizeValueArray(currentItem.related);

    const candidateRelated =
      normalizeValueArray(candidateItem.related);

    const currentId =
      normalizeText(currentItem.id);

    const candidateId =
      normalizeText(candidateItem.id);

    /*
    * 명시적인 related 연결
    */
    if (currentRelated.includes(candidateId)) {
      score += 100;
      reasons.push("직접 관련 자료");
    }

    if (candidateRelated.includes(currentId)) {
      score += 80;
      reasons.push("상호 연관 자료");
    }

    /*
    * 키워드 일치
    */
    const commonKeywords =
      getCommonValues(
        currentItem.keywords,
        candidateItem.keywords
      );

    if (commonKeywords.length) {
      score += commonKeywords.length * 24;

      reasons.push(
        `공통 키워드 ${commonKeywords
          .slice(0, 3)
          .join(" · ")}`
      );
    }

    /*
    * 분야 일치
    */
    const commonFields =
      getCommonValues(
        currentItem.fields,
        candidateItem.fields
      );

    if (commonFields.length) {
      score += commonFields.length * 14;

      reasons.push(
        `공통 분야 ${commonFields
          .slice(0, 2)
          .join(" · ")}`
      );
    }

    /*
    * 자료 유형 일치
    */
    if (
      currentItem.type
      && candidateItem.type
      && normalizeText(currentItem.type)
        === normalizeText(candidateItem.type)
    ) {
      score += 5;
    }

    /*
    * 같은 Library 카테고리
    */
    if (
      currentItem.libraryCategory
      === candidateItem.libraryCategory
    ) {
      score += 3;
    }

    /*
    * 현재 자료 키워드가 상대 자료 본문에 등장
    */
    const candidateBody =
      getItemBodyText(candidateItem);

    const bodyMatches =
      normalizeValueArray(currentItem.keywords)
        .filter(keyword =>
          keyword.length >= 2
          && candidateBody.includes(keyword)
        );

    if (bodyMatches.length) {
      score += bodyMatches.length * 4;

      if (
        !commonKeywords.length
        && bodyMatches.length
      ) {
        reasons.push(
          `내용 연관 ${bodyMatches
            .slice(0, 2)
            .join(" · ")}`
        );
      }
    }

    return {
      score,
      reasons
    };
  }

  function getRecommendedItems(
    currentItem,
    limit = 10
  ) {
    const itemCategory =
      currentItem.libraryCategory
      || currentCategory;

    const normalizedCurrentItem = {
      ...currentItem,
      libraryCategory: itemCategory
    };

    return recommendationPool
      .filter(candidate => {
        const sameItem =
          candidate.id === normalizedCurrentItem.id
          && candidate.libraryCategory
            === normalizedCurrentItem.libraryCategory;

        return !sameItem;
      })
      .map(candidate => {
        const result =
          calculateRecommendationScore(
            normalizedCurrentItem,
            candidate
          );

        return {
          ...candidate,
          recommendationScore: result.score,
          recommendationReasons: result.reasons
        };
      })
      .filter(item =>
        item.recommendationScore > 0
      )
      .sort((a, b) => {
        if (
          b.recommendationScore
          !== a.recommendationScore
        ) {
          return (
            b.recommendationScore
            - a.recommendationScore
          );
        }

        return getItemTitle(a)
          .localeCompare(
            getItemTitle(b),
            "ko"
          );
      })
      .slice(0, limit);
  }

  function getCategoryTitle(category) {
    return (
      LIBRARY_CONFIG.categories[category]?.title
      || category
    );
  }


  function createRecommendationMarkup(item) {
    if (!recommendationPoolLoaded) {
      return `
        <p class="empty-message">
          추천 자료를 불러오는 중입니다.
        </p>
      `;
    }

    const recommendedItems =
      getRecommendedItems(item, 10);

    if (!recommendedItems.length) {
      return `
        <p class="empty-message">
          연관 자료를 아직 찾지 못했습니다.
        </p>
      `;
    }

    return `
      <div class="archive-recommendation-list">
        ${recommendedItems
          .map((recommended, index) => {
            const reasons =
              recommended.recommendationReasons
                .slice(0, 2)
                .join(" · ");

            return `
              <button
                type="button"
                class="archive-recommendation-item"
                data-recommend-id="${escapeHtml(
                  recommended.id
                )}"
                data-recommend-category="${escapeHtml(
                  recommended.libraryCategory
                )}"
              >
                <span class="archive-recommendation-rank">
                  ${index + 1}
                </span>

                <span class="archive-recommendation-content">
                  <span class="archive-recommendation-header">
                    <span class="archive-recommendation-title">
                      ${escapeHtml(
                        getItemTitle(recommended)
                      )}
                    </span>

                    <span class="archive-recommendation-meta">
                      ${escapeHtml(
                        getCategoryTitle(
                          recommended.libraryCategory
                        )
                      )}
                      ·
                      ${escapeHtml(
                        getTypeLabel(recommended.type)
                      )}
                    </span>
                  </span>

                  ${
                    reasons
                      ? `
                        <span class="archive-recommendation-reason">
                          ${escapeHtml(reasons)}
                        </span>
                      `
                      : ""
                  }
                </span>
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  

  /* ---------------------------------------------------------
     카테고리
     --------------------------------------------------------- */

  function updateCategoryButtons() {
    categoryButtons.forEach(button => {
      const active =
        button.dataset.category === currentCategory;

      button.classList.toggle("active", active);

      button.setAttribute(
        "aria-selected",
        String(active)
      );
    });

    const config =
      LIBRARY_CONFIG.categories[currentCategory];

    timelineTitle.textContent =
      config?.timelineTitle || "연대기";

    archiveSearchTitle.textContent =
      config?.archiveSearchTitle || "자료 검색";

    selectedCategory.textContent =
      config?.title
        ? `(${config.title})`
        : "";

    currentMediaPath =
      config?.mediaPath || "";
  }


  async function handleCategoryChange(event) {
    const category =
      event.currentTarget.dataset.category;

    if (
      !category
      || category === currentCategory
    ) {
      return;
    }

    currentCategory = category;

    const newUrl =
      `${window.location.pathname}`
      + `?category=${encodeURIComponent(category)}`;

    window.history.replaceState(
      null,
      "",
      newUrl
    );

    await loadCategory(category);
  }


  async function loadCategory(category) {
    const config =
      LIBRARY_CONFIG.categories[category];

    if (!config) {
      console.error(
        `정의되지 않은 Library 카테고리입니다: ${category}`
      );

      return;
    }

    currentCategory = category;
    currentMediaPath = config.mediaPath || "";

    updateCategoryButtons();

    try {
      const dataUrl =
        `${getIndexFile(category)}?v=${Date.now()}`;

      const response = await fetch(dataUrl, {
        cache: "no-store"
      });

      if (!response.ok) {
        throw new Error(
          `${category} JSON 로딩 실패: HTTP ${response.status}`
        );
      }

      const data = await response.json();

      timeline = Array.isArray(data.timeline)
        ? [...data.timeline].sort(
            (a, b) => a.year - b.year
          )
        : [];

      archives = isComputerCategory()
        ? (
            Array.isArray(data.records)
              ? data.records
              : []
          )
        : (
            Array.isArray(data.archives)
              ? data.archives
              : []
          );

      selectedTimelineIndex = 0;
      selectedArchiveId = null;

      renderTimeline();

      renderArchiveSearchResults(
        archives,
        "전체 자료"
      );

      const firstLinkedItem =
        timeline.find(item =>
          getArchiveById(item.id)
        );

      if (firstLinkedItem) {
        selectedTimelineIndex =
          timeline.findIndex(item =>
            item.id === firstLinkedItem.id
          );

        selectArchive(firstLinkedItem.id);
        renderTimeline();

      } else if (archives[0]) {
        selectArchive(archives[0].id);

      } else {
        renderEmptyArchive();
      }

    } catch (error) {
      console.error(error);

      timeline = [];
      archives = [];

      timelineCount.textContent = "0항목";

      timelineList.innerHTML = `
        <p class="empty-message">
          연대기 자료를 불러오지 못했습니다.
        </p>
      `;

      archiveDetail.innerHTML = `
        <p class="empty-message">
          자료를 불러오지 못했습니다.
        </p>
      `;

      archiveSearchStatus.textContent =
        "불러오기 실패";

      archiveSearchCount.textContent =
        "0건";

      archiveSearchResults.innerHTML = `
        <p class="empty-message">
          검색 데이터를 불러오지 못했습니다.
        </p>
      `;
    }
  }


  /* ---------------------------------------------------------
     연대기
     --------------------------------------------------------- */

  function renderTimeline() {
    timelineCount.textContent =
      `${timeline.length}항목`;

    if (timeline.length === 0) {
      timelineList.innerHTML = `
        <p class="empty-message">
          이 카테고리의 연대기 자료는 아직 없습니다.
        </p>
      `;

      return;
    }

    const visibleItems = timeline;

    timelineList.innerHTML =
      visibleItems
        .map(item => {
          const selected =
            timeline[selectedTimelineIndex]?.id
            === item.id;

          return `
            <button
              type="button"
              class="timeline-item${selected ? " selected" : ""}"
              data-timeline-id="${escapeHtml(item.id)}"
            >
              <span class="timeline-year">
                ${escapeHtml(formatYear(item.year))}
              </span>

              <span class="timeline-name">
                ${escapeHtml(item.korean || item.title || item.name || item.id)}
              </span>

              <span class="timeline-description">
                ${escapeHtml(item.description || "")}
              </span>
            </button>
          `;
        })
        .join("");

    timelineList
      .querySelectorAll("[data-timeline-id]")
      .forEach(button => {
        button.addEventListener("click", () => {
          const id = button.dataset.timelineId;

          selectedTimelineIndex =
            timeline.findIndex(item =>
              item.id === id
            );

          renderTimeline();

          if (getArchiveById(id)) {
            selectArchive(id);
          } else {
            renderMissingLinkedArchive(id);
          }
        });
      });

      const selectedButton =
        timelineList.querySelector(".timeline-item.selected");

      selectedButton?.scrollIntoView({
        block: "center",
        behavior: "smooth"
      });
      
  }


  function handleTimelineSearch(event) {
    event.preventDefault();

    const query =
      normalizeText(timelineSearchWord.value);

    if (!query) {
      timelineSearchMessage.textContent =
        "검색할 이름 또는 연도를 입력해 주세요.";

      return;
    }

    let index = -1;

    const numericQuery =
      Number(query.replace(/^bc\s*/i, "-"));

    if (Number.isFinite(numericQuery)) {
      index = findNearestYearIndex(numericQuery);
    } else {
      index = timeline.findIndex(item => {
        const searchable = normalizeText([
          item.id,
          item.korean,
          item.title,
          item.english,
          item.name,
          item.description
        ].join(" "));

        return searchable.includes(query);
      });
    }

    if (index < 0) {
      timelineSearchMessage.textContent =
        "조건에 맞는 연대기 항목이 없습니다.";

      return;
    }

    selectedTimelineIndex = index;

    const item =
      timeline[selectedTimelineIndex];

    renderTimeline();

    timelineSearchMessage.textContent =
      `${formatYear(item.year)} · ${item.korean || item.title || item.name || item.id}`;

    if (getArchiveById(item.id)) {
      selectArchive(item.id);
    } else {
      renderMissingLinkedArchive(item.id);
    }
  }


  function findNearestYearIndex(targetYear) {
    if (timeline.length === 0) {
      return -1;
    }

    let nearestIndex = 0;
    let nearestDistance =
      Math.abs(timeline[0].year - targetYear);

    timeline.forEach((item, index) => {
      const distance =
        Math.abs(item.year - targetYear);

      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    });

    return nearestIndex;
  }


  function resetTimelineSearch() {
    timelineSearchForm.reset();

    if (timeline.length > 0) {
      selectedTimelineIndex = 0;
      renderTimeline();
    }

    timelineSearchMessage.textContent =
      "인물·사건의 이름이나 연도를 입력해 주세요.";

    timelineSearchWord.focus();
  }


  /* ---------------------------------------------------------
     상세 자료
     --------------------------------------------------------- */

  function selectArchive(id) {
    const item =
      getArchiveById(id);

    if (!item) {
      return;
    }

    selectedArchiveId = id;

    renderArchiveDetail(item);
    updateSelectedArchiveStyles();
  }


  function renderArchiveDetail(item) {
    if (isComputerItem(item)) {
      renderComputerDetail(item);
      return;
    }

    renderHistoryDetail(item);
  }


  function renderHistoryDetail(item) {
    const fields = toArray(item.fields);
    const keywords = toArray(item.keywords);

    archiveDetail.innerHTML = `
      <dl class="archive-meta">
        <dt>한글 명칭</dt>
        <dd>${escapeHtml(item.korean || "-")}</dd>

        <dt>원문 명칭</dt>
        <dd>${escapeHtml(item.name || "-")}</dd>

        <dt>자료 유형</dt>
        <dd>${escapeHtml(getTypeLabel(item.type))}</dd>

        <dt>시대·생애</dt>
        <dd>${escapeHtml(item.years || "-")}</dd>

        <dt>국가·지역</dt>
        <dd>${escapeHtml(item.country || "-")}</dd>

        <dt>분야</dt>
        <dd>${createTagMarkup(fields)}</dd>

        <dt>키워드</dt>
        <dd>${createTagMarkup(keywords)}</dd>
      </dl>

      <section class="archive-section">
        <h3>개요</h3>
        ${createParagraphMarkup(
          item.summary,
          "등록된 개요가 없습니다."
        )}
      </section>

      <section class="archive-section">
        <h3>주요 내용</h3>
        ${createParagraphMarkup(
          item.achievements,
          "등록된 주요 내용이 없습니다."
        )}
      </section>

      <section class="archive-section">
        <h3>참고 자료</h3>
        ${createTagMarkup(toArray(item.sources))}
      </section>

      <div
        class="archive-resource-grid"
        style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:24px; align-items:start;"
      >
        <section class="archive-section archive-resource-section">
          <h3>첨부 자료</h3>
          ${createMediaMarkup(item.media)}
        </section>

        <section class="archive-section archive-resource-section">
          <h3>관련 자료</h3>
          ${createRelatedMarkup(item.related)}
        </section>
      </div>

      <section class="archive-section archive-recommendation-section">
        <h3>함께 보면 좋은 자료</h3>
        ${createRecommendationMarkup(item)}
      </section>
    `;
  }


  function renderComputerDetail(item) {
    const fields = toArray(item.fields);
    const aliases = toArray(item.aliases);
    const keywords = toArray(item.keywords);

    archiveDetail.innerHTML = `
      <dl class="archive-meta">
        <dt>자료명</dt>
        <dd>${escapeHtml(item.title || item.id || "-")}</dd>

        <dt>영문명</dt>
        <dd>${escapeHtml(item.english || "-")}</dd>

        <dt>자료 유형</dt>
        <dd>${escapeHtml(getTypeLabel(item.type))}</dd>

        <dt>시대·연도</dt>
        <dd>${escapeHtml(item.years || "-")}</dd>

        <dt>분야</dt>
        <dd>${createTagMarkup(fields)}</dd>

        <dt>별칭</dt>
        <dd>${createTagMarkup(aliases)}</dd>

        <dt>키워드</dt>
        <dd>${createTagMarkup(keywords)}</dd>
      </dl>

      <section class="archive-section">
        <h3>요약</h3>
        ${createParagraphMarkup(
          item.summary,
          "등록된 요약이 없습니다."
        )}
      </section>

      <section class="archive-section">
        <h3>내용</h3>
        ${createParagraphMarkup(
          item.content,
          "등록된 내용이 없습니다."
        )}
      </section>

      <section class="archive-section">
        <h3>참고 자료</h3>
        ${createTagMarkup(toArray(item.sources))}
      </section>

      <div
        class="archive-resource-grid"
        style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:24px; align-items:start;"
      >
        <section class="archive-section archive-resource-section">
          <h3>첨부 자료</h3>
          ${createMediaMarkup(item.media)}
        </section>

        <section class="archive-section archive-resource-section">
          <h3>관련 자료</h3>
          ${createRelatedMarkup(item.related)}
        </section>
      </div>

      <section class="archive-section archive-recommendation-section">
        <h3>함께 보면 좋은 자료</h3>
        ${createRecommendationMarkup(item)}
      </section>
    `;
  }


  function renderEmptyArchive() {
    archiveDetail.innerHTML = `
      <p class="empty-message">
        이 카테고리의 자료는 아직 없습니다.
      </p>
    `;
  }


  function renderMissingLinkedArchive(id) {
    selectedArchiveId = null;

    archiveDetail.innerHTML = `
      <p class="empty-message">
        연대기 항목 “${escapeHtml(id)}”에 연결된 상세 자료는 아직 없습니다.
      </p>
    `;

    updateSelectedArchiveStyles();
  }


  function createTagMarkup(items) {
    if (!items.length) {
      return "-";
    }

    return `
      <div class="archive-tags">
        ${items
          .map(item => `
            <span class="archive-tag">
              ${escapeHtml(item)}
            </span>
          `)
          .join("")}
      </div>
    `;
  }


  function createParagraphMarkup(value, emptyMessage) {
    const items =
      toArray(value)
        .map(item => String(item).trim())
        .filter(Boolean);

    if (!items.length) {
      return `
        <p class="empty-message">
          ${escapeHtml(emptyMessage)}
        </p>
      `;
    }

    return items
      .map(item => `
        <p>
          ${escapeHtml(item)}
        </p>
      `)
      .join("");
  }


  function createRelatedMarkup(relatedIds) {
    const ids =
      toArray(relatedIds);

    if (!ids.length) {
      return `
        <p class="empty-message">
          연결된 자료가 없습니다.
        </p>
      `;
    }

    return ids
      .map(id => {
        const linked =
          getArchiveById(id);

        if (!linked) {
          return `
            <p>
              ${escapeHtml(id)}
            </p>
          `;
        }

        return `
          <p>
            <button
              type="button"
              class="related-link"
              data-related-id="${escapeHtml(id)}"
            >
              ${escapeHtml(
                linked.title ||
                linked.korean ||
                linked.name ||
                linked.english ||
                id
              )}
            </button>
          </p>
        `;
      })
      .join("");
  }


  function createMediaMarkup(mediaItems) {
    const items =
      Array.isArray(mediaItems)
        ? mediaItems
        : [];

    if (!items.length) {
      return `
        <p class="empty-message">
          첨부 자료가 없습니다.
        </p>
      `;
    }

    return items
      .map(item => {
        const filename =
          item.file || "";

        const title =
          item.title || filename;

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

        return `
          <p>
            <a
              class="archive-media-link"
              href="${currentMediaPath}${encodeURIComponent(filename)}"
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
     아카이브 검색
     --------------------------------------------------------- */

  function handleArchiveSearch(event) {
    event.preventDefault();

    const nameQuery =
      normalizeText(archiveSearchName.value);

    const typeQuery =
      normalizeText(archiveSearchType.value);

    const fieldQuery =
      normalizeText(archiveSearchField.value);

    const wordQuery =
      normalizeText(archiveSearchWord.value);

    const matched =
      archives.filter(item => {
        if (isComputerCategory()) {
          const nameText = normalizeText([
            item.id,
            item.title,
            item.english,
            ...toArray(item.aliases)
          ].join(" "));

          const fieldText =
            normalizeText(
              toArray(item.fields).join(" ")
            );

          const wordText =
            normalizeText([
              item.id,
              item.title,
              item.english,
              item.type,
              item.years,
              ...toArray(item.aliases),
              ...toArray(item.fields),
              ...toArray(item.keywords),
              ...toArray(item.summary),
              ...toArray(item.content),
              ...toArray(item.related),
              ...toArray(item.sources),
              ...toArray(item.media).flatMap(media => [
                media.file,
                media.title
              ])
            ].join(" "));

          return (
            nameText.includes(nameQuery)
            && normalizeText(item.type).includes(typeQuery)
            && fieldText.includes(fieldQuery)
            && wordText.includes(wordQuery)
          );
        }

        const nameText = normalizeText([
          item.id,
          item.korean,
          item.name
        ].join(" "));

        const fieldText =
          normalizeText(toArray(item.fields).join(" "));

        const wordText =
          normalizeText([
            item.id,
            item.korean,
            item.name,
            item.type,
            item.years,
            item.country,
            ...toArray(item.fields),
            ...toArray(item.keywords),
            ...toArray(item.summary),
            ...toArray(item.achievements),
            ...toArray(item.related),
            ...toArray(item.media).flatMap(media => [
              media.file,
              media.title
            ])
          ].join(" "));

        return (
          nameText.includes(nameQuery)
          && normalizeText(item.type).includes(typeQuery)
          && fieldText.includes(fieldQuery)
          && wordText.includes(wordQuery)
        );
      });

    renderArchiveSearchResults(
      matched,
      "검색 결과"
    );
  }


  function resetArchiveSearch() {
    archiveSearchForm.reset();

    renderArchiveSearchResults(
      archives,
      "전체 자료"
    );

    archiveSearchName.focus();
  }


  function renderArchiveSearchResults(items, statusText) {
    archiveSearchStatus.textContent =
      statusText;

    archiveSearchCount.textContent =
      `${items.length}건`;

    if (!items.length) {
      archiveSearchResults.innerHTML = `
        <p class="empty-message">
          조건에 맞는 자료가 없습니다.
        </p>
      `;

      return;
    }

    const useCompactComputerResults =
      items.every(item => isComputerItem(item))
      && items.length > 4;

    archiveSearchResults.innerHTML =
      items
        .map(item => {
          if (isComputerItem(item)) {
            const keywords =
              toArray(item.keywords)
                .filter(Boolean)
                .slice(0, 3)
                .join(" · ");

            const englishTitle =
              item.english || "";

            return `
              <button
                type="button"
                class="search-result-item computer-search-result${
                  useCompactComputerResults
                    ? " compact"
                    : " expanded"
                }${
                  item.id === selectedArchiveId
                    ? " selected"
                    : ""
                }"
                data-archive-id="${escapeHtml(item.id)}"
              >
                <span class="search-result-meta">
                  <span>
                    ${escapeHtml(getTypeLabel(item.type))}
                  </span>

                  <span class="search-result-top-keywords">
                    ${escapeHtml(keywords || "-")}
                  </span>
                </span>

                <span class="search-result-title">
                  ${escapeHtml(item.title || item.id)}
                </span>

                ${
                  useCompactComputerResults
                    ? ""
                    : `
                      <span class="search-result-english">
                        ${escapeHtml(englishTitle || "-")}
                      </span>
                    `
                }
              </button>
            `;
          }

          const keywords =
            toArray(item.keywords)
              .filter(Boolean)
              .join(" · ");

          return `
            <button
              type="button"
              class="search-result-item${
                item.id === selectedArchiveId
                  ? " selected"
                  : ""
              }"
              data-archive-id="${escapeHtml(item.id)}"
            >
              <span class="search-result-meta">
                <span>
                  ${escapeHtml(getTypeLabel(item.type))}
                </span>

                <span>
                  ${escapeHtml(toArray(item.fields).join(" · "))}
                </span>
              </span>

              <span class="search-result-title">
                ${escapeHtml(item.korean || item.name || item.id)}
              </span>

              <span class="search-result-keywords">
                ${escapeHtml(keywords || "등록된 설명이 없습니다.")}
              </span>
            </button>
          `;
        })
        .join("");

    archiveSearchResults
      .querySelectorAll("[data-archive-id]")
      .forEach(button => {
        button.addEventListener("click", () => {
          selectArchive(button.dataset.archiveId);
        });
      });

    updateSelectedArchiveStyles();
  }


  function updateSelectedArchiveStyles() {
    document
      .querySelectorAll("[data-archive-id]")
      .forEach(button => {
        button.classList.toggle(
          "selected",
          button.dataset.archiveId
            === selectedArchiveId
        );
      });
  }


  /* ---------------------------------------------------------
     이벤트
     --------------------------------------------------------- */

  function bindEvents() {
    categoryButtons.forEach(button => {
      button.addEventListener(
        "click",
        handleCategoryChange
      );
    });

    timelineSearchForm.addEventListener(
      "submit",
      handleTimelineSearch
    );

    timelineSearchReset.addEventListener(
      "click",
      resetTimelineSearch
    );

    archiveSearchForm.addEventListener(
      "submit",
      handleArchiveSearch
    );

    archiveSearchReset.addEventListener(
      "click",
      resetArchiveSearch
    );

    archiveDetail.addEventListener(
      "click",
      async event => {
        const relatedButton =
          event.target.closest("[data-related-id]");

        if (relatedButton) {
          selectArchive(
            relatedButton.dataset.relatedId
          );

          return;
        }

        const recommendationButton =
          event.target.closest("[data-recommend-id]");

        if (!recommendationButton) {
          return;
        }

        const id =
          recommendationButton.dataset.recommendId;

        const category =
          recommendationButton.dataset
            .recommendCategory;

        if (!id || !category) {
          return;
        }

        /*
        * 같은 카테고리의 자료
        */
        if (category === currentCategory) {
          selectArchive(id);
          return;
        }

        /*
        * 다른 카테고리의 자료
        */
        const newUrl =
          `${window.location.pathname}`
          + `?category=${encodeURIComponent(category)}`;

        window.history.replaceState(
          null,
          "",
          newUrl
        );

        await loadCategory(category);

        if (getArchiveById(id)) {
          selectArchive(id);
        }
      }
    );
  }


  /* ---------------------------------------------------------
     실행
     --------------------------------------------------------- */

  async function init() {
    const params =
      new URLSearchParams(window.location.search);

    const category =
      params.get("category");

    if (
      category &&
      LIBRARY_CONFIG.categories[category]
    ) {
      currentCategory = category;
    }

    bindEvents();
    await loadRecommendationPool();
    await loadCategory(currentCategory);
  }


  return {
    init
  };

})();


document.addEventListener(
  "DOMContentLoaded",
  LibraryBoard.init
);
