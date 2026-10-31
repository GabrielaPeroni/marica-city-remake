/**
 * Gerenciamento de usuários: tipo (moderador/regular) e conta ativa via AJAX,
 * com confirmação em <dialog>; exclusão pelo diálogo #delete-user.
 */

document.addEventListener('DOMContentLoaded', function () {
  const csrfToken = getCookie('csrftoken');
  const confirmDialog = document.getElementById('user-confirm');

  function askConfirm(message) {
    confirmDialog.querySelector('[data-confirm-message]').textContent = message;
    return new Promise(resolve => {
      let ok = false;
      confirmDialog.querySelector('[data-confirm]').onclick = () => {
        ok = true;
        confirmDialog.close();
      };
      confirmDialog.addEventListener('close', () => resolve(ok), { once: true });
      confirmDialog.showModal();
    });
  }

  function post(url) {
    return fetch(url, { method: 'POST', headers: { 'X-CSRFToken': csrfToken } }).then(
      response => response.json()
    );
  }

  document.querySelectorAll('.user-role-select').forEach(select => {
    select.addEventListener('change', async function () {
      const original = this.querySelector('option[selected]')?.value;
      const ok = await askConfirm(
        gettext(
          'Tem certeza que deseja alterar o tipo deste usuário? Isso pode modificar as permissões do usuário no sistema.'
        )
      );
      if (!ok) {
        this.value = original;
        return;
      }
      this.disabled = true;
      try {
        const data = await post(`/accounts/usuarios/${this.dataset.userId}/tipo/`);
        if (!data.success) throw new Error(data.error);
        this.querySelectorAll('option').forEach(opt => {
          opt.toggleAttribute(
            'selected',
            opt.value === (data.is_staff ? 'staff' : 'regular')
          );
        });
        this.value = data.is_staff ? 'staff' : 'regular';
        showToast(data.message, 'success');
      } catch (error) {
        this.value = original;
        showToast(
          error.message || gettext('Erro ao atualizar tipo de usuário'),
          'error'
        );
      } finally {
        this.disabled = false;
      }
    });
  });

  document.querySelectorAll('.toggle-status-btn').forEach(toggle => {
    toggle.addEventListener('change', async function () {
      const activating = this.checked;
      const ok = await askConfirm(
        activating
          ? gettext('Tem certeza que deseja ativar este usuário?')
          : gettext('Tem certeza que deseja desativar este usuário?')
      );
      if (!ok) {
        this.checked = !activating;
        return;
      }
      this.disabled = true;
      try {
        const data = await post(`/accounts/usuarios/${this.dataset.userId}/status/`);
        if (!data.success) throw new Error(data.error);
        this.checked = data.is_active;
        const label = document.querySelector(`.status-label-${this.dataset.userId}`);
        if (label) {
          label.textContent = data.is_active ? gettext('Ativo') : gettext('Inativo');
          label.classList.toggle('text-muted-foreground', !data.is_active);
        }
        showToast(data.message, 'success');
      } catch (error) {
        this.checked = !activating;
        showToast(error.message || gettext('Erro ao alterar status'), 'error');
      } finally {
        this.disabled = false;
      }
    });
  });

  // O link de excluir abre o diálogo (sem JS ele leva à página de confirmação)
  const deleteForm = document.getElementById('deleteUserForm');
  document.querySelectorAll('[data-delete-user]').forEach(link => {
    link.addEventListener('click', () => {
      deleteForm.action = link.getAttribute('href');
      document.querySelector('[data-delete-name]').textContent =
        link.dataset.deleteUser;
    });
  });
});
