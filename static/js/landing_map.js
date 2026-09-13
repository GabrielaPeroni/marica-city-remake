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

  // Inicializar mapa
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

function showInfoWindow(marker) {
  const place = marker.placeData;

  // Construir conteúdo da janela de informação
  let content = `
    <div style="max-width: 280px; padding: 8px;">
      ${
        place.image_url
          ? `
        <img src="${place.image_url}" alt="${place.name}"
             style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px; margin-bottom: 12px;">
      `
          : ''
      }

      <h6 style="margin: 0 0 8px 0; font-weight: 600; color: #212529;">
        ${place.category_icon} ${place.name}
      </h6>

      ${
        place.rating
          ? `
        <div style="margin-bottom: 8px;">
          <span style="color: #ffc107; font-size: 14px;">★</span>
          <span style="font-weight: 600; font-size: 14px;">${place.rating.toFixed(
            1
          )}</span>
          <span style="color: #6c757d; font-size: 13px;">(${
            place.review_count
          } avaliações)</span>
        </div>
      `
          : ''
      }

      <p style="margin: 0 0 12px 0; font-size: 14px; color: #6c757d; line-height: 1.4;">
        ${place.description}
      </p>

      <a href="${place.url}"
         style="display: inline-block; padding: 8px 16px; background: #212529; color: white;
                text-decoration: none; border-radius: 4px; font-size: 14px; font-weight: 500;">
        Ver Detalhes →
      </a>
    </div>
  `;

  infoWindow.setContent(content);
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
