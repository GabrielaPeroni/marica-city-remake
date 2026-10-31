/**
 * MaricaCity - Toasts (Basecoat)
 * As mensagens do Django já vêm renderizadas em #toaster; showToast() cria novas pelo JS.
 */

function escapeHtml(text) {
  const span = document.createElement('span');
  span.textContent = text;
  return span.innerHTML;
}

/**
 * Mostrar um toast
 * @param {string} message - Texto (escapado)
 * @param {'success'|'error'|'warning'|'info'} category - Tipo do toast
 */
function showToast(message, category = 'info') {
  const toaster = document.getElementById('toaster');
  if (!toaster || typeof toaster.toast !== 'function') return;
  toaster.toast({ category, title: escapeHtml(message), duration: 5000 });
}

/**
 * Mostrar toast de sucesso de login
 * @param {string} username - Nome do usuário que fez login
 */
function showLoginSuccessToast(username) {
  showToast(interpolate(gettext('Bem-vindo de volta, %s!'), [username]), 'success');
}

window.showToast = showToast;
window.showLoginSuccessToast = showLoginSuccessToast;

document.addEventListener('DOMContentLoaded', function () {
  if (sessionStorage.getItem('loginSuccess') === 'true') {
    showLoginSuccessToast(
      sessionStorage.getItem('loginUsername') || gettext('usuário')
    );
    sessionStorage.removeItem('loginSuccess');
    sessionStorage.removeItem('loginUsername');
  }
});
