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

  let dialog = null;
  function ask() {
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.className = 'dialog';
      dialog.setAttribute('aria-labelledby', 'unsaved-guard-title');
      dialog.innerHTML = `
        <div class="sm:max-w-sm">
          <header><h2 id="unsaved-guard-title" class="font-display text-xl font-semibold"></h2><p class="text-muted-foreground"></p></header>
          <footer>
            <button type="button" class="btn" data-variant="outline" value="leave"></button>
            <button type="button" class="btn" value="stay" autofocus></button>
          </footer>
        </div>`;
      dialog.querySelector('h2').textContent = gettext('Sair sem salvar?');
      dialog.querySelector('header p').textContent = gettext(
        'Você fez alterações neste formulário. Se sair agora, elas serão perdidas.'
      );
      dialog.querySelector('[value=stay]').textContent = gettext('Continuar editando');
      dialog.querySelector('[value=leave]').textContent = gettext('Descartar e sair');
      dialog.addEventListener('click', event => {
        const button = event.target.closest('button[value]');
        if (button) dialog.close(button.value);
        else if (event.target === dialog) dialog.close('stay');
      });
      document.body.appendChild(dialog);
    }
    return new Promise(resolve => {
      dialog.returnValue = '';
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'leave'), {
        once: true,
      });
      dialog.showModal();
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
