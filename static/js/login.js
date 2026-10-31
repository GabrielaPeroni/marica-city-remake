/**
 * MaricaCity - Login no popover da navbar
 * Envia o formulário por AJAX e mostra o erro dentro do próprio popover
 */

document.addEventListener('DOMContentLoaded', function () {
  const loginForms = document.querySelectorAll('form[action*="accounts/login"]');

  loginForms.forEach(form => {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      const submitButton = form.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.textContent;

      submitButton.disabled = true;
      submitButton.replaceChildren(
        cloneIcon('loader-circle') || '',
        document.createTextNode(gettext('Entrando...'))
      );
      form.querySelector('[data-login-error]')?.remove();

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await response.json();

        if (data.success) {
          submitButton.replaceChildren(
            cloneIcon('check') || '',
            document.createTextNode(gettext('Sucesso!'))
          );
          sessionStorage.setItem('loginSuccess', 'true');
          sessionStorage.setItem('loginUsername', data.username || gettext('usuário'));
          setTimeout(() => location.reload(), 500);
        } else {
          showErrorInForm(form, data.error || gettext('Erro ao fazer login.'));
          submitButton.disabled = false;
          submitButton.textContent = originalButtonText;
        }
      } catch (error) {
        console.error('Erro de login:', error);
        showErrorInForm(
          form,
          gettext('Erro ao conectar com o servidor. Tente novamente.')
        );
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
      }
    });
  });
});

/**
 * Exibir mensagem de erro dentro do formulário
 * @param {HTMLFormElement} form - O elemento do formulário
 * @param {string} message - Mensagem de erro para exibir
 */
function showErrorInForm(form, message) {
  form.querySelector('[data-login-error]')?.remove();

  const alert = document.createElement('div');
  alert.className = 'alert';
  alert.dataset.variant = 'destructive';
  alert.dataset.loginError = '';
  alert.setAttribute('role', 'alert');
  const text = document.createElement('section');
  text.textContent = message;
  alert.append(cloneIcon('circle-alert') || '', text);
  form.prepend(alert);

  form.classList.remove('animate-shake');
  void form.offsetWidth;
  form.classList.add('animate-shake');
}
