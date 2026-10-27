/*
 * Bulk selection for staff lists. Works on any <form data-bulk-form>:
 *   [data-bulk-item]    row checkbox (may sit outside the form via form="id")
 *   [data-bulk-all]     select-all checkbox
 *   [data-bulk-count]   element that shows "N selecionados"
 *   [data-bulk-action]  submit buttons, disabled while nothing is selected
 *   [data-bulk-confirm] message for confirm() before submitting
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

    buttons.forEach(btn =>
      btn.addEventListener('click', event => {
        const message = btn.dataset.bulkConfirm;
        if (message && !confirm(message)) {
          event.preventDefault();
          return;
        }
        if (reason && comments) {
          const needsReason = btn.dataset.bulkRequire === 'reason';
          reason.required = needsReason;
          comments.required = needsReason && reason.value === 'Outros';
        }
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

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-bulk-form]').forEach(init);
  });
})();
