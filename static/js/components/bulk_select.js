/*
 * Bulk selection for staff lists. Works on any <form data-bulk-form>:
 *   [data-bulk-item]    row checkbox (may sit outside the form via form="id")
 *   [data-bulk-all]     select-all checkbox
 *   [data-bulk-count]   element that shows "N selecionados"
 *   [data-bulk-bar]     toolbar; gets data-active while something is selected
 *   [data-bulk-action]  submit buttons, disabled while nothing is selected
 *   [data-bulk-confirm] message shown in a confirmation dialog (%s = selected count)
 *   data-bulk-tone="danger" on a button: red confirm button
 *   data-bulk-require="reason"  on a button: the removal reason is required
 * Without JS the form still submits normally.
 */
(function () {
  function init(form) {
    const field = attr => Array.from(form.elements).filter(el => el.hasAttribute(attr));
    const items = field('data-bulk-item');
    const all = field('data-bulk-all');
    const buttons = field('data-bulk-action');
    const counters = document.querySelectorAll(`[data-bulk-count="${form.id}"]`);
    const bar = form.querySelector('[data-bulk-bar]');
    const reason = form.querySelector('[name="reason"]');
    const comments = form.querySelector('[name="comments"]');
    const reasonFields = form.querySelector('[data-bulk-reason]');

    function update() {
      const checked = items.filter(el => el.checked).length;
      all.forEach(box => {
        box.checked = items.length > 0 && checked === items.length;
        box.indeterminate = checked > 0 && checked < items.length;
      });
      buttons.forEach(btn => {
        btn.disabled = checked === 0;
      });
      counters.forEach(el => {
        const label = ngettext('%s selecionado', '%s selecionados', checked);
        el.textContent = interpolate(label, [checked]);
      });
      items.forEach(el => {
        const row = el.closest('tr, article');
        if (row) row.toggleAttribute('data-selected', el.checked);
      });
      if (bar) bar.toggleAttribute('data-active', checked > 0);
    }

    all.forEach(box =>
      box.addEventListener('change', () => {
        items.forEach(el => {
          if (!el.disabled) el.checked = box.checked;
        });
        update();
      })
    );
    items.forEach(el => el.addEventListener('change', update));

    // Shift+clique marca/desmarca o intervalo desde o último item clicado
    let last = null;
    items.forEach(el =>
      el.addEventListener('click', event => {
        const enabled = items.filter(i => !i.disabled);
        if (event.shiftKey && last && last !== el) {
          const [a, b] = [enabled.indexOf(last), enabled.indexOf(el)].sort(
            (x, y) => x - y
          );
          if (a >= 0 && b >= 0)
            enabled.slice(a, b + 1).forEach(i => (i.checked = el.checked));
          update();
        }
        last = el;
      })
    );

    // A célula inteira do checkbox é clicável (alvo maior que a caixinha)
    items.forEach(el => {
      const cell = el.closest('td');
      if (!cell) return;
      cell.classList.add('cursor-pointer');
      cell.addEventListener('click', event => {
        if (event.target === cell && !el.disabled) el.click();
      });
    });

    buttons.forEach(btn =>
      btn.addEventListener('click', event => {
        if (reason && comments) {
          const needsReason = btn.dataset.bulkRequire === 'reason';
          reason.required = needsReason;
          comments.required = needsReason && reason.value === 'Outros';
        }
        const message = btn.dataset.bulkConfirm;
        if (!message) return;
        event.preventDefault();
        const needsReason = btn.dataset.bulkRequire === 'reason' && reasonFields;
        if (!needsReason && !form.reportValidity()) return;
        const count = items.filter(el => el.checked).length;
        confirmDialog(
          btn,
          interpolate(message, [count]),
          needsReason ? reasonFields : null
        ).then(ok => {
          if (ok) form.requestSubmit(btn);
        });
      })
    );

    if (reason && comments) {
      const toggle = () => {
        comments.hidden = reason.value !== 'Outros';
        comments.required = !comments.hidden && reason.required;
        if (comments.hidden) comments.value = '';
      };
      reason.addEventListener('change', toggle);
      toggle();
    }

    update();
  }

  // <dialog> criado uma vez e reaproveitado: "Cancelar" / o rótulo da própria ação
  let dialog = null;
  function buildDialog() {
    const el = document.createElement('dialog');
    el.className = 'dialog';
    el.id = 'bulk-confirm';
    el.setAttribute('aria-labelledby', 'bulk-confirm-title');
    el.innerHTML = `
      <div class="sm:max-w-md">
        <header><h2 id="bulk-confirm-title" class="font-display text-xl font-semibold"></h2></header>
        <section><p data-message></p></section>
        <footer>
          <button type="button" class="btn" data-variant="outline" data-dialog-close></button>
          <button type="button" class="btn" data-confirm></button>
        </footer>
        <button type="button" class="btn" data-variant="ghost" data-size="icon-sm" data-dialog-close></button>
      </div>`;
    const cancel = el.querySelector('footer [data-dialog-close]');
    cancel.textContent = gettext('Cancelar');
    const close = el.querySelector('div > [data-dialog-close]');
    close.setAttribute('aria-label', gettext('Fechar'));
    const x = cloneIcon('x');
    if (x) close.appendChild(x);
    document.body.appendChild(el);
    return el;
  }

  function confirmDialog(btn, message, extraFields) {
    dialog = dialog || buildDialog();
    const label = btn.textContent.trim();
    dialog.querySelector('h2').textContent = label;
    dialog.querySelector('[data-message]').textContent = message;
    const ok = dialog.querySelector('[data-confirm]');
    ok.textContent = label;
    if (btn.dataset.bulkTone === 'danger') ok.dataset.variant = 'destructive';
    else delete ok.dataset.variant;
    // Campos extras (ex.: motivo da remoção) entram no diálogo e voltam ao formulário ao fechar
    const home = extraFields && extraFields.parentElement;
    if (extraFields) {
      dialog.querySelector('section').appendChild(extraFields);
      extraFields.hidden = false;
    }
    return new Promise(resolve => {
      let confirmed = false;
      ok.onclick = () => {
        if (extraFields) {
          const invalid = [...extraFields.querySelectorAll('select, input')].find(
            f => !f.checkValidity()
          );
          if (invalid) {
            invalid.reportValidity();
            return;
          }
        }
        confirmed = true;
        dialog.close();
      };
      dialog.addEventListener(
        'close',
        () => {
          if (extraFields) {
            extraFields.hidden = true;
            home.appendChild(extraFields);
          }
          resolve(confirmed);
        },
        { once: true }
      );
      dialog.showModal();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-bulk-form]').forEach(init);
  });
})();
