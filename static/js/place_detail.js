/**
 * MaricaCity - JavaScript da Página de Detalhes do Local
 * Gerencia avaliações (criar, editar, excluir) e funcionalidade de favoritos
 */

// Variáveis de estado
let currentReviewId = null;
let deleteReviewId = null;

/**
 * Resetar formulário de avaliação para estado de nova avaliação
 */
function resetReviewForm() {
  currentReviewId = null;
  const form = document.getElementById('reviewForm');
  const reviewIdField = document.getElementById('reviewId');
  const modalLabel = document.getElementById('reviewModalLabel');
  const submitButtonText = document.getElementById('submitButtonText');

  if (form) form.reset();
  if (reviewIdField) reviewIdField.value = '';
  if (modalLabel) modalLabel.textContent = gettext('Escrever avaliação');
  if (submitButtonText) submitButtonText.textContent = gettext('Enviar avaliação');
}

/**
 * Preencher formulário para editar avaliação existente
 * @param {number} reviewId - ID da avaliação
 * @param {number} rating - Valor da classificação (1-5)
 * @param {string} comment - Comentário da avaliação
 */
function editReview(reviewId, rating, comment) {
  currentReviewId = reviewId;

  const reviewIdField = document.getElementById('reviewId');
  const modalLabel = document.getElementById('reviewModalLabel');
  const submitButtonText = document.getElementById('submitButtonText');
  const ratingInput = document.getElementById('rating' + rating);
  const commentField = document.getElementById('reviewComment');

  if (reviewIdField) reviewIdField.value = reviewId;
  if (modalLabel) modalLabel.textContent = gettext('Editar avaliação');
  if (submitButtonText) submitButtonText.textContent = gettext('Atualizar avaliação');
  if (ratingInput) ratingInput.checked = true;
  if (commentField) commentField.value = comment;
}

/**
 * Enviar avaliação (criar ou atualizar)
 */
function submitReview() {
  const form = document.getElementById('reviewForm');
  if (!form) return;

  const formData = new FormData(form);
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  if (!csrfToken) {
    alert(gettext('Erro: CSRF token não encontrado.'));
    return;
  }

  // Determinar URL com base em estar criando ou editando
  let url;
  if (currentReviewId) {
    // Obter do atributo data no formulário
    url = form.dataset.editUrlTemplate.replace('0', currentReviewId);
  } else {
    url = form.dataset.createUrl;
  }

  // Enviar formulário via fetch
  fetch(url, {
    method: 'POST',
    body: formData,
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })
    .then(response => {
      if (response.ok) {
        // Fechar modal e recarregar página para mostrar avaliação atualizada
        const modal = bootstrap.Modal.getInstance(
          document.getElementById('reviewModal')
        );
        if (modal) modal.hide();
        location.reload();
      } else {
        alert(gettext('Erro ao enviar avaliação. Por favor, tente novamente.'));
      }
    })
    .catch(error => {
      console.error('Erro ao enviar avaliação:', error);
      alert(gettext('Erro ao enviar avaliação. Por favor, tente novamente.'));
    });
}

/**
 * Mostrar modal de confirmação de exclusão
 * @param {number} reviewId - ID da avaliação para excluir
 */
function deleteReview(reviewId) {
  deleteReviewId = reviewId;
  const deleteModal = new bootstrap.Modal(document.getElementById('deleteReviewModal'));
  if (deleteModal) deleteModal.show();
}

/**
 * Confirmar e executar exclusão de avaliação
 */
function confirmDeleteReview() {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  const deleteForm = document.getElementById('deleteReviewForm');

  if (!csrfToken || !deleteForm || !deleteReviewId) {
    alert(gettext('Erro ao excluir avaliação.'));
    return;
  }

  const url = deleteForm.dataset.deleteUrlTemplate.replace('0', deleteReviewId);

  fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })
    .then(response => {
      if (response.ok) {
        // Fechar modal e recarregar página
        const modal = bootstrap.Modal.getInstance(
          document.getElementById('deleteReviewModal')
        );
        if (modal) modal.hide();
        location.reload();
      } else {
        alert(gettext('Erro ao excluir avaliação. Por favor, tente novamente.'));
      }
    })
    .catch(error => {
      console.error('Erro ao excluir avaliação:', error);
      alert(gettext('Erro ao excluir avaliação. Por favor, tente novamente.'));
    });
}

/**
 * Nota: A funcionalidade do botão de favorito agora é gerenciada pelo favorites-ui.js
 * que usa localStorage para todos os usuários e opcionalmente sincroniza com o backend
 * para usuários logados. O sistema unificado é carregado no base.html.
 */

/**
 * Inicializar comportamento visual da avaliação por estrelas
 */
function initStarRating() {
  const ratingInputs = document.querySelectorAll('input[name="rating"]');

  ratingInputs.forEach(input => {
    input.addEventListener('change', function () {
      updateStarVisuals(this.value);
    });
  });

  // Definir estado inicial se houver um radio marcado
  const checkedInput = document.querySelector('input[name="rating"]:checked');
  if (checkedInput) {
    updateStarVisuals(checkedInput.value);
  }
}

/**
 * Atualizar visuais das estrelas para preencher todas até a avaliação selecionada
 * @param {string|number} rating - Valor da avaliação selecionada
 */
function updateStarVisuals(rating) {
  const ratingValue = parseInt(rating);
  const allLabels = document.querySelectorAll('.star-label');

  allLabels.forEach((label, index) => {
    const starValue = index + 1;
    if (starValue <= ratingValue) {
      label.classList.add('star-selected');
    } else {
      label.classList.remove('star-selected');
    }
  });
}

/**
 * Inicializar Carrossel do Local
 */
function initPlaceCarousel() {
  const carousel = document.querySelector('.place-carousel');
  if (!carousel) return;

  const items = carousel.querySelectorAll('.place-carousel-item');
  const prevBtn = carousel.querySelector('.place-carousel-prev');
  const nextBtn = carousel.querySelector('.place-carousel-next');
  const dots = carousel.querySelectorAll('.place-carousel-dot');

  if (items.length <= 1) return; // Não há necessidade de carrossel com uma única imagem

  let currentIndex = 0;

  function showSlide(index) {
    // Remover classe active de todos os itens e pontos
    items.forEach(item => item.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));

    // Adicionar classe active ao item e ponto atual
    items[index].classList.add('active');
    dots[index].classList.add('active');
    currentIndex = index;
  }

  function nextSlide() {
    const newIndex = (currentIndex + 1) % items.length;
    showSlide(newIndex);
  }

  function prevSlide() {
    const newIndex = (currentIndex - 1 + items.length) % items.length;
    showSlide(newIndex);
  }

  // Ouvintes de eventos
  if (prevBtn) {
    prevBtn.addEventListener('click', prevSlide);
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', nextSlide);
  }

  dots.forEach((dot, index) => {
    dot.addEventListener('click', () => showSlide(index));
  });

  // Navegação por teclado
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') prevSlide();
    if (e.key === 'ArrowRight') nextSlide();
  });
}

// Inicializar carrossel e avaliação por estrelas quando o DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initPlaceCarousel();
    initStarRating();
  });
} else {
  initPlaceCarousel();
  initStarRating();
}

// Reinicializar avaliação por estrelas quando o modal for exibido
const reviewModal = document.getElementById('reviewModal');
if (reviewModal) {
  reviewModal.addEventListener('shown.bs.modal', initStarRating);
}

// Exportar funções para uso global
window.resetReviewForm = resetReviewForm;
window.editReview = editReview;
window.submitReview = submitReview;
window.deleteReview = deleteReview;
window.confirmDeleteReview = confirmDeleteReview;
