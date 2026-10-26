function decodeJWT(token) {
  let base64Url = token.split('.')[1];
  let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  let jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      })
      .join('')
  );
  return JSON.parse(jsonPayload);
}

function handleCredentialResponse(response) {
  const payload = decodeJWT(response.credential);

  // Enviar token para o backend para autenticação
  fetch('/auth/google/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ token: response.credential }),
  })
    .then(res => {
      if (res.ok) {
        // Armazenar flag para mostrar toast de sucesso após redirect
        sessionStorage.setItem('loginSuccess', 'true');
        sessionStorage.setItem('loginUsername', payload.name || gettext('usuário'));
        window.location.href = '/';
      } else {
        console.error('Autenticação do Google falhou');
        alert(gettext('Falha ao autenticar com Google. Por favor, tente novamente.'));
      }
    })
    .catch(error => {
      console.error('Erro durante a autenticação do Google:', error);
      alert(gettext('Erro ao conectar com o servidor. Por favor, tente novamente.'));
    });
}

// Rastrear se o Google Sign-In foi inicializado
let googleInitialized = false;

// Inicializar SDK do Google Sign-In
function initializeGoogleSDK() {
  if (
    typeof google !== 'undefined' &&
    google.accounts &&
    window.GOOGLE_CLIENT_ID &&
    !googleInitialized
  ) {
    try {
      google.accounts.id.initialize({
        client_id: window.GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
      });
      googleInitialized = true;
      renderGoogleButton();
    } catch (error) {
      console.error('Erro ao inicializar SDK do Google Sign-In:', error);
    }
  } else if (!googleInitialized) {
    // Se o SDK do Google ainda não estiver pronto, tentar novamente em 100ms
    setTimeout(initializeGoogleSDK, 100);
  }
}

// Renderizar o botão do Google Sign-In
function renderGoogleButton() {
  if (!googleInitialized) {
    return;
  }

  const googleButton = document.getElementById('google-signin-button');
  if (googleButton && !googleButton.hasChildNodes()) {
    try {
      google.accounts.id.renderButton(googleButton, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: 280,
      });
    } catch (error) {
      console.error('Erro ao renderizar botão do Google Sign-In:', error);
    }
  }
}

// Ouvir eventos de exibição do dropdown para renderizar o botão quando ele se tornar visível
document.addEventListener('shown.bs.dropdown', function (event) {
  // Verificar se este é um dropdown de login
  const dropdown = event.target;
  if (dropdown.querySelector('#google-signin-button')) {
    renderGoogleButton();
  }
});

// Iniciar inicialização quando o DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeGoogleSDK);
} else {
  initializeGoogleSDK();
}
