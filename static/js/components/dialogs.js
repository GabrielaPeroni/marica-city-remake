// <dialog> nativo: data-dialog-open="id" abre, data-dialog-close fecha, clique no fundo fecha
document.addEventListener('click', e => {
  const opener = e.target.closest('[data-dialog-open]');
  if (opener) {
    const dialog = document.getElementById(opener.dataset.dialogOpen);
    if (dialog instanceof HTMLDialogElement) {
      e.preventDefault();
      dialog.showModal();
    }
    return;
  }
  if (e.target.closest('[data-dialog-close]')) {
    e.target.closest('dialog')?.close();
    return;
  }
  if (e.target instanceof HTMLDialogElement && !e.target.hasAttribute('data-static')) {
    e.target.close();
  }
});
