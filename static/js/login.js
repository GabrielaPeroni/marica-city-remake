/**
 * MaricaCity - Gerenciador de Login Dropdown
 * Gerencia login baseado em AJAX com feedback no local no dropdown
 */

document.addEventListener('DOMContentLoaded', function () {
  // Impedir que os dropdowns fechem ao clicar dentro
  const loginDropdowns = document.querySelectorAll('.dropdown-menu');
  loginDropdowns.forEach(dropdown => {
    dropdown.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  });

  // Encontrar todos os formulários de login (de diferentes dropdowns)
  const loginForms = document.querySelectorAll('form[action*="accounts/login"]');

  loginForms.forEach(form => {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      const submitButton = form.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.textContent;

      // Desabilitar formulário durante o envio
      submitButton.disabled = true;
      submitButton.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>Entrando...';

      // Remover mensagens de erro existentes
      const existingError = form.querySelector('.alert-danger');
      if (existingError) {
        existingError.remove();
      }

      // Obter dados do formulário
      const formData = new FormData(form);

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
          },
        });

        const data = await response.json();

        if (data.success) {
          // Sucesso - fechar dropdown e recarregar página para mostrar estado logado
          submitButton.innerHTML = '<i class="bi bi-check-circle me-2"></i>Sucesso!';
          submitButton.classList.remove('btn-dark');
          submitButton.classList.add('btn-success');

          // Fechar o dropdown
          const dropdown = form.closest('.dropdown-menu');
          if (dropdown) {
            const dropdownToggle = dropdown.previousElementSibling;
            if (dropdownToggle && bootstrap && bootstrap.Dropdown) {
              const bsDropdown = bootstrap.Dropdown.getInstance(dropdownToggle);
              if (bsDropdown) {
                bsDropdown.hide();
              }
            }
          }

          // Armazenar flag para mostrar toast de sucesso após reload
          sessionStorage.setItem('loginSuccess', 'true');
          sessionStorage.setItem('loginUsername', data.username || 'usuário');

          // Recarregar página após breve atraso
          setTimeout(() => {
            location.reload();
          }, 500);
        } else {
          // Erro - mostrar mensagem de erro no formulário
          showErrorInForm(form, data.error || 'Erro ao fazer login.');

          // Reabilitar formulário
          submitButton.disabled = false;
          submitButton.textContent = originalButtonText;
        }
      } catch (error) {
        console.error('Erro de login:', error);
        showErrorInForm(form, 'Erro ao conectar com o servidor. Tente novamente.');

        // Reabilitar formulário
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
  // Remover qualquer erro existente
  const existingError = form.querySelector('.alert-danger');
  if (existingError) {
    existingError.remove();
  }

  // Criar alerta de erro
  const errorDiv = document.createElement('div');
  errorDiv.className = 'alert alert-danger alert-dismissible fade show mb-3';
  errorDiv.setAttribute('role', 'alert');
  errorDiv.innerHTML = `
    <i class="bi bi-exclamation-triangle me-2"></i>${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  // Inserir no início do formulário
  form.insertBefore(errorDiv, form.firstChild);

  // Animação de vibração para erro
  form.style.animation = 'shake 0.3s ease';
  setTimeout(() => {
    form.style.animation = '';
  }, 300);
}

// Adicionar CSS de animação de vibração se ainda não estiver presente
if (!document.getElementById('login-shake-styles')) {
  const style = document.createElement('style');
  style.id = 'login-shake-styles';
  style.textContent = `
    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      25% { transform: translateX(-10px); }
      75% { transform: translateX(10px); }
    }
  `;
  document.head.appendChild(style);
}
