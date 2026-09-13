/**
 * JavaScript de Gerenciamento de Usuários
 * Gerencia operações AJAX para atualizações de tipo de usuário e alternâncias de status
 */

document.addEventListener('DOMContentLoaded', function () {
  const csrfToken = getCookie('csrftoken');

  // Gerenciar mudança de função de usuário (alternar entre staff e regular)
  const userRoleSelects = document.querySelectorAll('.user-role-select');
  userRoleSelects.forEach(select => {
    select.addEventListener('change', function () {
      const userId = this.dataset.userId;
      const originalRole = this.querySelector('option[selected]')?.value;

      if (
        !confirm(
          'Tem certeza que deseja alterar o tipo deste usuário?\n\nIsso pode modificar as permissões do usuário no sistema.'
        )
      ) {
        this.value = originalRole;
        return;
      }

      // Desabilitar select durante a requisição
      this.disabled = true;

      fetch(`/accounts/usuarios/${userId}/tipo/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Mostrar mensagem de sucesso
            showNotification('success', data.message);

            // Atualizar a opção selecionada com base na resposta
            const options = this.querySelectorAll('option');
            options.forEach(opt => {
              opt.removeAttribute('selected');
              if (
                (data.is_staff && opt.value === 'staff') ||
                (!data.is_staff && opt.value === 'regular')
              ) {
                opt.setAttribute('selected', 'selected');
              }
            });
          } else {
            // Reverter para função original
            this.value = originalRole;
            showNotification(
              'error',
              data.error || 'Erro ao atualizar tipo de usuário'
            );
          }
        })
        .catch(error => {
          console.error('Erro:', error);
          this.value = originalRole;
          showNotification('error', 'Erro ao processar solicitação');
        })
        .finally(() => {
          this.disabled = false;
        });
    });
  });

  // Gerenciar alternância de status
  const statusButtons = document.querySelectorAll('.toggle-status-btn');
  statusButtons.forEach(button => {
    button.addEventListener('click', function () {
      const userId = this.dataset.userId;
      const row = document.getElementById(`user-row-${userId}`);
      const statusBadge = row.querySelector(`.status-badge-${userId}`);
      const isActive = statusBadge.classList.contains('bg-success');

      const action = isActive ? 'desativar' : 'ativar';
      if (!confirm(`Tem certeza que deseja ${action} este usuário?`)) {
        return;
      }

      // Desabilitar botão durante a requisição
      this.disabled = true;

      fetch(`/accounts/usuarios/${userId}/status/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
        },
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Atualizar badge
            if (data.is_active) {
              statusBadge.classList.remove('bg-secondary');
              statusBadge.classList.add('bg-success');
              statusBadge.textContent = 'Ativo';
              this.innerHTML = '<i class="bi bi-x-circle"></i>';
            } else {
              statusBadge.classList.remove('bg-success');
              statusBadge.classList.add('bg-secondary');
              statusBadge.textContent = 'Inativo';
              this.innerHTML = '<i class="bi bi-check-circle"></i>';
            }

            showNotification('success', data.message);
          } else {
            showNotification('error', data.error || 'Erro ao alterar status');
          }
        })
        .catch(error => {
          console.error('Erro:', error);
          showNotification('error', 'Erro ao processar solicitação');
        })
        .finally(() => {
          this.disabled = false;
        });
    });
  });

  /**
   * Mostrar mensagem de notificação
   * @param {string} type - 'success' ou 'error'
   * @param {string} message - Mensagem para exibir
   */
  function showNotification(type, message) {
    // Criar elemento de notificação
    const notification = document.createElement('div');
    notification.className = `alert alert-${
      type === 'success' ? 'success' : 'danger'
    } alert-dismissible fade show position-fixed`;
    notification.style.cssText =
      'top: 20px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    notification.innerHTML = `
      <i class="bi bi-${
        type === 'success' ? 'check-circle' : 'exclamation-circle'
      } me-2"></i>
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Remover automaticamente após 5 segundos
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 150);
    }, 5000);
  }
});
