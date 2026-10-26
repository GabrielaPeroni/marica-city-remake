/**
 * MaricaCity - Componente de Toast
 * Mostra automaticamente mensagens de toast do Bootstrap
 */

document.addEventListener('DOMContentLoaded', function () {
  // Mostrar toasts existentes (do Django messages)
  const toastElList = [].slice.call(document.querySelectorAll('.toast'));
  const toastList = toastElList.map(function (toastEl) {
    return new bootstrap.Toast(toastEl);
  });
  toastList.forEach(toast => toast.show());

  // Verificar se houve login bem-sucedido
  if (sessionStorage.getItem('loginSuccess') === 'true') {
    const username = sessionStorage.getItem('loginUsername') || 'usuário';
    showLoginSuccessToast(username);

    // Limpar flags
    sessionStorage.removeItem('loginSuccess');
    sessionStorage.removeItem('loginUsername');
  }
});

/**
 * Mostrar toast de sucesso de login
 * @param {string} username - Nome do usuário que fez login
 */
function showLoginSuccessToast(username) {
  // Criar elemento de toast
  const toastEl = document.createElement('div');
  toastEl.className = 'toast align-items-center text-white bg-success border-0';
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');
  toastEl.setAttribute('data-bs-autohide', 'true');
  toastEl.setAttribute('data-bs-delay', '5000');

  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${interpolate(gettext('Bem-vindo de volta, %s!'), [username])}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="${gettext(
        'Fechar'
      )}"></button>
    </div>
  `;

  // Adicionar ao container de toasts
  let toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '9999';
    document.body.appendChild(toastContainer);
  }

  toastContainer.appendChild(toastEl);

  // Mostrar toast
  const toast = new bootstrap.Toast(toastEl);
  toast.show();

  // Remover elemento do DOM após ser ocultado
  toastEl.addEventListener('hidden.bs.toast', function () {
    toastEl.remove();
  });
}
