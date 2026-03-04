(() => {
  'use strict';

  const FINISH_THRESHOLD_SECONDS = 0.12;
  const ADVANCE_COOLDOWN_MS = 900;

  let activeVideo = null;
  let lastAdvanceAt = 0;
  let observer = null;

  function getShortIdFromPath() {
    const match = location.pathname.match(/^\/shorts\/([^/?#]+)/);
    return match ? match[1] : null;
  }

  function getActiveRenderer() {
    return document.querySelector('ytd-reel-video-renderer[is-active]');
  }

  function getCurrentVideo() {
    const renderer = getActiveRenderer();
    if (renderer) {
      const directVideo = renderer.querySelector('video');
      if (directVideo) return directVideo;
    }

    return document.querySelector('video');
  }

  function goNext() {
    const nextButton = document.querySelector(
      'button[aria-label="Next video"], button[aria-label="Next"], yt-icon-button[aria-label="Next video"]'
    );

    if (nextButton) {
      nextButton.click();
      return;
    }

    const eventOptions = { key: 'ArrowDown', code: 'ArrowDown', keyCode: 40, which: 40, bubbles: true };
    document.dispatchEvent(new KeyboardEvent('keydown', eventOptions));
    document.dispatchEvent(new KeyboardEvent('keyup', eventOptions));
  }

  function shouldAdvance(video) {
    if (!video || !Number.isFinite(video.duration) || video.duration <= 0) return false;
    if (video.ended) return true;

    const remaining = video.duration - video.currentTime;
    return remaining <= FINISH_THRESHOLD_SECONDS;
  }

  function maybeAdvance() {
    const now = Date.now();
    if (now - lastAdvanceAt < ADVANCE_COOLDOWN_MS) return;

    const video = getCurrentVideo();
    if (!video || !shouldAdvance(video)) return;

    const shortId = getShortIdFromPath();
    if (!shortId) return;

    lastAdvanceAt = now;
    goNext();
  }

  function attachVideoListeners(video) {
    if (!video || video === activeVideo) return;

    if (activeVideo) {
      activeVideo.removeEventListener('ended', maybeAdvance);
      activeVideo.removeEventListener('timeupdate', maybeAdvance);
    }

    activeVideo = video;
    activeVideo.addEventListener('ended', maybeAdvance);
    activeVideo.addEventListener('timeupdate', maybeAdvance);
  }

  function refreshBindings() {
    attachVideoListeners(getCurrentVideo());
  }

  function startObserver() {
    if (observer) observer.disconnect();

    observer = new MutationObserver(() => {
      refreshBindings();
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['is-active']
    });
  }

  function init() {
    refreshBindings();
    startObserver();
    setInterval(maybeAdvance, 400);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
