(function () {
  const listEl = document.getElementById('api-list');
  const paginationEl = document.getElementById('pagination');
  let currentPage = 1;
  let editingId = null;

  window.addEventListener('auth-ready', () => {
    if (!window._currentUser) {
      window.location.href = '/error?code=401&msg=Not%20Logged%20In';
      return;
    }
    loadApis(1);
  });

  async function loadApis(page) {
    currentPage = page;
    if (!listEl) return;
    listEl.innerHTML = '<div style="text-align:center;padding:32px;color:var(--text-muted)">Loading...</div>';
    const data = await api.get(`/api/manage/apis?page=${page}`);
    if (data.error) { toast(data.error, 'error'); return; }
    renderApis(data.apis);
    renderPagination(data.page, data.pages);
  }

  function renderApis(apis) {
    if (!listEl) return;
    if (!apis.length) {
      listEl.innerHTML = `<div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        <p>No APIs yet. Create one on the <a href="/">Home</a> page.</p>
      </div>`;
      return;
    }
    listEl.innerHTML = '<div class="api-grid"></div>';
    const grid = listEl.querySelector('.api-grid');
    for (const a of apis) {
      const card = document.createElement('div');
      card.className = 'api-card';
      card.innerHTML = `
        <div class="api-card-info">
          <div class="api-card-name">${a.displayName || a.apiName}</div>
          <div class="api-card-id">/api/v4/${a.apiId}/${a.apiName}</div>
          <div class="api-card-meta">
            <span class="badge ${a.visibility === 'Private' ? 'badge-danger' : 'badge-success'}">${a.visibility}</span>
            ${a.encodeEnabled ? `<span class="badge badge-info">${a.encodeMethod || 'Encode'}</span>` : ''}
            ${a.rateLimit ? `<span class="badge badge-info">${a.rateLimit} req/m</span>` : ''}
            <span class="badge badge-info">${Array.isArray(a.data) ? a.data.length : 0} entries</span>
          </div>
        </div>
        <div class="menu-btn" data-id="${a.id}">
          <button class="btn btn-ghost btn-icon btn-dots" data-id="${a.id}" title="Options">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
          <div class="dropdown-menu" id="menu-${a.id}">
            <button class="dropdown-item" data-action="edit" data-id="${a.id}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Edit
            </button>
            <button class="dropdown-item" data-action="reset" data-id="${a.id}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
              Reset Data
            </button>
            <button class="dropdown-item danger" data-action="delete" data-id="${a.id}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
              Delete
            </button>
          </div>
        </div>
      `;
      grid.appendChild(card);
    }

    listEl.addEventListener('click', (e) => {
      const dotsBtn = e.target.closest('.btn-dots');
      if (dotsBtn) {
        const id = dotsBtn.dataset.id;
        document.querySelectorAll('.dropdown-menu').forEach(m => { if (m.id !== `menu-${id}`) m.classList.remove('open'); });
        document.getElementById(`menu-${id}`)?.classList.toggle('open');
        e.stopPropagation();
        return;
      }
      const actionBtn = e.target.closest('[data-action]');
      if (actionBtn) {
        const { action, id } = actionBtn.dataset;
        document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('open'));
        if (action === 'edit') openEditDialog(id);
        if (action === 'delete') openDeleteDialog(id);
        if (action === 'reset') openResetDialog(id);
      }
    });
  }

  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('open'));
  });

  function renderPagination(page, pages) {
    if (!paginationEl) return;
    if (pages <= 1) { paginationEl.innerHTML = ''; return; }
    paginationEl.innerHTML = `
      <button class="btn btn-ghost btn-sm" id="prev-page" ${page <= 1 ? 'disabled' : ''}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <span class="page-info">Page ${page} / ${pages}</span>
      <button class="btn btn-ghost btn-sm" id="next-page" ${page >= pages ? 'disabled' : ''}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    `;
    document.getElementById('prev-page')?.addEventListener('click', () => loadApis(page - 1));
    document.getElementById('next-page')?.addEventListener('click', () => loadApis(page + 1));
  }

  let allApis = [];

  async function openEditDialog(id) {
    editingId = id;
    const data = await api.get('/api/manage/apis');
    allApis = data.apis || [];
    const found = allApis.find(a => a.id === id);
    if (!found) return;
    const fc = document.getElementById('edit-form-fields');
    if (typeof buildFormFields === 'function') buildFormFields(fc, found);
    openDialog('edit-dialog');
  }

  function openDeleteDialog(id) {
    editingId = id;
    openDialog('delete-dialog');
  }

  function openResetDialog(id) {
    editingId = id;
    openDialog('reset-dialog');
  }

  document.getElementById('btn-edit-save')?.addEventListener('click', async () => {
    const data = typeof collectFormData === 'function' ? collectFormData() : {};
    const res = await api.put(`/api/manage/apis/${editingId}`, data);
    if (res.error) { toast(res.error, 'error'); return; }
    toast('API updated!', 'success');
    closeDialog('edit-dialog');
    loadApis(currentPage);
  });

  document.getElementById('btn-edit-cancel')?.addEventListener('click', () => closeDialog('edit-dialog'));

  document.getElementById('btn-delete-confirm')?.addEventListener('click', async () => {
    const res = await api.del(`/api/manage/apis/${editingId}`);
    if (res.error) { toast(res.error, 'error'); return; }
    toast('API deleted', 'success');
    closeDialog('delete-dialog');
    loadApis(currentPage);
  });

  document.getElementById('btn-delete-cancel')?.addEventListener('click', () => closeDialog('delete-dialog'));

  document.getElementById('btn-reset-confirm')?.addEventListener('click', async () => {
    const res = await api.post(`/api/manage/apis/${editingId}/reset`, {});
    if (res.error) { toast(res.error, 'error'); return; }
    toast('Data reset!', 'success');
    closeDialog('reset-dialog');
    loadApis(currentPage);
  });

  document.getElementById('btn-reset-cancel')?.addEventListener('click', () => closeDialog('reset-dialog'));

  document.querySelectorAll('.dialog-overlay').forEach(ov => {
    ov.addEventListener('click', (e) => {
      if (e.target === ov) ov.classList.remove('open');
    });
  });
})();
