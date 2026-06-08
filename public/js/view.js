(function () {
  const loadBtn = document.getElementById('btn-load');
  const outputEl = document.getElementById('view-output');

  if (loadBtn) {
    loadBtn.addEventListener('click', async () => {
      const apiId = document.getElementById('view-apiId').value.trim();
      const apiName = document.getElementById('view-apiName').value.trim();
      if (!apiId || !apiName) { toast('Please enter both API ID and API Name', 'error'); return; }
      if (!outputEl) return;
      outputEl.textContent = 'Loading...';
      outputEl.style.display = 'block';
      try {
        const r = await fetch(`/api/v4/${apiId}/${apiName}`);
        const data = await r.json();
        outputEl.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        outputEl.textContent = 'Error: ' + String(e);
      }
    });
  }

  document.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' && loadBtn) loadBtn.click(); });
  });
})();
