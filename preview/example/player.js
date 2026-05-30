(function () {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");
  const menuToggle = document.getElementById("menu-toggle");
  const episodeListEl = document.getElementById("episode-list");
  const playerArea = document.getElementById("player-area");
  const loadingEl = document.getElementById("loading");
  const seriesTitleEl = document.getElementById("series-title");
  const seriesDescEl = document.getElementById("series-description");
  const topSeriesTitleEl = document.getElementById("top-series-title");

  let catalog = null;
  let currentIndex = 0;
  let videoEl = null;

  function getEpisodeFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const ep = parseInt(params.get("ep"), 10);
    return Number.isFinite(ep) && ep > 0 ? ep : 1;
  }

  function setEpisodeQuery(number) {
    const url = new URL(window.location.href);
    url.searchParams.set("ep", String(number));
    history.replaceState(null, "", url);
  }

  function findIndexByNumber(number) {
    if (!catalog) return 0;
    const idx = catalog.episodes.findIndex((e) => e.number === number);
    return idx >= 0 ? idx : 0;
  }

  function toggleSidebar(open) {
    const shouldOpen = open ?? !sidebar.classList.contains("open");
    sidebar.classList.toggle("open", shouldOpen);
    overlay.classList.toggle("open", shouldOpen);
  }

  menuToggle.addEventListener("click", () => toggleSidebar());
  overlay.addEventListener("click", () => toggleSidebar(false));

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderEpisodeList() {
    episodeListEl.innerHTML = "";
    catalog.episodes.forEach((ep, idx) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.innerHTML =
        '<span class="ep-num">Episode ' + ep.number + "</span>" +
        '<span class="ep-title">' + escapeHtml(ep.title) + "</span>";
      btn.addEventListener("click", () => {
        loadEpisode(idx);
        if (window.innerWidth <= 768) toggleSidebar(false);
      });
      li.appendChild(btn);
      episodeListEl.appendChild(li);
    });
  }

  function updateActiveListItem() {
    episodeListEl.querySelectorAll("button").forEach((btn, idx) => {
      btn.classList.toggle("active", idx === currentIndex);
    });
  }

  function buildPlayer() {
    playerArea.innerHTML = "";
    const ep = catalog.episodes[currentIndex];

    const wrap = document.createElement("div");
    wrap.className = "video-wrap";

    videoEl = document.createElement("video");
    videoEl.controls = true;
    videoEl.playsInline = true;
    videoEl.setAttribute("playsinline", "");
    videoEl.src = ep.file;
    videoEl.addEventListener("ended", onVideoEnded);
    wrap.appendChild(videoEl);

    const nowPlaying = document.createElement("div");
    nowPlaying.className = "now-playing";
    nowPlaying.innerHTML =
      '<div class="ep-label">Episode ' + ep.number + "</div>" +
      "<h2>" + escapeHtml(ep.title) + "</h2>";

    const controls = document.createElement("div");
    controls.className = "controls";

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.textContent = "← Previous";
    prevBtn.disabled = currentIndex === 0;
    prevBtn.addEventListener("click", () => loadEpisode(currentIndex - 1));

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.textContent = "Next →";
    nextBtn.className = "primary";
    nextBtn.disabled = currentIndex >= catalog.episodes.length - 1;
    nextBtn.addEventListener("click", () => loadEpisode(currentIndex + 1));

    controls.appendChild(prevBtn);
    controls.appendChild(nextBtn);

    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = "Use ← → arrow keys to navigate · Auto-advances when video ends";

    playerArea.appendChild(wrap);
    playerArea.appendChild(nowPlaying);
    playerArea.appendChild(controls);
    playerArea.appendChild(hint);

    document.title = "Ep " + ep.number + ": " + ep.title + " — Storyforge Preview";
    setEpisodeQuery(ep.number);
    updateActiveListItem();
  }

  function loadEpisode(index) {
    if (!catalog || index < 0 || index >= catalog.episodes.length) return;
    currentIndex = index;
    buildPlayer();
  }

  function onVideoEnded() {
    if (currentIndex < catalog.episodes.length - 1) {
      loadEpisode(currentIndex + 1);
      if (videoEl) videoEl.play().catch(() => {});
    }
  }

  document.addEventListener("keydown", (e) => {
    if (!catalog) return;
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA")) return;
    if (e.key === "ArrowLeft" && currentIndex > 0) {
      e.preventDefault();
      loadEpisode(currentIndex - 1);
    } else if (e.key === "ArrowRight" && currentIndex < catalog.episodes.length - 1) {
      e.preventDefault();
      loadEpisode(currentIndex + 1);
    }
  });

  fetch("episodes.json")
    .then((res) => {
      if (!res.ok) throw new Error("Failed to load episodes.json");
      return res.json();
    })
    .then((data) => {
      catalog = data;
      seriesTitleEl.textContent = data.series_title || "Storyforge Preview";
      seriesDescEl.textContent = data.series_description || "";
      topSeriesTitleEl.textContent = data.series_title || "Storyforge Preview";
      renderEpisodeList();
      loadingEl.remove();
      currentIndex = findIndexByNumber(getEpisodeFromQuery());
      buildPlayer();
    })
    .catch((err) => {
      loadingEl.remove();
      playerArea.innerHTML = '<p class="error">' + escapeHtml(err.message) + "</p>";
    });
})();
