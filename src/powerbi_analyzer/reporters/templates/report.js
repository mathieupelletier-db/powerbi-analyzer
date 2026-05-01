(function () {
  const chips = document.querySelectorAll('.chip[data-filter]');
  const findings = document.querySelectorAll('.finding');
  const active = new Set();
  function apply() {
    findings.forEach(f => {
      const sev = f.dataset.severity;
      const phase = f.dataset.phase;
      const ok = active.size === 0 || active.has(sev) || active.has(phase);
      f.style.display = ok ? '' : 'none';
    });
  }
  chips.forEach(c => c.addEventListener('click', () => {
    const v = c.dataset.filter;
    if (active.has(v)) { active.delete(v); c.setAttribute('aria-pressed', 'false'); }
    else { active.add(v); c.setAttribute('aria-pressed', 'true'); }
    apply();
  }));
  document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', async () => {
    await navigator.clipboard.writeText(b.dataset.text);
    b.textContent = 'copied';
    setTimeout(() => (b.textContent = 'copy'), 1200);
  }));
})();
