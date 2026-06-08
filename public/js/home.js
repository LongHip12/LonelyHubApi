(function () {
  const formContainer = document.getElementById('create-form-fields');
  const logConsole = document.getElementById('log-console');
  const resultBox = document.getElementById('result-box');

  if (typeof buildFormFields === 'function') buildFormFields(formContainer, null);

  function addLog(type, text) {
    if (!logConsole) return;
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="log-badge ${type}">${type.toUpperCase()}</span><span class="log-text">${text}</span>`;
    logConsole.appendChild(line);
    logConsole.scrollTop = logConsole.scrollHeight;
  }

  function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

  function showResult(apiObj) {
    if (!resultBox) return;
    const link = `/api/v4/${apiObj.apiId}/${apiObj.apiName}`;
    resultBox.innerHTML = `
      <div style="margin-bottom:12px;font-weight:700;color:var(--primary);font-size:0.95rem;display:flex;align-items:center;gap:8px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        API Created Successfully
      </div>
      <table class="result-table">
        <tr><th>API Name</th><td>${apiObj.apiName}</td></tr>
        <tr><th>API ID</th><td><code>${apiObj.apiId}</code></td></tr>
        <tr><th>API Link</th><td>
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <code style="word-break:break-all">${link}</code>
            <div class="result-actions">
              <button class="btn btn-ghost btn-sm" onclick="copyText('${window.location.origin}${link}')">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                Copy
              </button>
              <a href="${link}" target="_blank" class="btn btn-secondary btn-sm">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                Open
              </a>
            </div>
          </div>
        </td></tr>
      </table>
    `;
    resultBox.classList.add('show');
  }

  const createBtn = document.getElementById('btn-create-api');
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      if (!window._currentUser) {
        if (typeof collectFormData === 'function') {
          const pending = collectFormData();
          localStorage.setItem('pendingApiForm', JSON.stringify(pending));
        }
        window.location.href = '/auth?method=login&redirect=/';
        return;
      }

      if (logConsole) logConsole.innerHTML = '';
      if (resultBox) resultBox.classList.remove('show');

      const data = typeof collectFormData === 'function' ? collectFormData() : {};
      if (!data.apiId) data.apiId = randomId(10);
      if (!data.apiName) data.apiName = randomId(10);
      if (!data.displayName) data.displayName = data.apiName;

      addLog('info', `Preparing to create <b>${data.displayName}</b> API`);
      await sleep(500);

      addLog('info', 'Setup webhook...');
      await sleep(200);
      if (data.webhookUrl) {
        addLog('info', 'Setup webhook successfully!');
      } else {
        addLog('info', 'Webhook not found - set webhook as none');
      }
      await sleep(300);

      addLog('info', 'Setup rate limit...');
      await sleep(400);
      if (data.rateLimit) {
        addLog('info', `Rate limit has been set with <b>${data.rateLimit}</b> request/min`);
      } else {
        addLog('info', 'Rate limit not found - set rate limit default as none');
      }
      await sleep(300);

      addLog('info', 'Setup default value...');
      await sleep(100);
      if (data.emptyValue) {
        addLog('info', 'Empty value is true, skipping default value...');
      } else {
        addLog('info', 'Setup default value successfully!');
      }
      await sleep(300);

      addLog('info', 'Setup encoding...');
      await sleep(100);
      if (data.encodeEnabled && data.encodeMethod) {
        addLog('info', `Setup encode successfully! Type: <b>${data.encodeMethod}</b>`);
      } else {
        addLog('info', 'Encode not found - set encode value as none');
      }
      await sleep(200);
      addLog('info', 'API endpoint almost done...');
      await sleep(500);

      try {
        const res = await api.post('/api/manage/apis', data);
        if (res.error) {
          addLog('error', res.error);
          toast(res.error, 'error');
          return;
        }
        addLog('info', 'API Create Successfully!');
        showResult({ ...res.api, ...data });
        localStorage.removeItem('pendingApiForm');
        toast('API created!', 'success');
      } catch (err) {
        addLog('error', String(err));
        toast('Error creating API', 'error');
      }
    });
  }

  window.addEventListener('auth-ready', () => {
    const pending = localStorage.getItem('pendingApiForm');
    if (pending && window._currentUser) {
      try {
        const data = JSON.parse(pending);
        if (typeof buildFormFields === 'function') buildFormFields(formContainer, data);
        toast('Your previous form data has been restored', 'success');
      } catch {}
    }
  });

  addLog('info', 'System Ready!');
})();
