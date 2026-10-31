// Navbar transparente sobre o hero vira barra branca ao rolar (data-scrolled)
(function () {
  const nav = document.querySelector('[data-site-nav]');
  if (!nav) return;
  const update = () => nav.toggleAttribute('data-scrolled', window.scrollY > 8);
  update();
  window.addEventListener('scroll', update, { passive: true });
})();
