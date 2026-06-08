(function () {
  const listEl = document.getElementById('user-list');
  const paginationEl = document.getElementById('pagination');
  let currentPage = 1;
  let actionId = null;
  let actionType = null;

  window.addEventListener('auth-ready', () => {
    if (!window._currentUser || !window._currentUser.isAdmin) {
      window.location.href = '/error?code=403&msg=Admin%20Required';
      return;
    }
    loadUsers(1);
  });

  async function loadUsers(page) {
    currentPage = page;
    if (!listEl) return;
    listEl.innerHTML = '<div style="text-align:center;padding:32px;color:var(--text-muted)">Loading...</div>';
    const data = await api.get(`/api/manage/users?page=${page}`);
    if (data.error) { toast(data.error, 'error'); return; }
    renderUsers(data.users);
    renderPagination(data.page, data.pages);
  }

  function renderUsers(users) {
    if (!listEl) return;
    if (!users.length) {
      listEl.innerHTML = `<div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        <p>No users found.</p>
      </div>`;
      return;
    }
    listEl.innerHTML = '<div class="api-grid"></div>';
    const grid = listEl.querySelector('.api-grid');
    for (const u of users) {
      const card = document.createElement('div');
      card.className = 'api-card';
      card.innerHTML = `
        <div class="api-card-info">
          <div class="api-card-name" style="display:flex;align-items:center;gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
            ${u.username}
            ${u.isAdmin ? '<span class="badge badge-admin">Admin</span>' : '<span class="badge badge-info">User</span>'}
          </div>
          <div class="api-card-id">ID: ${u.id}</div>
          <div class="api-card-meta">
            <span class="badge badge-info">Joined: ${new Date(u.createdAt).toLocaleDateString()}</span>
          </div>
        </div>
        <div class="menu-btn" data-id="${u.id}">
          <button class="btn btn-ghost btn-icon btn-dots" data-id="${u.id}" title="Options">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
          <div class="dropdown-menu" id="menu-${u.id}">
            <button class="dropdown-item" data-action="permission" data-id="${u.id}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              ${u.isAdmin ? 'Revoke Admin' : 'Give Admin'}
            </button>
            <button class="dropdown-item danger" data-action="delete" data-id="${u.id}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
              Delete Account
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
        actionId = id;
        actionType = action;
        const dlg = document.getElementById('confirm-dialog');
        const msg = document.getElementById('confirm-msg');
        if (msg) {
          if (action === 'permission') msg.textContent = 'Are you sure you want to toggle admin permission for this user?';
          if (action === 'delete') msg.textContent = 'Are you sure you want to delete this account? This cannot be undone.';
        }
        openDialog('confirm-dialog');
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
    document.getElementById('prev-page')?.addEventListener('click', () => loadUsers(page - 1));
    document.getElementById('next-page')?.addEventListener('click', () => loadUsers(page + 1));
  }

  document.getElementById('btn-confirm-yes')?.addEventListener('click', async () => {
    if (actionType === 'permission') {
      const res = await api.put(`/api/manage/users/${actionId}/permission`, {});
      if (res.error) { toast(res.error, 'error'); } else toast('Permission updated!', 'success');
    } else if (actionType === 'delete') {
      const res = await api.del(`/api/manage/users/${actionId}`);
      if (res.error) { toast(res.error, 'error'); } else toast('User deleted', 'success');
    }
    closeDialog('confirm-dialog');
    loadUsers(currentPage);
  });

  document.getElementById('btn-confirm-no')?.addEventListener('click', () => closeDialog('confirm-dialog'));

  document.querySelectorAll('.dialog-overlay').forEach(ov => {
    ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('open'); });
  });
})();
