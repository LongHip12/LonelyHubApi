(function () {
  const LOGO = 'https://i.imgur.com/xY7M2iE.jpeg';

  const topbarEl = document.getElementById('topbar');
  if (topbarEl) {
    topbarEl.innerHTML = `
      <a class="topbar-brand" href="/">
        <img class="topbar-logo" src="${LOGO}" alt="Lonely Api" onerror="this.style.display='none'">
        <span class="topbar-title">Lonely<span>Api</span></span>
      </a>
      <button id="nav-toggle" title="Toggle navigation" aria-label="Toggle navigation">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>
        </svg>
      </button>
    `;
  }

  const currentPath = window.location.pathname;

  const sidebarEl = document.getElementById('sidebar');
  if (sidebarEl) {
    sidebarEl.innerHTML = `
      <nav class="sidebar-nav">
        <a class="sidebar-link${currentPath === '/' ? ' active' : ''}" href="/">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          Home
        </a>
        <a class="sidebar-link${currentPath === '/manager' ? ' active' : ''}" href="/manager">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          Manager
        </a>
        <a class="sidebar-link${currentPath === '/view' ? ' active' : ''}" href="/view">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          View
        </a>
        <div id="admin-links"></div>
      </nav>
      <div class="sidebar-bottom" id="sidebar-bottom">
        <div class="sidebar-auth-row">
          <a href="/auth?method=login" class="btn btn-secondary btn-sm">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
            Login
          </a>
          <a href="/auth?method=register" class="btn btn-primary btn-sm">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
            Register
          </a>
        </div>
      </div>
    `;
  }

  const overlay = document.getElementById('sidebar-overlay');

  function toggleSidebar() {
    const sb = document.getElementById('sidebar');
    const ov = document.getElementById('sidebar-overlay');
    if (!sb) return;
    sb.classList.toggle('open');
    if (ov) ov.classList.toggle('open');
  }

  document.addEventListener('click', (e) => {
    const toggle = document.getElementById('nav-toggle');
    const sb = document.getElementById('sidebar');
    if (toggle && toggle.contains(e.target)) { toggleSidebar(); return; }
    if (sb && sb.classList.contains('open') && !sb.contains(e.target)) {
      const ov = document.getElementById('sidebar-overlay');
      sb.classList.remove('open');
      if (ov) ov.classList.remove('open');
    }
  });

  if (overlay) {
    overlay.addEventListener('click', () => {
      const sb = document.getElementById('sidebar');
      if (sb) sb.classList.remove('open');
      overlay.classList.remove('open');
    });
  }

  fetch('/api/auth/me')
    .then((r) => r.json())
    .then((data) => {
      const bottom = document.getElementById('sidebar-bottom');
      if (!bottom) return;
      if (data.loggedIn) {
        bottom.innerHTML = `
          <div class="sidebar-user">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
            ${data.user.username}${data.user.isAdmin ? ' <span class="badge badge-admin" style="margin-left:4px;padding:2px 6px;font-size:0.68rem;">Admin</span>' : ''}
          </div>
          <button class="btn btn-ghost btn-sm" id="logout-btn" style="width:100%">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Logout
          </button>
        `;
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
          logoutBtn.addEventListener('click', async () => {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/';
          });
        }
        if (data.user.isAdmin) {
          const adminLinks = document.getElementById('admin-links');
          if (adminLinks) {
            adminLinks.innerHTML = `
              <a class="sidebar-link${currentPath === '/admin' ? ' active' : ''}" href="/admin">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Admin
              </a>
              <a class="sidebar-link${currentPath === '/manager-user' ? ' active' : ''}" href="/manager-user">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
                Users
              </a>
            `;
          }
        }
        window._currentUser = data.user;
      } else {
        window._currentUser = null;
      }
      window.dispatchEvent(new Event('auth-ready'));
    })
    .catch(() => {
      window._currentUser = null;
      window.dispatchEvent(new Event('auth-ready'));
    });
})();
