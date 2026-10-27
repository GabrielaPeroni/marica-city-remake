/*
 * Bulk selection for staff lists. Works on any <form data-bulk-form>:
 *   [data-bulk-item]    row checkbox (may sit outside the form via form="id")
 *   [data-bulk-all]     select-all checkbox
 *   [data-bulk-count]   element that shows "N selecionados"
 *   [data-bulk-action]  submit buttons, disabled while nothing is selected
 *   [data-bulk-confirm] message shown in a confirmation modal (%s = selected count)
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
      if (bar) bar.classList.toggle('is-active', checked > 0);
    }

    all.forEach(box =>
      box.addEventListener('change', () => {
        items.forEach(el => {
          el.checked = box.checked;
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
      const cell = el.closest('td, .bulk-select-row');
      if (!cell || cell.tagName === 'LABEL') return;
      cell.classList.add('bulk-cell');
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
        if (comments.hidden) comments.value = '';
      };
      reason.addEventListener('change', toggle);
      toggle();
    }

    update();
  }

  // Bootstrap modal built once and reused: "Cancelar" / the action's own label
  let dialog = null;
  function confirmDialog(btn, message, extraFields) {
    if (!dialog) {
      const el = document.createElement('div');
      el.className = 'modal fade';
      el.tabIndex = -1;
      el.setAttribute('aria-labelledby', 'bulkConfirmTitle');
      el.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header">
              <h2 class="modal-title h5" id="bulkConfirmTitle"></h2>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body"><p></p></div>
            <div class="modal-footer">
              <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal"></button>
              <button type="button" class="btn" data-confirm></button>
            </div>
          </div>
        </div>`;
      document.body.appendChild(el);
      el.querySelector('.btn-close').setAttribute('aria-label', gettext('Fechar'));
      el.querySelector('[data-bs-dismiss].btn-outline-secondary').textContent =
        gettext('Cancelar');
      dialog = { el, modal: new bootstrap.Modal(el) };
    }
    const { el, modal } = dialog;
    const label = btn.textContent.trim();
    el.querySelector('.modal-title').textContent = label;
    el.querySelector('.modal-body p').textContent = message;
    const ok = el.querySelector('[data-confirm]');
    ok.textContent = label;
    ok.className = `btn ${
      btn.dataset.bulkTone === 'danger' ? 'btn-danger' : 'btn-dark'
    }`;
    // Campos extras (ex.: motivo da remoção) entram no popup e voltam ao formulário ao fechar
    const home = extraFields && extraFields.parentElement;
    if (extraFields) {
      el.querySelector('.modal-body').appendChild(extraFields);
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
        modal.hide();
      };
      el.addEventListener(
        'hidden.bs.modal',
        () => {
          if (extraFields) {
            extraFields.hidden = true;
            home.appendChild(extraFields);
          }
          resolve(confirmed);
        },
        { once: true }
      );
      modal.show();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-bulk-form]').forEach(init);
  });
})();
