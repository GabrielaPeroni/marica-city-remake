/**
 * Google Maps Interativo para Página Inicial
 * Mostra todos os locais com marcadores clicáveis e janelas de informação
 */

let landingMap;
let markers = [];
let infoWindow;

async function initLandingMap() {
  const mapContainer = document.getElementById('landing-map');

  if (!mapContainer) {
    return;
  }

  // Centro padrão (Maricá, Brasil)
  const defaultCenter = { lat: -22.9194, lng: -42.8186 };

  mapContainer.replaceChildren();
  mapContainer.removeAttribute('aria-busy');
  landingMap = new google.maps.Map(mapContainer, {
    center: defaultCenter,
    zoom: 12,
    mapTypeControl: true,
    mapTypeControlOptions: {
      style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
      position: google.maps.ControlPosition.TOP_RIGHT,
    },
    streetViewControl: true,
    fullscreenControl: true,
    zoomControl: true,
  });

  // Criar instância única de janela de informação (reutilizada para todos os marcadores)
  infoWindow = new google.maps.InfoWindow();

  // Buscar dados dos locais
  try {
    const response = await fetch('/explore/api/map-data/');
    const data = await response.json();

    if (data.places && data.places.length > 0) {
      // Criar marcadores para todos os locais
      createMarkers(data.places);

      // Ajustar mapa para mostrar todos os marcadores
      fitMapToMarkers();
    }

    // Atualizar contagem de locais
    updatePlaceCount(data.count);
  } catch (error) {
    console.error('Erro ao buscar dados dos locais:', error);
  }
}

function createMarkers(places) {
  places.forEach(place => {
    const marker = new google.maps.Marker({
      position: { lat: place.latitude, lng: place.longitude },
      map: landingMap,
      title: place.name,
      animation: google.maps.Animation.DROP,
    });

    // Armazenar dados do local com o marcador
    marker.placeData = place;

    // Adicionar ouvinte de clique para mostrar janela de informação
    marker.addListener('click', () => {
      showInfoWindow(marker);
    });

    markers.push(marker);
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function showInfoWindow(marker) {
  const place = marker.placeData;
  const card = el('a', 'block w-64 text-foreground no-underline');
  card.href = place.url;

  if (place.image_url) {
    const img = el('img', 'mb-3 h-36 w-full rounded-lg bg-muted object-cover');
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
        interpolate(ngettext('(%s avaliação)', '(%s avaliações)', place.review_count), [
          place.review_count,
        ])
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

  infoWindow.setContent(card);
  infoWindow.open(landingMap, marker);
}

function fitMapToMarkers() {
  if (markers.length === 0) return;

  const bounds = new google.maps.LatLngBounds();
  markers.forEach(marker => {
    bounds.extend(marker.getPosition());
  });

  landingMap.fitBounds(bounds);

  // Não dar zoom demais se houver apenas um marcador
  if (markers.length === 1) {
    landingMap.setZoom(15);
  }
}

function updatePlaceCount(count) {
  const countElement = document.getElementById('map-place-count');
  if (countElement) {
    countElement.textContent = count;
  }
}

// Tornar função globalmente disponível para callback do Google Maps
window.initLandingMap = initLandingMap;
