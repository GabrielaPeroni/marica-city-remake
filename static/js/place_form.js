/**
 * MaricaCity - JavaScript do Formulário de Local
 * Gerencia visualização e gerenciamento de upload de imagens para criação/edição de locais
 */

document.addEventListener('DOMContentLoaded', function () {
  const previewGrid = document.getElementById('image-preview-grid');
  const addImageBtn = document.getElementById('add-image-btn');
  const formsetContainer = document.getElementById('formset-container');
  const formsetForms = formsetContainer.querySelectorAll('.formset-form');
  let imageCount = 0;
  const MAX_IMAGES = 3;

  // Contar imagens existentes ao carregar a página
  formsetForms.forEach((formDiv, index) => {
    const deleteInput = formDiv.querySelector('input[name*="DELETE"]');
    const existingImageUrl = formDiv.dataset.existingImageUrl;

    // Verificar se há uma imagem existente (do banco de dados) e não está marcada para exclusão
    if (existingImageUrl && !deleteInput.checked) {
      imageCount++;
      createPreviewCard(existingImageUrl, index, true);
    }
  });

  // Gerenciar clique no botão adicionar imagem
  addImageBtn.addEventListener('click', function () {
    if (imageCount >= MAX_IMAGES) {
      alert(`Você pode adicionar no máximo ${MAX_IMAGES} imagens.`);
      return;
    }

    // Encontrar primeiro slot de formulário disponível
    let targetFormIndex = -1;
    formsetForms.forEach((formDiv, index) => {
      if (targetFormIndex === -1) {
        const deleteInput = formDiv.querySelector('input[name*="DELETE"]');
        const imageInput = formDiv.querySelector('input[type="file"]');
        const existingImageUrl = formDiv.dataset.existingImageUrl;

        // Disponível se não excluído, não tem novo arquivo e não tem imagem existente
        if (!deleteInput.checked && !imageInput.files.length && !existingImageUrl) {
          targetFormIndex = index;
        }
      }
    });

    if (targetFormIndex === -1) {
      alert('Não há mais espaço para novas imagens.');
      return;
    }

    // Acionar clique no input de arquivo
    const formDiv = formsetForms[targetFormIndex];
    const imageInput = formDiv.querySelector('input[type="file"]');
    imageInput.click();

    // Gerenciar seleção de arquivo
    imageInput.onchange = function (e) {
      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function (event) {
          createPreviewCard(event.target.result, targetFormIndex, false);
          imageCount++;
          updateButtonState();
        };
        reader.readAsDataURL(file);
      }
    };
  });

  /**
   * Criar um cartão de visualização para uma imagem
   * @param {string} imageSrc - URL da fonte da imagem ou URL de dados
   * @param {number} formIndex - Índice do formulário no formset
   * @param {boolean} isExisting - Se esta é uma imagem existente
   */
  function createPreviewCard(imageSrc, formIndex, isExisting) {
    const col = document.createElement('div');
    col.className = 'col-6 col-md-4';
    col.dataset.formIndex = formIndex;

    col.innerHTML = `
      <div class="card position-relative">
        <img src="${imageSrc}" class="card-img-top" style="height: 150px; object-fit: cover;" loading="lazy">
        <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 m-2 remove-image" data-form-index="${formIndex}">
          <i class="bi bi-trash"></i>
        </button>
        ${
          formIndex === 0
            ? '<span class="badge bg-primary position-absolute top-0 start-0 m-2">Principal</span>'
            : ''
        }
      </div>
    `;

    previewGrid.appendChild(col);

    const removeBtn = col.querySelector('.remove-image');
    removeBtn.addEventListener('click', function () {
      removeImage(formIndex, col);
    });
  }

  /**
   * Remover uma imagem da visualização e marcar para exclusão
   * @param {number} formIndex - Índice do formulário no formset
   * @param {HTMLElement} cardElement - O elemento do cartão para remover
   */
  function removeImage(formIndex, cardElement) {
    const formDiv = formsetForms[formIndex];
    const deleteInput = formDiv.querySelector('input[name*="DELETE"]');
    const imageInput = formDiv.querySelector('input[type="file"]');

    if (deleteInput) {
      deleteInput.checked = true;
    }

    if (imageInput) {
      imageInput.value = '';
    }

    // Limpar o atributo de dados da URL da imagem existente
    if (formDiv.dataset.existingImageUrl) {
      delete formDiv.dataset.existingImageUrl;
    }

    cardElement.remove();
    imageCount--;
    updateButtonState();
  }

  /**
   * Atualizar o estado do botão adicionar com base na contagem de imagens
   */
  function updateButtonState() {
    if (imageCount >= MAX_IMAGES) {
      addImageBtn.disabled = true;
      addImageBtn.classList.add('disabled');
      addImageBtn.querySelector('span').textContent = 'Limite de fotos atingido';
    } else {
      addImageBtn.disabled = false;
      addImageBtn.classList.remove('disabled');
      addImageBtn.querySelector('span').textContent = 'Adicionar Fotos';
    }
  }

  // Atualização inicial do estado do botão
  updateButtonState();

  // Definir ordem de exibição e primária automaticamente ao enviar o formulário
  document.getElementById('place-form').addEventListener('submit', function (e) {
    const previewCards = previewGrid.querySelectorAll('[data-form-index]');
    previewCards.forEach((card, index) => {
      const formIndex = card.dataset.formIndex;
      const formDiv = formsetForms[formIndex];
      const orderInput = formDiv.querySelector('input[name*="display_order"]');
      const primaryInput = formDiv.querySelector('input[name*="is_primary"]');

      if (orderInput) orderInput.value = index;
      if (primaryInput) primaryInput.checked = index === 0;
    });
  });
});
