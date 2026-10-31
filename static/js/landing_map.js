// Mapa da página inicial (Leaflet + OpenStreetMap) com todos os lugares, montado quando entra na tela
(function () {
  const container = document.getElementById('landing-map');
  const L = window.L;
  if (!container || !L) return;

  const MARICA = [-22.9194, -42.8186];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function popupFor(place) {
    const card = el('a', 'block w-60 text-foreground no-underline');
    card.href = place.url;

    if (place.image_url) {
      const img = el('img', 'mb-3 h-32 w-full rounded-lg bg-muted object-cover');
      img.src = place.image_url;
      img.alt = '';
      card.append(img);
    }
    card.append(
      el('h3', 'font-display text-base font-semibold leading-snug', place.name)
    );

    if (place.rating) {
      const rating = el('p', 'mt-1 flex items-center gap-1 text-sm');
      rating.append(
        el('span', 'text-star', '★'),
        el('span', 'font-semibold', place.rating.toFixed(1)),
        el(
          'span',
          'text-muted-foreground',
          interpolate(
            ngettext('(%s avaliação)', '(%s avaliações)', place.review_count),
            [place.review_count]
          )
        )
      );
      card.append(rating);
    }
    if (place.description) {
      card.append(
        el('p', 'mt-2 line-clamp-3 text-sm text-muted-foreground', place.description)
      );
    }
    card.append(
      el(
        'span',
        'mt-3 inline-block text-sm font-semibold text-brand',
        gettext('Ver detalhes')
      )
    );
    return card;
  }

  async function mount() {
    container.replaceChildren();
    container.removeAttribute('aria-busy');
    const map = L.map(container, { scrollWheelZoom: false }).setView(MARICA, 12);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      referrerPolicy: 'strict-origin-when-cross-origin',
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    const brand = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue('--brand')
      .trim();

    try {
      const response = await fetch('/explore/api/map-data/');
      const data = await response.json();
      const places = (data.places || []).filter(
        p => Number.isFinite(p.latitude) && Number.isFinite(p.longitude)
      );
      const points = places.map(place => {
        const point = [place.latitude, place.longitude];
        L.circleMarker(point, {
          radius: 9,
          color: 'white',
          weight: 3,
          fillColor: brand,
          fillOpacity: 1,
        })
          .addTo(map)
          .bindTooltip(place.name, { direction: 'top', offset: [0, -8] })
          .bindPopup(popupFor(place), { maxWidth: 260 });
        return point;
      });
      if (points.length > 1) map.fitBounds(points, { padding: [32, 32] });
      else if (points.length === 1) map.setView(points[0], 15);
    } catch (error) {
      console.error('Erro ao buscar dados dos locais:', error);
    }
  }

  const observer = new window.IntersectionObserver(
    entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        mount();
      }
    },
    { rootMargin: '200px' }
  );
  observer.observe(container);
})();
