// Asks once per browser; the answer lives in the mc_consent cookie for a year.
(function () {
  const banner = document.getElementById('cookieConsent');
  if (!banner || /(?:^|;\s*)mc_consent=/.test(document.cookie)) return;
  banner.hidden = false;
  banner.addEventListener('click', e => {
    const choice = e.target.closest('[data-consent]');
    if (!choice) return;
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `mc_consent=${choice.dataset.consent}; Max-Age=31536000; Path=/; SameSite=Lax${secure}`;
    banner.hidden = true;
  });
})();
