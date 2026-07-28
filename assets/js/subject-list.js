"use strict";


/* =========================================================
   LOGIA Subject List
   ========================================================= */

const SubjectList = (() => {

  const DATA_FILE = "/subjects/subjects-index.json";


  async function fetchSubjectCatalog() {
    const response = await fetch(
      `${DATA_FILE}?v=${Date.now()}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(
        `Subject catalog loading failed: HTTP ${response.status}`
      );
    }

    const data = await response.json();

    return Array.isArray(data.subjects)
      ? [...data.subjects].sort((first, second) => {
          const firstOrder = Number(first.displayOrder) || 999999;
          const secondOrder = Number(second.displayOrder) || 999999;

          if (firstOrder !== secondOrder) {
            return firstOrder - secondOrder;
          }

          return String(first.title || first.subject)
            .localeCompare(
              String(second.title || second.subject),
              "ko"
            );
        })
      : [];
  }


  function createAnchor(item, includeOrder = false) {
    const anchor = document.createElement("a");

    anchor.href = item.href
      || `/subjects/subject.html?subject=${encodeURIComponent(item.subject)}`;

    anchor.target = "contentFrame";

    const prefix = includeOrder
      ? `${item.displayOrder}. `
      : "";

    anchor.textContent =
      `${prefix}${item.title || item.subject}`;

    return anchor;
  }


  function renderCourseList(container, subjects) {
    container.innerHTML = "";

    subjects.forEach(item => {
      const listItem = document.createElement("li");
      listItem.appendChild(createAnchor(item));
      container.appendChild(listItem);
    });
  }


  function renderNavigation(marker, subjects) {
    document
      .querySelectorAll("[data-subject-link]")
      .forEach(link => link.remove());

    const fragment = document.createDocumentFragment();

    subjects.forEach(item => {
      const anchor = createAnchor(item, true);
      anchor.dataset.subjectLink = "";
      fragment.appendChild(anchor);
    });

    marker.parentNode.insertBefore(
      fragment,
      marker.nextSibling
    );
  }


  async function init() {
    const courseList = document.getElementById(
      "current-course-list"
    );

    const navigationMarker = document.getElementById(
      "subject-navigation-marker"
    );

    if (!courseList && !navigationMarker) {
      return;
    }

    try {
      const subjects = await fetchSubjectCatalog();

      if (!subjects.length) {
        return;
      }

      if (courseList) {
        renderCourseList(courseList, subjects);
      }

      if (navigationMarker) {
        renderNavigation(navigationMarker, subjects);
      }
    } catch (error) {
      /*
       * 정적 HTML에 기존 목록이 남아 있으므로,
       * 카탈로그 로딩 실패 시 그 목록을 그대로 사용한다.
       */
      console.info(error);
    }
  }


  return {
    init
  };

})();


document.addEventListener(
  "DOMContentLoaded",
  SubjectList.init
);
