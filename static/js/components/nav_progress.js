// Slim top bar while the next page loads (only when it takes longer than a blink).
(function () {
  const bar = document.createElement('div');
  bar.className = 'nav-progress';
  bar.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar);
  let timer = null;

  function start() {
    clearTimeout(timer);
    timer = setTimeout(() => bar.classList.add('is-loading'), 120);
  }

  function reset() {
    clearTimeout(timer);
    bar.classList.remove('is-loading');
  }

  document.addEventListener('click', e => {
    const link = e.target.closest('a[href]');
    if (!link || e.defaultPrevented || e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (link.target && link.target !== '_self') return;
    if (link.hasAttribute('download') || link.origin !== location.origin) return;
    const url = new URL(link.href);
    if (url.pathname === location.pathname && url.search === location.search) return;
    start();
  });

  // Runs after other submit handlers, so AJAX forms (preventDefault) are skipped
  document.addEventListener('submit', e => {
    setTimeout(() => {
      if (!e.defaultPrevented) start();
    }, 0);
  });

  window.addEventListener('pageshow', reset);
  window.addEventListener('pagehide', reset);
})();
