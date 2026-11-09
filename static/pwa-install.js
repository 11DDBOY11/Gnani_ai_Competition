(() => {
  const banner = document.querySelector('[data-pwa-install]');
  if (!banner) return;
  const button = document.getElementById('installButton');
  const dismiss = document.getElementById('dismissInstall');
  const help = document.getElementById('installHelp');
  let pendingPrompt = null;

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  }
  function dismissed() {
    try { return localStorage.getItem('krishi-install-dismissed') === '1'; }
    catch (error) { return false; }
  }
  function hide() { banner.hidden = true; }
  function updateVisibility() {
    banner.hidden = isStandalone() || dismissed();
  }

  updateVisibility();
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    pendingPrompt = event;
    updateVisibility();
  });
  button.addEventListener('click', async () => {
    if (!pendingPrompt) {
      help.textContent = document.documentElement.lang === 'kn'
        ? 'Chrome ಮೆನು → Add to Home screen'
        : 'Chrome menu → Add to Home screen';
      return;
    }
    pendingPrompt.prompt();
    const choice = await pendingPrompt.userChoice;
    pendingPrompt = null;
    if (choice?.outcome === 'accepted') hide();
  });
  dismiss.addEventListener('click', () => {
    try { localStorage.setItem('krishi-install-dismissed', '1'); } catch (error) {}
    hide();
  });
  window.addEventListener('appinstalled', hide);
})();
