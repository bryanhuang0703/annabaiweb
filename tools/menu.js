(function () {
  var btn = document.getElementById('ab-nav-toggle');
  var panel = document.getElementById('ab-nav-panel');
  if (!btn || !panel) return;
  var openIcon = btn.querySelector('.ab-icon-open');
  var closeIcon = btn.querySelector('.ab-icon-close');
  function setOpen(open) {
    panel.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    openIcon.style.display = open ? 'none' : '';
    closeIcon.style.display = open ? '' : 'none';
  }
  btn.addEventListener('click', function () { setOpen(panel.hidden); });
  panel.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) { setOpen(false); btn.focus(); } });
})();
