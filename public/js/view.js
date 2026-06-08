(function () {
  const loadBtn = document.getElementById('btn-load');
  const outputEl = document.getElementById('view-output');
  const outputCard = document.getElementById('output-card');
  const copyBtn = document.getElementById('btn-copy-output');

  if (loadBtn) {
    loadBtn.addEventListener('click', async () => {
      const apiId = document.getElementById('view-apiId').value.trim();
      const apiName = document.getElementById('view-apiName').value.trim();
      if (!apiId || !apiName) { toast('Please enter both API ID and API Name', 'error'); return; }
      if (outputCard) outputCard.style.display = 'block';
      if (outputEl) { outputEl.style.display = 'block'; outputEl.textContent = 'Loading...'; }
      try {
        const r = await fetch('/api/v4/' + apiId + '/' + apiName);
        const text = await r.text();
        let data;
        try {
          data = JSON.parse(text);
        } catch (parseErr) {
          const preview = text.substring(0, 120).replace(/\n/g, ' ');
          if (outputEl) outputEl.textContent = 'Error: Server trả về HTML thay vì JSON. Endpoint không tồn tại hoặc server lỗi. Preview: ' + preview;
          return;
        }
        if (outputEl) outputEl.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        if (outputEl) outputEl.textContent = 'Error: ' + (e.message || String(e));
      }
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      if (outputEl && outputEl.textContent) copyText(outputEl.textContent);
    });
  }

  document.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' && loadBtn) loadBtn.click(); });
  });
})();
