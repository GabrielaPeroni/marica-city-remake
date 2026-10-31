// Telas de conta: código de 6 dígitos em caixas e o link "Entrar" que abre o menu de login
document.addEventListener('click', e => {
  if (!e.target.closest('[data-open-login]')) return;
  const trigger = document.getElementById('login-popover-trigger');
  if (!trigger) return;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  // Depois deste clique, senão o "clique fora" do popover o fecha na hora
  setTimeout(() => trigger.click());
});

// O input original (name="code") continua sendo o enviado; as caixas só o preenchem
function setupOtp(field) {
  const source = field.querySelector('input[name="code"]');
  if (!source) return;
  const length = 6;
  const group = document.createElement('div');
  group.className = 'grid grid-cols-6 gap-2 sm:gap-3';
  group.setAttribute('role', 'group');
  const label = field.querySelector('label');
  if (label) {
    label.id ||= `${source.id}-label`;
    group.setAttribute('aria-labelledby', label.id);
  }

  const boxes = Array.from({ length }, (_, i) => {
    const box = document.createElement('input');
    box.type = 'text';
    box.inputMode = 'numeric';
    box.autocomplete = i === 0 ? 'one-time-code' : 'off';
    box.className =
      'input h-14 w-full px-0 text-center text-2xl font-semibold tabular-nums sm:h-16';
    box.setAttribute(
      'aria-label',
      interpolate(
        gettext('Dígito %(n)s de %(total)s'),
        { n: i + 1, total: length },
        true
      )
    );
    if (source.getAttribute('aria-invalid')) box.setAttribute('aria-invalid', 'true');
    group.appendChild(box);
    return box;
  });

  const sync = () => {
    source.value = boxes.map(b => b.value).join('');
  };

  const fill = (digits, start) => {
    let i = start;
    for (const d of digits) {
      if (i >= length) break;
      boxes[i++].value = d;
    }
    sync();
    boxes[Math.min(i, length - 1)].focus();
  };

  boxes.forEach((box, i) => {
    box.addEventListener('input', () => {
      const digits = box.value.replace(/\D/g, '');
      box.value = '';
      if (digits) fill(digits, digits.length >= length ? 0 : i);
      else sync();
    });
    box.addEventListener('keydown', e => {
      if (e.key === 'Backspace' && !box.value && i > 0) {
        e.preventDefault();
        boxes[i - 1].value = '';
        boxes[i - 1].focus();
        sync();
      } else if (e.key === 'ArrowLeft' && i > 0) {
        e.preventDefault();
        boxes[i - 1].focus();
      } else if (e.key === 'ArrowRight' && i < length - 1) {
        e.preventDefault();
        boxes[i + 1].focus();
      }
    });
    box.addEventListener('paste', e => {
      const digits = (e.clipboardData?.getData('text') || '').replace(/\D/g, '');
      if (!digits) return;
      e.preventDefault();
      fill(digits, digits.length >= length ? 0 : i);
    });
    box.addEventListener('focus', () => box.select());
  });

  // O id passa para a primeira caixa, para o <label for> e o foco continuarem certos
  const id = source.id;
  source.id = `${id}-value`;
  boxes[0].id = id;
  source.hidden = true;
  source.removeAttribute('required');
  source.after(group);

  const initial = source.value.replace(/\D/g, '').slice(0, length);
  initial.split('').forEach((d, i) => (boxes[i].value = d));
  sync();

  source.form?.addEventListener('submit', e => {
    const empty = boxes.findIndex(b => !b.value);
    if (empty !== -1) {
      e.preventDefault();
      boxes[empty].focus();
      group.classList.remove('animate-shake');
      void group.offsetWidth;
      group.classList.add('animate-shake');
    }
  });
}

document.querySelectorAll('[data-otp]').forEach(setupOtp);
