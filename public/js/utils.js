window.api = {
  async get(path) {
    const r = await fetch(path, { credentials: 'include' });
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    });
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    });
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method: 'DELETE', credentials: 'include' });
    return r.json();
  },
};

window.toast = function (msg, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(20px)'; t.style.transition = '0.3s'; setTimeout(() => t.remove(), 300); }, 3000);
};

window.openDialog = function (id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
};

window.closeDialog = function (id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
};

window.randomId = function (len = 10) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let r = '';
  for (let i = 0; i < len; i++) r += chars[Math.floor(Math.random() * chars.length)];
  return r;
};

window.copyText = function (text) {
  navigator.clipboard.writeText(text).then(() => toast('Copied!', 'success')).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    toast('Copied!', 'success');
  });
};

window.formatJson = function (obj) {
  return JSON.stringify(obj, null, 2);
};

const CUSTOM_ENCODE_TEMPLATE = `{
  "a": "", "b": "", "c": "", "d": "", "e": "",
  "f": "", "g": "", "h": "", "i": "", "j": "",
  "k": "", "l": "", "m": "", "n": "", "o": "",
  "p": "", "q": "", "r": "", "s": "", "t": "",
  "u": "", "v": "", "w": "", "x": "", "y": "",
  "z": "",
  "A": "", "B": "", "C": "", "D": "", "E": "",
  "F": "", "G": "", "H": "", "I": "", "J": "",
  "K": "", "L": "", "M": "", "N": "", "O": "",
  "P": "", "Q": "", "R": "", "S": "", "T": "",
  "U": "", "V": "", "W": "", "X": "", "Y": "",
  "Z": "",
  "0": "", "1": "", "2": "", "3": "", "4": "",
  "5": "", "6": "", "7": "", "8": "", "9": ""
}`;

window.CUSTOM_ENCODE_TEMPLATE = CUSTOM_ENCODE_TEMPLATE;

function buildFormFields(container, data) {
  if (!container) return;
  const fields = [
    { label: 'API Name', id: 'f-apiName', type: 'text', placeholder: 'my-api', value: data?.apiName ?? '' },
    { label: 'API ID', id: 'f-apiId', type: 'text', placeholder: 'auto-generated', value: data?.apiId ?? '', withRandom: true },
    { label: 'API Display Name', id: 'f-displayName', type: 'text', placeholder: 'My API', value: data?.displayName ?? '' },
    { label: 'Discord Webhook URL', id: 'f-webhookUrl', type: 'text', placeholder: 'https://discord.com/api/webhooks/...', value: data?.webhookUrl ?? '' },
  ];
  container.innerHTML = '';
  for (const f of fields) {
    const g = document.createElement('div');
    g.className = 'form-group';
    g.innerHTML = `<label>${f.label}</label>`;
    if (f.withRandom) {
      g.innerHTML += `<div class="form-row">
        <input type="${f.type}" id="${f.id}" placeholder="${f.placeholder}" value="${f.value}">
        <button class="btn btn-ghost btn-icon" id="btn-random-id" title="Generate random ID">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/></svg>
        </button>
      </div>`;
    } else {
      g.innerHTML += `<input type="${f.type}" id="${f.id}" placeholder="${f.placeholder}" value="${f.value}">`;
    }
    container.appendChild(g);
  }

  const toggleEmptyGroup = document.createElement('div');
  toggleEmptyGroup.className = 'form-group';
  toggleEmptyGroup.innerHTML = `
    <div class="toggle-group">
      <span class="toggle-label">Empty Value</span>
      <label class="toggle"><input type="checkbox" id="f-emptyValue" ${data?.emptyValue !== false ? 'checked' : ''}><span class="toggle-slider"></span></label>
    </div>
    <div id="default-value-group" class="form-group" style="margin-top:10px;display:${data?.emptyValue !== false ? 'none' : 'block'}">
      <label>Default Value (JSON)</label>
      <textarea id="f-defaultValue" placeholder='{"key": "value"}'>${data?.defaultValue ? JSON.stringify(data.defaultValue, null, 2) : ''}</textarea>
    </div>
  `;
  container.appendChild(toggleEmptyGroup);

  const visGroup = document.createElement('div');
  visGroup.className = 'form-group';
  visGroup.innerHTML = `
    <label>Visibility</label>
    <select id="f-visibility"><option value="Public" ${data?.visibility !== 'Private' ? 'selected' : ''}>Public</option><option value="Private" ${data?.visibility === 'Private' ? 'selected' : ''}>Private</option></select>
    <div id="whitelist-group" style="margin-top:10px;display:${data?.visibility === 'Private' ? 'block' : 'none'}">
      <label>Whitelist IPs (comma separated)</label>
      <input type="text" id="f-whitelistIps" placeholder="1.2.3.4, 5.6.7.8" value="${(data?.whitelistIps || []).join(', ')}">
    </div>
  `;
  container.appendChild(visGroup);

  const rateLimitGroup = document.createElement('div');
  rateLimitGroup.className = 'form-group';
  rateLimitGroup.innerHTML = `<label>Rate Limit (req/min)</label><input type="number" id="f-rateLimit" placeholder="No limit" min="1" value="${data?.rateLimit ?? ''}">`;
  container.appendChild(rateLimitGroup);

  const toggleDupGroup = document.createElement('div');
  toggleDupGroup.className = 'form-group';
  toggleDupGroup.innerHTML = `
    <div class="toggle-group">
      <span class="toggle-label">Allow Duplicate Data</span>
      <label class="toggle"><input type="checkbox" id="f-allowDuplicate" ${data?.allowDuplicate ? 'checked' : ''}><span class="toggle-slider"></span></label>
    </div>
  `;
  container.appendChild(toggleDupGroup);

  const encodeGroup = document.createElement('div');
  encodeGroup.className = 'form-group';
  encodeGroup.innerHTML = `
    <div class="toggle-group">
      <span class="toggle-label">Enable Data Encode</span>
      <label class="toggle"><input type="checkbox" id="f-encodeEnabled" ${data?.encodeEnabled ? 'checked' : ''}><span class="toggle-slider"></span></label>
    </div>
    <div id="encode-settings" style="margin-top:12px;display:${data?.encodeEnabled ? 'block' : 'none'}">
      <div class="sub-section">
        <div class="section-label">Encode Settings</div>
        <div class="form-group">
          <label>Encode Method</label>
          <select id="f-encodeMethod">
            <option value="Base64" ${data?.encodeMethod === 'Base64' ? 'selected' : ''}>Base64</option>
            <option value="Base62" ${data?.encodeMethod === 'Base62' ? 'selected' : ''}>Base62</option>
            <option value="Base32" ${data?.encodeMethod === 'Base32' ? 'selected' : ''}>Base32</option>
            <option value="Hex" ${data?.encodeMethod === 'Hex' ? 'selected' : ''}>Hex</option>
            <option value="Binary" ${data?.encodeMethod === 'Binary' ? 'selected' : ''}>Binary</option>
            <option value="Unicode Escaped" ${data?.encodeMethod === 'Unicode Escaped' ? 'selected' : ''}>Unicode Escaped</option>
            <option value="Custom" ${data?.encodeMethod === 'Custom' ? 'selected' : ''}>Custom</option>
          </select>
        </div>
        <div id="custom-encode-fields" style="display:${data?.encodeMethod === 'Custom' ? 'block' : 'none'}">
          <div class="form-group">
            <label>Prefix</label>
            <input type="text" id="f-encodePrefix" placeholder="optional prefix" value="${data?.encodePrefix ?? ''}">
          </div>
          <div class="form-group">
            <label>Encode Map (JSON)</label>
            <textarea id="f-encodeMap" rows="6" placeholder='{"a": "X1Y", "b": "Z2W", ...}'>${data?.encodeMap ? JSON.stringify(data.encodeMap, null, 2) : CUSTOM_ENCODE_TEMPLATE}</textarea>
          </div>
        </div>
        <div class="form-group">
          <label>Key to Encode</label>
          <input type="text" id="f-encodeKey" placeholder="e.g. name, JobId" value="${data?.encodeKey ?? ''}">
        </div>
      </div>
    </div>
  `;
  container.appendChild(encodeGroup);

  const emptyToggle = document.getElementById('f-emptyValue');
  if (emptyToggle) {
    emptyToggle.addEventListener('change', () => {
      const dv = document.getElementById('default-value-group');
      if (dv) dv.style.display = emptyToggle.checked ? 'none' : 'block';
    });
  }

  const visSelect = document.getElementById('f-visibility');
  if (visSelect) {
    visSelect.addEventListener('change', () => {
      const wl = document.getElementById('whitelist-group');
      if (wl) wl.style.display = visSelect.value === 'Private' ? 'block' : 'none';
    });
  }

  const encodeToggle = document.getElementById('f-encodeEnabled');
  if (encodeToggle) {
    encodeToggle.addEventListener('change', () => {
      const es = document.getElementById('encode-settings');
      if (es) es.style.display = encodeToggle.checked ? 'block' : 'none';
    });
  }

  const encodeMethod = document.getElementById('f-encodeMethod');
  if (encodeMethod) {
    encodeMethod.addEventListener('change', () => {
      const cf = document.getElementById('custom-encode-fields');
      if (cf) cf.style.display = encodeMethod.value === 'Custom' ? 'block' : 'none';
      if (encodeMethod.value === 'Custom') {
        const em = document.getElementById('f-encodeMap');
        if (em && !em.value.trim()) em.value = CUSTOM_ENCODE_TEMPLATE;
      }
    });
  }

  const randomBtn = document.getElementById('btn-random-id');
  if (randomBtn) {
    randomBtn.addEventListener('click', () => {
      const inp = document.getElementById('f-apiId');
      if (inp) inp.value = randomId(10);
    });
  }
}

function collectFormData() {
  function val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ''; }
  function checked(id) { const el = document.getElementById(id); return el ? el.checked : false; }
  const emptyValue = checked('f-emptyValue');
  const encodeEnabled = checked('f-encodeEnabled');
  const visibility = val('f-visibility');
  const encodeMethod = val('f-encodeMethod');
  let defaultValue = null;
  if (!emptyValue) {
    try { defaultValue = JSON.parse(val('f-defaultValue') || 'null'); } catch { defaultValue = val('f-defaultValue'); }
  }
  let encodeMap = null;
  if (encodeEnabled && encodeMethod === 'Custom') {
    try { encodeMap = JSON.parse(val('f-encodeMap')); } catch {}
  }
  return {
    apiId: val('f-apiId'),
    apiName: val('f-apiName'),
    displayName: val('f-displayName'),
    emptyValue,
    defaultValue,
    webhookUrl: val('f-webhookUrl'),
    visibility,
    whitelistIps: visibility === 'Private' ? val('f-whitelistIps') : '',
    rateLimit: val('f-rateLimit') ? parseInt(val('f-rateLimit')) : null,
    allowDuplicate: checked('f-allowDuplicate'),
    encodeEnabled,
    encodeMethod: encodeEnabled ? encodeMethod : null,
    encodePrefix: encodeEnabled && encodeMethod === 'Custom' ? val('f-encodePrefix') : null,
    encodeMap,
    encodeKey: encodeEnabled ? val('f-encodeKey') : null,
  };
}

window.buildFormFields = buildFormFields;
window.collectFormData = collectFormData;
