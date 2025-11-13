(() => {
  const panel = document.querySelector('[data-reader-panel]');
  if (!panel) return;

  const page = document.querySelector('.chapter-page');
  const body = document.body;
  const root = document.documentElement;
  const overlayCard = panel.querySelector('[data-reader-overlay-card]');
  const themeBtn = panel.querySelector('[data-theme-toggle]');
  const fontSlider = panel.querySelector('[data-font-slider]');
  const fontLabel = panel.querySelector('[data-font-label]');
  const slider = panel.querySelector('[data-chapter-slider]');
  const sliderLabel = panel.querySelector('[data-slider-value]');
  const progressEl = panel.querySelector('[data-progress]');
  const trackButtons = panel.querySelectorAll('[data-track]');
  const jumpBtn = panel.querySelector('[data-jump-btn]');
  const jumpPanel = panel.querySelector('[data-jump-panel]');
  const jumpClose = panel.querySelector('[data-jump-close]');
  const chapterList = panel.querySelector('[data-chapter-list]');
  const fontBtn = panel.querySelector('[data-font-btn]');
  const fontPanel = panel.querySelector('[data-font-panel]');

  const total = Number(panel.dataset.total || 1);
  let activeChapter = Math.min(Number(panel.dataset.current || 1), total);
  const slug = panel.dataset.slug || '';
  const groupSize = Number(panel.dataset.groupSize || 10);
  const prevUrl = panel.dataset.prevUrl;
  const nextUrl = panel.dataset.nextUrl;
  const THEME_KEY = 'readerTheme';
  const FONT_KEY = 'readerFontSize';

  let controlsVisible = page ? page.classList.contains('controls-visible') : true;
  const setControls = (show) => {
    controlsVisible = show;
    if (page) page.classList.toggle('controls-visible', show);
    if (!show) {
      closeJumpPanel();
      closeFontPanel();
    }
  };

  const outsidePanels = (target) =>
    target.closest('[data-reader-panel]') ||
    target.closest('[data-jump-panel]') ||
    target.closest('[data-font-panel]');

  page?.addEventListener('click', (event) => {
    if (outsidePanels(event.target)) return;
    setControls(!controlsVisible);
  });

  overlayCard?.addEventListener('click', (event) => event.stopPropagation());
  jumpPanel?.addEventListener('click', (event) => event.stopPropagation());
  fontPanel?.addEventListener('click', (event) => event.stopPropagation());

  const applyTheme = (theme) => {
    body.dataset.theme = theme;
    if (themeBtn) themeBtn.textContent = theme === 'dark' ? '🌙' : '☀️';
  };

  const applyFont = (size) => {
    root.style.setProperty('--reader-font-size', `${size}px`);
    if (fontLabel) fontLabel.textContent = `${size}px`;
  };

  const storedTheme = localStorage.getItem(THEME_KEY) || 'dark';
  const storedFont = Number(localStorage.getItem(FONT_KEY)) || 18;
  applyTheme(storedTheme);
  applyFont(storedFont);
  if (fontSlider) fontSlider.value = storedFont;

  themeBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    const nextTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    localStorage.setItem(THEME_KEY, nextTheme);
  });

  fontSlider?.addEventListener('input', () => {
    const size = Number(fontSlider.value);
    applyFont(size);
    localStorage.setItem(FONT_KEY, String(size));
  });

  const updateProgress = () => {
    if (progressEl) {
      const pct = Math.min(100, ((activeChapter / total) * 100).toFixed(1));
      progressEl.textContent = `${pct}%`;
    }
  };

  const highlightChapter = () => {
    if (!chapterList) return;
    chapterList.querySelectorAll('.chapter-item.is-active').forEach((node) => node.classList.remove('is-active'));
    const active = chapterList.querySelector(`[data-chapter-item="${activeChapter}"]`);
    active?.classList.add('is-active');
  };

  const syncControls = () => {
    if (slider) {
      slider.value = activeChapter;
      if (sliderLabel) sliderLabel.textContent = slider.value;
    }
    updateProgress();
    highlightChapter();
  };

  const goToChapter = (chapterNumber) => {
    if (!slug) return;
    const safeValue = Math.min(Math.max(chapterNumber, 1), total);
    const start = Math.floor((safeValue - 1) / groupSize) * groupSize + 1;
    window.location.href = `/novel/${slug}/group/${start}`;
  };

  if (slider) {
    slider.max = total;
    slider.value = activeChapter;
    syncControls();

    slider.addEventListener('input', () => {
      if (sliderLabel) sliderLabel.textContent = slider.value;
    });

    slider.addEventListener('change', () => {
      activeChapter = Math.min(Math.max(Number(slider.value), 1), total);
      syncControls();
      goToChapter(activeChapter);
    });
  }

  const buildChapterList = () => {
    if (!chapterList || chapterList.childElementCount) return;
    const fragment = document.createDocumentFragment();
    for (let i = 1; i <= total; i += 1) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chapter-item';
      btn.dataset.chapterItem = String(i);
      btn.textContent = `Chapter ${i}`;
      fragment.appendChild(btn);
    }
    chapterList.appendChild(fragment);
    highlightChapter();
  };

  chapterList?.addEventListener('click', (event) => {
    const target = event.target.closest('.chapter-item');
    if (!target) return;
    activeChapter = Number(target.dataset.chapterItem);
    syncControls();
    goToChapter(activeChapter);
  });

  function closeJumpPanel() {
    if (!jumpPanel || !jumpBtn) return;
    jumpPanel.hidden = true;
    jumpBtn.setAttribute('aria-expanded', 'false');
  }

  const toggleJumpPanel = () => {
    if (!jumpPanel || !jumpBtn) return;
    const willShow = jumpPanel.hidden;
    if (willShow) {
      buildChapterList();
      jumpPanel.hidden = false;
      jumpBtn.setAttribute('aria-expanded', 'true');
      setControls(true);
    } else {
      closeJumpPanel();
    }
  };

  jumpBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    toggleJumpPanel();
  });

  jumpClose?.addEventListener('click', closeJumpPanel);

  function closeFontPanel() {
    if (!fontPanel || !fontBtn) return;
    fontPanel.hidden = true;
    fontBtn.setAttribute('aria-expanded', 'false');
  }

  const toggleFontPanel = () => {
    if (!fontPanel || !fontBtn) return;
    const willShow = fontPanel.hidden;
    if (willShow) {
      fontPanel.hidden = false;
      fontBtn.setAttribute('aria-expanded', 'true');
      setControls(true);
    } else {
      closeFontPanel();
    }
  };

  fontBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    toggleFontPanel();
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('[data-jump-panel]') && !event.target.closest('[data-jump-btn]')) {
      closeJumpPanel();
    }
    if (!event.target.closest('[data-font-panel]') && !event.target.closest('[data-font-btn]')) {
      closeFontPanel();
    }
  });

  trackButtons.forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      const direction = btn.dataset.track;
      if (direction === 'prev') {
        if (prevUrl) return (window.location.href = prevUrl);
        activeChapter = Math.min(Math.max(activeChapter - groupSize, 1), total);
        syncControls();
        goToChapter(activeChapter);
      }
      if (direction === 'next') {
        if (nextUrl) return (window.location.href = nextUrl);
        activeChapter = Math.min(Math.max(activeChapter + groupSize, 1), total);
        syncControls();
        goToChapter(activeChapter);
      }
    });
  });

  syncControls();
})();
