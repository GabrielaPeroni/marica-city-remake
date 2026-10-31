/* Página inicial: carrossel do hero e trilho de lugares "Onde ir" (Swiper) */

const HERO_DELAY = 5000;

function initHero() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const hero = new Swiper('.hero-swiper', {
    loop: true,
    effect: 'fade',
    fadeEffect: { crossFade: true },
    speed: reduceMotion ? 0 : 700,
    autoplay: reduceMotion
      ? false
      : { delay: HERO_DELAY, disableOnInteraction: false, pauseOnMouseEnter: true },
    keyboard: { enabled: true, onlyInViewport: true },
    a11y: {
      prevSlideMessage: gettext('Slide anterior'),
      nextSlideMessage: gettext('Próximo slide'),
      paginationBulletMessage: gettext('Ir para o slide {{index}}'),
    },
    pagination: {
      el: document.querySelector('.hero-pagination'),
      clickable: true,
      bulletClass: 'hero-dot',
      bulletActiveClass: 'is-active',
    },
    threshold: 10,
  });

  const pauseBtn = document.querySelector('.hero-pause-btn');
  if (!pauseBtn) return;
  const setPaused = paused => {
    pauseBtn.setAttribute('aria-pressed', String(paused));
    pauseBtn.setAttribute(
      'aria-label',
      paused ? gettext('Retomar apresentação') : gettext('Pausar apresentação')
    );
  };
  setPaused(reduceMotion);
  pauseBtn.addEventListener('click', () => {
    const paused = pauseBtn.getAttribute('aria-pressed') === 'true';
    if (paused) {
      hero.params.autoplay = { delay: HERO_DELAY, disableOnInteraction: false };
      hero.autoplay.start();
    } else {
      hero.autoplay.stop();
    }
    setPaused(!paused);
  });
}

function initFeatured() {
  if (!document.querySelector('.featured-swiper')) return;
  new Swiper('.featured-swiper', {
    slidesPerView: 'auto',
    spaceBetween: 20,
    grabCursor: true,
    freeMode: true,
    mousewheel: { forceToAxis: true },
    a11y: { enabled: true },
  });
}

function initLanding() {
  initHero();
  initFeatured();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initLanding);
} else {
  initLanding();
}
