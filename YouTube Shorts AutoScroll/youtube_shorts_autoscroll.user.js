// ==UserScript==
// @name         YouTube Shorts Auto-Next
// @namespace    dtools.userscripts
// @version      1.0.0
// @description  Automatically go to the next YouTube Short when the current one finishes.
// @author       D.Tools
// @match        https://www.youtube.com/shorts/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const CHECK_INTERVAL_MS = 250;
  const FINISH_THRESHOLD_S = 0.15;

  let lastAdvancedVideoId = null;

  function getCurrentShortId() {
    const path = window.location.pathname;
    const match = path.match(/^\/shorts\/([^/?#]+)/);
    return match ? match[1] : null;
  }

  function getActiveShortVideo() {
    const reelsPlayer = document.querySelector('ytd-reel-video-renderer[is-active]');
    if (reelsPlayer) {
      const video = reelsPlayer.querySelector('video');
      if (video) return video;
    }

    const visibleVideos = Array.from(document.querySelectorAll('video')).filter((video) => {
      const rect = video.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });

    return visibleVideos[0] || null;
  }

  function goToNextShort() {
    const nextButton = document.querySelector('button[aria-label="Next video"], button[aria-label="Next"]');
    if (nextButton) {
      nextButton.click();
      return true;
    }

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true }));
    return true;
  }

  function shouldAdvance(video) {
    if (!video || !Number.isFinite(video.duration) || video.duration <= 0) return false;

    if (video.ended) return true;

    const remaining = video.duration - video.currentTime;
    return remaining <= FINISH_THRESHOLD_S;
  }

  function tick() {
    const currentVideoId = getCurrentShortId();
    const video = getActiveShortVideo();

    if (!currentVideoId || !video) return;

    if (shouldAdvance(video) && currentVideoId !== lastAdvancedVideoId) {
      const didAdvance = goToNextShort();
      if (didAdvance) {
        lastAdvancedVideoId = currentVideoId;
      }
      return;
    }

    if (currentVideoId !== lastAdvancedVideoId && video.currentTime < 1) {
      lastAdvancedVideoId = null;
    }
  }

  setInterval(tick, CHECK_INTERVAL_MS);
})();
