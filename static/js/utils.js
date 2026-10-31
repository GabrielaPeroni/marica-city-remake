/**
 * MaricaCity - Utilitários Compartilhados
 * Funções comuns usadas em toda a aplicação
 */

/**
 * Obter token CSRF do cookie
 * @param {string} name - Nome do cookie
 * @returns {string|null} Valor do cookie
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Cópia de um ícone Lucide de <template id="js-icons"> (includes/js_icons.html)
 * @param {string} name - Nome do ícone, ex. "check"
 * @returns {SVGElement|null}
 */
function cloneIcon(name) {
  const template = document.getElementById('js-icons');
  const svg = template && template.content.querySelector(`[data-icon="${name}"]`);
  return svg ? svg.cloneNode(true) : null;
}

// Exportar para uso em outros scripts
if (typeof window !== 'undefined') {
  window.getCookie = getCookie;
  window.cloneIcon = cloneIcon;
}
