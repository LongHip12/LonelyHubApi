(function () {
  const params = new URLSearchParams(window.location.search);
  const method = params.get('method') || 'login';
  const redirect = params.get('redirect') || '/';

  const loginTab = document.getElementById('tab-login');
  const registerTab = document.getElementById('tab-register');
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');

  function showTab(tab) {
    if (tab === 'login') {
      loginTab.classList.add('active');
      registerTab.classList.remove('active');
      loginForm.style.display = 'block';
      registerForm.style.display = 'none';
    } else {
      registerTab.classList.add('active');
      loginTab.classList.remove('active');
      registerForm.style.display = 'block';
      loginForm.style.display = 'none';
    }
  }

  showTab(method);

  loginTab.addEventListener('click', () => { showTab('login'); history.replaceState(null, '', `/auth?method=login`); });
  registerTab.addEventListener('click', () => { showTab('register'); history.replaceState(null, '', `/auth?method=register`); });

  const loginBtn = document.getElementById('btn-login');
  if (loginBtn) {
    loginBtn.addEventListener('click', async () => {
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value;
      if (!username || !password) { toast('Please fill all fields', 'error'); return; }
      loginBtn.disabled = true;
      loginBtn.textContent = 'Logging in...';
      try {
        const res = await api.post('/api/auth/login', { username, password });
        if (res.error) { toast(res.error, 'error'); return; }
        toast('Logged in successfully!', 'success');
        setTimeout(() => { window.location.href = redirect; }, 600);
      } catch { toast('Login failed', 'error'); }
      finally { loginBtn.disabled = false; loginBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Login'; }
    });
  }

  const registerBtn = document.getElementById('btn-register');
  if (registerBtn) {
    registerBtn.addEventListener('click', async () => {
      const username = document.getElementById('reg-username').value.trim();
      const password = document.getElementById('reg-password').value;
      const confirm = document.getElementById('reg-confirm').value;
      if (!username || !password) { toast('Please fill all fields', 'error'); return; }
      if (password !== confirm) { toast('Passwords do not match', 'error'); return; }
      registerBtn.disabled = true;
      registerBtn.textContent = 'Creating account...';
      try {
        const res = await api.post('/api/auth/register', { username, password });
        if (res.error) { toast(res.error, 'error'); return; }
        toast('Account created! Redirecting...', 'success');
        setTimeout(() => { window.location.href = redirect; }, 700);
      } catch { toast('Registration failed', 'error'); }
      finally { registerBtn.disabled = false; registerBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg> Register'; }
    });
  }

  document.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const activeForm = loginForm.style.display !== 'none' ? loginBtn : registerBtn;
        if (activeForm) activeForm.click();
      }
    });
  });

  window.addEventListener('auth-ready', () => {
    if (window._currentUser) window.location.href = redirect;
  });
})();
