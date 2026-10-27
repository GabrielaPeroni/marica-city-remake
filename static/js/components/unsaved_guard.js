// Forms with [data-unsaved-guard]: leaving after editing asks first (links in-page get a dialog,
// closing the tab or the browser's back button get the browser's own prompt).
(function () {
  const forms = [...document.querySelectorAll('form[data-unsaved-guard]')];
  if (!forms.length) return;
  let dirty = false;
  let submitting = false;

  forms.forEach(form => {
    form.addEventListener('input', () => (dirty = true));
    form.addEventListener('change', () => (dirty = true));
    form.addEventListener('submit', () => (submitting = true));
  });

  window.addEventListener('beforeunload', event => {
    if (dirty && !submitting) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  let modal = null;
  function ask() {
    if (!modal) {
      const el = document.createElement('div');
      el.className = 'modal fade';
      el.tabIndex = -1;
      el.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header"><h2 class="modal-title h5"></h2></div>
            <div class="modal-body"><p class="mb-0"></p></div>
            <div class="modal-footer">
              <button type="button" class="btn btn-dark" data-bs-dismiss="modal"></button>
              <button type="button" class="btn btn-outline-danger" data-leave></button>
            </div>
          </div>
        </div>`;
      document.body.appendChild(el);
      el.querySelector('.modal-title').textContent = gettext('Sair sem salvar?');
      el.querySelector('.modal-body p').textContent = gettext(
        'Você fez alterações neste formulário. Se sair agora, elas serão perdidas.'
      );
      el.querySelector('[data-bs-dismiss]').textContent = gettext('Continuar editando');
      el.querySelector('[data-leave]').textContent = gettext('Descartar e sair');
      modal = { el, bs: new bootstrap.Modal(el) };
    }
    return new Promise(resolve => {
      let leave = false;
      modal.el.querySelector('[data-leave]').onclick = () => {
        leave = true;
        modal.bs.hide();
      };
      modal.el.addEventListener('hidden.bs.modal', () => resolve(leave), {
        once: true,
      });
      modal.bs.show();
    });
  }

  // Capture phase: runs before the progress bar and other link handlers
  document.addEventListener(
    'click',
    event => {
      const link = event.target.closest('a[href]');
      if (!dirty || submitting || !link || event.defaultPrevented) return;
      if (link.target === '_blank' || link.getAttribute('href').startsWith('#')) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0)
        return;
      event.preventDefault();
      event.stopPropagation();
      ask().then(leave => {
        if (!leave) return;
        dirty = false;
        location.href = link.href;
      });
    },
    true
  );
})();
