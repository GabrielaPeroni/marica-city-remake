// Painel: botão do topo abre/fecha a sidebar (folha no celular); no desktop o estado fica salvo
document.addEventListener('click', e => {
  const toggle = e.target.closest('[data-sidebar-toggle]');
  const sidebar = document.getElementById('admin-sidebar');
  if (!toggle || !sidebar || typeof sidebar.toggle !== 'function') return;
  sidebar.toggle();
  const open = sidebar.getAttribute('aria-hidden') !== 'true';
  toggle.setAttribute('aria-expanded', String(open));
  if (window.innerWidth >= 768) {
    try {
      localStorage.setItem('adminSidebar', open ? 'open' : 'closed');
    } catch (err) {}
  }
});

// Filtros que se aplicam ao mudar (select de categoria/ordem)
document.addEventListener('change', e => {
  if (e.target.matches('[data-autosubmit]')) e.target.form?.requestSubmit();
});

// Remover lugar: diálogo de includes/remove_place_modal.html
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-remove-place]');
  if (btn && typeof window.openRemoveModal === 'function') {
    window.openRemoveModal(btn.dataset.removePlace, btn.dataset.placeName);
  }
});
