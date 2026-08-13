/**
 * Finances Bot Dashboard — SPA JavaScript
 *
 * Architecture:
 *  - Hash-based router: #overview, #bot, #database, #parser, #alerts, #groups, #errors, #config, #users
 *  - Auth state stored in memory (cookie validated server-side)
 *  - Auto-refresh every 30 seconds for the active section
 *  - Charts powered by Chart.js (loaded from CDN)
 */

'use strict';

// ─── Constants ────────────────────────────────────────────────────────────────
const REFRESH_INTERVAL_MS = 30_000;
const API = {
  requestOtp:   '/api/auth/request-otp',
  verifyOtp:    '/api/auth/verify-otp',
  logout:       '/api/auth/logout',
  health:       '/api/health',
  overview:     '/api/stats/overview',
  activity:     '/api/stats/activity',
  users:        '/api/stats/users',
  database:     '/api/stats/database',
  bot:          '/api/stats/bot',
  parser:       '/api/stats/parser',
  alerts:       '/api/stats/alerts',
  groups:       '/api/stats/groups',
  errors:       '/api/stats/errors',
  config:       '/api/config',
  configFeature: '/api/config/features',
  restart:      '/api/actions/restart',
  checkStatus:  '/api/auth/check-status',
};

const NAV_ITEMS = [
  { id: 'overview', icon: '📊', label: 'Overview' },
  { id: 'bot',      icon: '🤖', label: 'Bot Status' },
  { id: 'database', icon: '🗄️', label: 'Database' },
  { id: 'parser',   icon: '⚙️', label: 'Parser' },
  { id: 'alerts',   icon: '🔔', label: 'Alerts' },
  { id: 'groups',   icon: '👥', label: 'Groups' },
  { id: 'errors',   icon: '❌', label: 'Error Log' },
  { id: 'users',    icon: '👤', label: 'Users' },
  { id: 'config',   icon: '🛠️', label: 'Config' },
];

// ─── State ─────────────────────────────────────────────────────────────────
const state = {
  currentPage: 'overview',
  isLoggedIn: false,
  loginStep: 1,       // 1 = enter TG ID, 2 = enter OTP
  telegramId: null,
  reqId: null,
  authPollTimer: null,
  refreshTimer: null,
  lastRefresh: null,
  charts: {},
  logFilter: 'ALL',
  logData: [],
};

// ─── Utility ──────────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '—';
  if (typeof n !== 'number') return n;
  return n.toLocaleString('en-US');
}

function fmtBytes(mb) {
  if (mb == null) return '—';
  if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
  if (mb < 1024) return `${mb.toFixed(2)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

function timeSince(iso) {
  if (!iso) return '—';
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ─── API Client ───────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  const merged = { ...defaults, ...opts, headers: { ...defaults.headers, ...opts.headers } };
  const res = await fetch(url, merged);
  if (res.status === 401) {
    handleLogout();
    return null;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Snackbar ─────────────────────────────────────────────────────────────────
function showSnack(msg, type = '') {
  const container = document.getElementById('snackbar-container');
  const el = document.createElement('div');
  el.className = `snackbar${type ? ' snack-' + type : ''}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
async function checkAuth() {
  try {
    const data = await fetch(API.overview, { credentials: 'same-origin' });
    return data.ok;
  } catch { return false; }
}

function startAuthPolling(reqId) {
  clearInterval(state.authPollTimer);
  state.reqId = reqId;
  state.authPollTimer = setInterval(async () => {
    if (!state.reqId || state.isLoggedIn) {
      clearInterval(state.authPollTimer);
      return;
    }
    try {
      const res = await fetch(`${API.checkStatus}?req_id=${state.reqId}`, { credentials: 'same-origin' });
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.status === 'approved') {
        clearInterval(state.authPollTimer);
        state.isLoggedIn = true;
        showSnack('✅ Login approved via Telegram!', 'success');
        renderDashboard();
      } else if (data && data.status === 'blocked') {
        clearInterval(state.authPollTimer);
        showSnack('⛔ IP address blacklisted by admin!', 'error');
        goBackToStep1();
      }
    } catch {
      // Ignore poll error
    }
  }, 1500);
}

async function handleRequestOtp(e) {
  e.preventDefault();
  const tidInput = document.getElementById('tg-id-input');
  const tid = parseInt(tidInput.value.trim(), 10);
  if (!tid || isNaN(tid)) { showSnack('Enter a valid Telegram ID', 'error'); return; }

  const btn = document.getElementById('otp-request-btn');
  btn.disabled = true;
  btn.textContent = 'Sending…';

  try {
    const res = await apiFetch(API.requestOtp, {
      method: 'POST',
      body: JSON.stringify({ telegram_id: tid }),
    });
    state.telegramId = tid;
    state.reqId = res.req_id;
    state.loginStep = 2;
    renderLoginStep2();
    startAuthPolling(res.req_id);
    showSnack('Verification code and approval buttons sent to Telegram!', 'success');
  } catch (err) {
    showSnack(err.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Send Code';
  }
}

async function handleVerifyOtp(otpCode) {
  if (otpCode.length !== 6) return;

  const btn = document.getElementById('otp-verify-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Verifying…'; }

  try {
    await apiFetch(API.verifyOtp, {
      method: 'POST',
      body: JSON.stringify({ telegram_id: state.telegramId, otp: otpCode }),
    });
    state.isLoggedIn = true;
    renderDashboard();
  } catch (err) {
    showSnack(err.message || 'Invalid code', 'error');
    // Shake OTP display
    document.querySelector('.otp-display')?.classList.add('shake');
    setTimeout(() => document.querySelector('.otp-display')?.classList.remove('shake'), 500);
    resetOtpDigits();
    if (btn) { btn.disabled = false; btn.textContent = 'Verify'; }
  }
}

async function handleLogout() {
  await apiFetch(API.logout, { method: 'POST' }).catch(() => {});
  state.isLoggedIn = false;
  state.loginStep = 1;
  state.telegramId = null;
  clearInterval(state.refreshTimer);
  renderLogin();
}

// ─── OTP digit display ────────────────────────────────────────────────────────
let otpValue = '';

function renderOtpDigits() {
  const digits = document.querySelectorAll('.otp-digit');
  digits.forEach((d, i) => {
    d.textContent = otpValue[i] || '';
    d.classList.toggle('filled', i < otpValue.length);
    d.classList.toggle('active', i === otpValue.length);
  });
}

function resetOtpDigits() {
  otpValue = '';
  renderOtpDigits();
}

function handleOtpPaste(e) {
  const clipboardData = e.clipboardData || window.clipboardData;
  if (!clipboardData) return;
  const pastedText = clipboardData.getData('text') || '';
  const digits = pastedText.replace(/\D/g, '').slice(0, 6);
  if (digits) {
    otpValue = digits;
    renderOtpDigits();
    if (otpValue.length === 6) {
      setTimeout(() => handleVerifyOtp(otpValue), 300);
    }
  }
}

function handleOtpKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v') {
    return;
  }
  if (e.key >= '0' && e.key <= '9' && otpValue.length < 6) {
    otpValue += e.key;
    renderOtpDigits();
    if (otpValue.length === 6) {
      setTimeout(() => handleVerifyOtp(otpValue), 300);
    }
  } else if (e.key === 'Backspace') {
    otpValue = otpValue.slice(0, -1);
    renderOtpDigits();
  }
}

// ─── Render: Login ────────────────────────────────────────────────────────────
function renderLogin() {
  document.getElementById('app').innerHTML = `
    <div id="login-page">
      <div class="login-card">
        <div class="login-logo">💰</div>
        <h1 class="login-title">Admin Dashboard</h1>
        <p class="login-subtitle">finances-bot — secure admin access</p>

        <!-- Step 1: Enter Telegram ID -->
        <div class="login-step" id="login-step-1">
          <form id="otp-form">
            <div class="text-field">
              <label for="tg-id-input">Your Telegram ID</label>
              <input id="tg-id-input" type="text" inputmode="numeric" pattern="[0-9]*" placeholder="e.g. 123456789"
                     autocomplete="off" required />
            </div>
            <button class="btn btn-filled w-full" id="otp-request-btn" type="submit"
                    style="justify-content:center;margin-top:8px">
              Send Verification Code
            </button>
          </form>
          <p class="body-small text-muted mt-md" style="text-align:center">
            A 6-digit code will be sent to your Telegram via the bot.
          </p>
        </div>

        <!-- Step 2: Enter OTP -->
        <div class="login-step hidden" id="login-step-2">
          <p class="body-medium text-muted mb-md" style="text-align:center">
            Click <b>Approve</b> in Telegram or enter the 6-digit code:
          </p>
          <div class="otp-display" id="otp-display" tabindex="0"
               style="cursor:text; outline:none">
            ${Array(6).fill(0).map((_, i) =>
              `<div class="otp-digit" id="otp-d-${i}"></div>`).join('')}
          </div>
          <input class="otp-input-hidden" id="otp-hidden-input" type="number"
                 inputmode="numeric" maxlength="6" />
          <button class="btn btn-filled w-full mt-md" id="otp-verify-btn"
                  style="justify-content:center" onclick="handleVerifyOtp(otpValue)">
            Verify & Login
          </button>
          <button class="btn btn-text w-full mt-sm" style="justify-content:center"
                  onclick="goBackToStep1()">← Change Telegram ID</button>
        </div>
      </div>
    </div>
    <div id="snackbar-container" class="snackbar-container"></div>
  `;

  document.getElementById('otp-form')?.addEventListener('submit', handleRequestOtp);
}

function renderLoginStep2() {
  document.getElementById('login-step-1').classList.add('hidden');
  const s2 = document.getElementById('login-step-2');
  s2.classList.remove('hidden');
  otpValue = '';
  renderOtpDigits();

  document.removeEventListener('keydown', handleOtpKeydown);
  document.addEventListener('keydown', handleOtpKeydown);
  document.removeEventListener('paste', handleOtpPaste);
  document.addEventListener('paste', handleOtpPaste);
}

function goBackToStep1() {
  clearInterval(state.authPollTimer);
  state.reqId = null;
  document.removeEventListener('keydown', handleOtpKeydown);
  document.removeEventListener('paste', handleOtpPaste);
  state.loginStep = 1;
  state.telegramId = null;
  document.getElementById('login-step-2').classList.add('hidden');
  document.getElementById('login-step-1').classList.remove('hidden');
  const btn = document.getElementById('otp-request-btn');
  if (btn) { btn.disabled = false; btn.textContent = 'Send Verification Code'; }
}

// ─── Render: Dashboard Shell ──────────────────────────────────────────────────
function renderDashboard() {
  const isDark = !document.documentElement.dataset.theme;

  document.getElementById('app').innerHTML = `
    <nav class="nav-rail" id="nav-rail">
      <div class="nav-rail-logo">💰</div>
      ${NAV_ITEMS.map(item => `
        <button class="nav-item${item.id === state.currentPage ? ' active' : ''}"
                id="nav-${item.id}" onclick="navigate('${item.id}')" title="${item.label}">
          <div class="nav-item-indicator">
            <span class="nav-item-icon">${item.icon}</span>
          </div>
          <span class="nav-item-label">${item.label}</span>
        </button>
      `).join('')}
      <div class="nav-spacer"></div>
      <div class="nav-divider"></div>
      <button class="nav-item" onclick="handleLogout()" title="Logout">
        <div class="nav-item-indicator">
          <span class="nav-item-icon">🚪</span>
        </div>
        <span class="nav-item-label">Logout</span>
      </button>
    </nav>

    <main class="main-content" id="main-content">
      <!-- Pages inserted here -->
      ${NAV_ITEMS.map(item => `
        <div class="page${item.id === state.currentPage ? ' active' : ''}" id="page-${item.id}">
          <div class="empty-state">
            <div class="empty-state-icon skeleton" style="width:48px;height:48px;border-radius:50%"></div>
            <div class="skeleton" style="width:200px;height:20px;margin-top:8px"></div>
          </div>
        </div>
      `).join('')}
    </main>

    <div id="snackbar-container" class="snackbar-container"></div>

    <!-- Global top bar injected per page -->
  `;

  // Theme toggle button floated in top-right
  const themeBtn = document.createElement('button');
  themeBtn.className = 'theme-btn';
  themeBtn.style.cssText = 'position:fixed;top:16px;right:16px;z-index:200;';
  themeBtn.title = 'Toggle theme';
  themeBtn.innerHTML = isDark ? '☀️' : '🌙';
  themeBtn.onclick = toggleTheme;
  document.body.appendChild(themeBtn);

  loadPage(state.currentPage);
  startRefresh();
}

// ─── Router ───────────────────────────────────────────────────────────────────
function navigate(pageId) {
  state.currentPage = pageId;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelector(`#nav-${pageId}`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  document.querySelector(`#page-${pageId}`)?.classList.add('active');
  loadPage(pageId);
}

function loadPage(pageId) {
  switch (pageId) {
    case 'overview': return loadOverview();
    case 'bot':      return loadBot();
    case 'database': return loadDatabase();
    case 'parser':   return loadParser();
    case 'alerts':   return loadAlerts();
    case 'groups':   return loadGroups();
    case 'errors':   return loadErrors();
    case 'users':    return loadUsers();
    case 'config':   return loadConfig();
  }
}

function startRefresh() {
  clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(() => {
    loadPage(state.currentPage);
  }, REFRESH_INTERVAL_MS);
}

// ─── Top Bar Helper ───────────────────────────────────────────────────────────
function makeTopBar(title, subtitle = '') {
  const now = new Date().toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
  return `
    <div class="top-bar">
      <div>
        <div class="top-bar-title">${title}</div>
        ${subtitle ? `<div class="top-bar-subtitle">${subtitle}</div>` : ''}
      </div>
      <div class="refresh-badge">
        <div class="refresh-dot"></div>
        Updated ${now}
      </div>
    </div>
  `;
}

// ─── Page: Overview ───────────────────────────────────────────────────────────
async function loadOverview() {
  const page = document.getElementById('page-overview');
  try {
    const [d, act] = await Promise.all([
      apiFetch(API.overview),
      apiFetch(API.activity + '?days=14'),
    ]);
    if (!d) return;

    const retentionColor = d.retention_rate >= 50 ? 'var(--md-success)' :
                           d.retention_rate >= 20 ? 'var(--md-warning)' : 'var(--md-error)';

    page.innerHTML = `
      ${makeTopBar('Overview', 'Key performance indicators')}

      <div class="kpi-grid">
        ${kpiCard('👥', 'Total Users', fmt(d.total_users), '', '#D0BCFF')}
        ${kpiCard('🔥', 'Active Today (DAU)', fmt(d.dau), `${d.retention_rate}% retention`, '#EFB8C8')}
        ${kpiCard('📅', 'Weekly (WAU)', fmt(d.wau), '', '#A8D5A2')}
        ${kpiCard('🗓️', 'Monthly (MAU)', fmt(d.mau), '', '#80DEEA')}
        ${kpiCard('💎', 'Premium Users', fmt(d.premium), `${d.total_users ? Math.round(d.premium/d.total_users*100) : 0}% of total`, '#FFD180')}
        ${kpiCard('📨', 'Requests Today', fmt(d.requests_today), `${fmt(d.requests_week)} this week`, '#CE93D8')}
        ${kpiCard('🔔', 'Active Alerts', fmt(d.active_alerts), '', '#80CBC4')}
        ${kpiCard('❌', 'Errors Today', fmt(d.errors_today), d.errors_today > 0 ? 'Check error log' : 'All clear', d.errors_today > 0 ? '#EF9A9A' : '#A8D5A2')}
        ${kpiCard('🔄', 'Parser Cycles', fmt(d.parser_cycles_today), 'today', '#BCAAA4')}
        ${kpiCard('👥', 'Groups', fmt(d.total_groups), 'registered', '#B0BEC5')}
      </div>

      <div class="section-grid section-grid-2">
        <div class="card">
          <div class="card-title">User Activity — 14 Days</div>
          <div class="chart-wrap">
            <canvas id="activity-chart"></canvas>
          </div>
        </div>
        <div class="card">
          <div class="card-title">Requests — 14 Days</div>
          <div class="chart-wrap">
            <canvas id="requests-chart"></canvas>
          </div>
        </div>
      </div>
    `;

    if (act?.days) {
      const labels = act.days.map(d => d.date.slice(5));
      const dauData = act.days.map(d => d.dau);
      const reqData = act.days.map(d => d.requests);

      renderLineChart('activity-chart', labels, dauData, 'DAU', '#D0BCFF');
      renderLineChart('requests-chart', labels, reqData, 'Requests', '#EFB8C8');
    }

  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

function kpiCard(icon, label, value, sub, accent = 'var(--md-primary)') {
  return `
    <div class="kpi-card" style="--kpi-accent:${accent}">
      <span class="kpi-icon">${icon}</span>
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value ?? '—'}</div>
      ${sub ? `<div class="kpi-sub">${sub}</div>` : ''}
    </div>
  `;
}

// ─── Page: Bot Status ─────────────────────────────────────────────────────────
async function loadBot() {
  const page = document.getElementById('page-bot');
  try {
    const d = await apiFetch(API.bot);
    if (!d) return;

    const isActive = d.service_status === 'active';
    const ramPct = d.sys_ram_pct || 0;
    const cpuPct = d.sys_cpu_pct || 0;
    const diskPct = d.disk_pct || 0;

    page.innerHTML = `
      ${makeTopBar('Bot Status', d.bot_version || 'finances-bot')}

      <div class="section-grid section-grid-3 mb-lg">
        <div class="card" style="grid-column: span 1">
          <div class="card-title">Service</div>
          <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
            <span class="badge ${isActive ? 'badge-success' : 'badge-error'}">
              <div class="status-dot ${isActive ? 'status-dot-green' : 'status-dot-red'}"></div>
              ${d.service_status || 'unknown'}
            </span>
          </div>
          ${d.started_at ? `<div class="text-muted body-small mt-sm">Since: ${d.started_at}</div>` : ''}
          ${d.bot_pid ? `<div class="text-muted body-small">PID: <span class="text-mono">${d.bot_pid}</span></div>` : ''}
          ${d.bot_threads ? `<div class="text-muted body-small">Threads: <span class="text-mono">${d.bot_threads}</span></div>` : ''}
        </div>

        <div class="card">
          <div class="card-title">Process Memory</div>
          ${gaugeRing(d.bot_ram_mb ? Math.min(Math.round(d.bot_ram_mb / (d.sys_ram_total_gb * 1024) * 100), 100) : 0,
                      d.bot_ram_mb ? `${d.bot_ram_mb} MB` : '—', '#D0BCFF')}
          <div class="text-muted body-small mt-sm">Bot process RAM usage</div>
        </div>

        <div class="card">
          <div class="card-title">Bot CPU</div>
          ${gaugeRing(Math.round(d.bot_cpu_pct || 0), `${d.bot_cpu_pct || 0}%`, '#EFB8C8')}
          <div class="text-muted body-small mt-sm">Bot process CPU %</div>
        </div>
      </div>

      <div class="section-grid section-grid-2 mb-lg">
        <div class="card">
          <div class="card-title">System RAM</div>
          <div style="margin-top:8px">
            <div class="flex justify-between mb-md">
              <span class="body-medium">${d.sys_ram_used_gb} GB used</span>
              <span class="text-muted body-small">of ${d.sys_ram_total_gb} GB</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill ${ramPct>90?'danger':ramPct>70?'warning':''}"
                   style="width:${ramPct}%"></div>
            </div>
            <div class="text-muted body-small mt-sm">${ramPct}% used</div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">System CPU & Load</div>
          <div style="margin-top:8px">
            <div class="progress-bar mb-md">
              <div class="progress-fill ${cpuPct>90?'danger':cpuPct>70?'warning':''}"
                   style="width:${cpuPct}%"></div>
            </div>
            <div class="metric-row">
              <span class="metric-key">CPU</span>
              <span class="metric-val">${cpuPct}% (${d.sys_cpu_cores} cores)</span>
            </div>
            <div class="metric-row">
              <span class="metric-key">Load avg 1m</span>
              <span class="metric-val">${d.load_avg_1m}</span>
            </div>
            <div class="metric-row">
              <span class="metric-key">Load avg 5m</span>
              <span class="metric-val">${d.load_avg_5m}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Disk</div>
          <div style="margin-top:8px">
            <div class="flex justify-between mb-md">
              <span class="body-medium">${d.disk_used_gb} GB used</span>
              <span class="text-muted body-small">of ${d.disk_total_gb} GB</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill ${diskPct>90?'danger':diskPct>70?'warning':''}"
                   style="width:${diskPct}%"></div>
            </div>
            <div class="text-muted body-small mt-sm">${diskPct}% used</div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">System Info</div>
          <div style="margin-top:8px">
            <div class="metric-row">
              <span class="metric-key">OS</span>
              <span class="metric-val">${d.os}</span>
            </div>
            <div class="metric-row">
              <span class="metric-key">Python</span>
              <span class="metric-val text-mono">${d.python_version}</span>
            </div>
            <div class="metric-row">
              <span class="metric-key">Hostname</span>
              <span class="metric-val text-mono">${d.hostname}</span>
            </div>
            <div class="metric-row">
              <span class="metric-key">Bot version</span>
              <span class="metric-val">${d.bot_version}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex gap-md">
        <button class="btn btn-danger" onclick="confirmRestart()">🔄 Restart Bot</button>
      </div>
    `;
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

function gaugeRing(pct, label, color = '#D0BCFF') {
  const r = 30, cx = 40, cy = 40, circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct / 100);
  const strokeColor = pct > 90 ? 'var(--md-error)' : pct > 70 ? 'var(--md-warning)' : color;
  return `
    <div class="gauge-wrap">
      <div class="gauge-ring">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle class="gauge-ring-bg" cx="${cx}" cy="${cy}" r="${r}" />
          <circle class="gauge-ring-fill" cx="${cx}" cy="${cy}" r="${r}"
            stroke="${strokeColor}"
            stroke-dasharray="${circ}"
            stroke-dashoffset="${offset}" />
        </svg>
        <div class="gauge-label">${label}</div>
      </div>
      <div>
        <div class="title-medium">${pct}%</div>
        <div class="text-muted body-small">of system RAM</div>
      </div>
    </div>
  `;
}

async function confirmRestart() {
  if (!confirm('Restart finances-bot service? The bot will be unavailable for ~5 seconds.')) return;
  try {
    await apiFetch(API.restart, { method: 'POST' });
    showSnack('✅ Bot restarted successfully', 'success');
    setTimeout(loadBot, 3000);
  } catch (err) {
    showSnack('Restart failed: ' + err.message, 'error');
  }
}

// ─── Page: Database ────────────────────────────────────────────────────────────
async function loadDatabase() {
  const page = document.getElementById('page-database');
  try {
    const d = await apiFetch(API.database);
    if (!d) return;

    const colRows = (d.collections || []).map(c => `
      <tr>
        <td class="text-mono">${escapeHtml(c.name)}</td>
        <td class="text-mono">${fmt(c.count)}</td>
        <td class="text-mono">${fmtBytes(c.size_kb / 1024)}</td>
        <td class="text-mono">${c.avg_obj_size_bytes ? c.avg_obj_size_bytes + 'B' : '—'}</td>
      </tr>
    `).join('');

    page.innerHTML = `
      ${makeTopBar('Database', `MongoDB — ${d.num_collections} collections`)}

      <div class="kpi-grid mb-lg" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr))">
        ${kpiCard('💾', 'Data Size', fmtBytes(d.total_size_mb), '', '#A8D5A2')}
        ${kpiCard('🗃️', 'Storage', fmtBytes(d.storage_size_mb), 'on disk', '#80DEEA')}
        ${kpiCard('📑', 'Indexes', fmtBytes(d.index_size_mb), 'total index size', '#FFD180')}
        ${kpiCard('🔌', 'Connections', `${d.connections_current}`, `${d.connections_available} available`, '#D0BCFF')}
        ${kpiCard('🏷️', 'MongoDB', d.mongo_version || '—', '', '#BCAAA4')}
      </div>

      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Collections</div>
        <div style="overflow-x:auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Collection</th>
                <th>Documents</th>
                <th>Size</th>
                <th>Avg Doc Size</th>
              </tr>
            </thead>
            <tbody>${colRows}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

// ─── Page: Parser ─────────────────────────────────────────────────────────────
async function loadParser() {
  const page = document.getElementById('page-parser');
  try {
    const d = await apiFetch(API.parser);
    if (!d) return;

    const errRows = (d.parser_errors || []).map(e => `
      <tr>
        <td class="text-mono">${escapeHtml(e.source)}</td>
        <td><span class="badge badge-error">${fmt(e.count)}</span></td>
        <td class="truncate text-muted" style="max-width:280px" title="${escapeHtml(e.last_error)}">
          ${escapeHtml(e.last_error?.slice(0, 80))}
        </td>
        <td class="text-muted body-small">${timeSince(e.last_seen)}</td>
      </tr>
    `).join('');

    page.innerHTML = `
      ${makeTopBar('Parser Status', 'Fiat · Crypto · Stocks')}

      <div class="section-grid section-grid-3 mb-lg">
        ${parserCard('💱', 'Fiat Parser', d.fiat.last_updated, d.fiat.count + ' currencies cached', d.fiat.last_updated)}
        ${parserCard('🪙', 'Crypto Parser', d.crypto.last_updated, 'via Binance/Bybit', d.crypto.last_updated)}
        ${parserCard('📈', 'Stocks Parser', d.stocks.last_updated, 'via yfinance', d.stocks.last_updated)}
      </div>

      <div class="kpi-grid mb-lg" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr))">
        ${kpiCard('🔄', 'Cycles Today', fmt(d.cycles_today), '', '#D0BCFF')}
        ${kpiCard('🔴', 'Error Sources', fmt((d.parser_errors || []).length), '', '#EF9A9A')}
      </div>

      ${errRows ? `
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Problematic Sources</div>
          <div style="overflow-x:auto">
            <table class="data-table">
              <thead><tr>
                <th>Source</th><th>Error Count</th><th>Last Error</th><th>Last Seen</th>
              </tr></thead>
              <tbody>${errRows}</tbody>
            </table>
          </div>
        </div>
      ` : `<div class="card"><div class="empty-state">
              <div class="empty-state-icon">✅</div>
              <div class="empty-state-text">All data sources operating normally</div>
            </div></div>`}
    `;
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

function parserCard(icon, name, lastUpdated, sub, ts) {
  const isOld = ts && (Date.now() - new Date(ts)) > 4 * 3600_000;
  const status = !ts ? 'neutral' : isOld ? 'warning' : 'success';
  return `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-size:24px;margin-bottom:8px">${icon}</div>
          <div class="title-medium">${name}</div>
          <div class="text-muted body-small mt-sm">${sub}</div>
        </div>
        <span class="badge badge-${status}">
          <div class="status-dot status-dot-${status === 'success' ? 'green' : status === 'warning' ? 'yellow' : 'gray'}"></div>
          ${status === 'success' ? 'OK' : status === 'warning' ? 'Stale' : 'Unknown'}
        </span>
      </div>
      <div class="text-muted body-small mt-md">Updated: ${timeSince(lastUpdated)}</div>
    </div>
  `;
}

// ─── Page: Alerts ─────────────────────────────────────────────────────────────
async function loadAlerts() {
  const page = document.getElementById('page-alerts');
  try {
    const d = await apiFetch(API.alerts);
    if (!d) return;

    const topRows = (d.top_currencies || []).map((c, i) => `
      <tr>
        <td>${i + 1}</td>
        <td class="text-mono">${escapeHtml(c.currency)}</td>
        <td><span class="badge badge-primary">${fmt(c.count)}</span></td>
      </tr>
    `).join('');

    page.innerHTML = `
      ${makeTopBar('Price Alerts', 'Active monitoring')}

      <div class="kpi-grid mb-lg" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">
        ${kpiCard('🔔', 'Total Alerts', fmt(d.total), '', '#D0BCFF')}
        ${kpiCard('✅', 'Active', fmt(d.active), 'pending trigger', '#A8D5A2')}
        ${kpiCard('🔕', 'Triggered', fmt(d.triggered), 'completed', '#EF9A9A')}
      </div>

      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Top Currencies in Alerts</div>
        ${topRows ? `
          <table class="data-table">
            <thead><tr><th>#</th><th>Currency</th><th>Alert Count</th></tr></thead>
            <tbody>${topRows}</tbody>
          </table>
        ` : '<div class="empty-state"><div class="empty-state-text">No active alerts</div></div>'}
      </div>
    `;

    // Pie chart for alerts
    if (d.total > 0) {
      const chartHtml = `<div class="chart-wrap-sm" style="max-width:280px;margin:16px auto 0">
        <canvas id="alerts-chart"></canvas></div>`;
      document.querySelector('#page-alerts .card').insertAdjacentHTML('beforeend', chartHtml);

      renderDoughnutChart('alerts-chart',
        ['Active', 'Triggered'],
        [d.active, d.triggered],
        ['#A8D5A2', '#EF9A9A']);
    }
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

// ─── Page: Groups ─────────────────────────────────────────────────────────────
async function loadGroups() {
  const page = document.getElementById('page-groups');
  try {
    const d = await apiFetch(API.groups);
    if (!d) return;

    const rows = (d.recent || []).map(g => `
      <tr>
        <td class="text-mono truncate" style="max-width:200px">${escapeHtml(g.title)}</td>
        <td class="text-mono">${g.chat_id}</td>
        <td>${g.member_count ? fmt(g.member_count) : '—'}</td>
        <td>
          <span class="badge ${g.is_active ? 'badge-success' : 'badge-neutral'}">
            <div class="status-dot ${g.is_active ? 'status-dot-green' : 'status-dot-gray'}"></div>
            ${g.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td class="text-muted body-small">${timeSince(g.added_at)}</td>
      </tr>
    `).join('');

    page.innerHTML = `
      ${makeTopBar('Groups', 'Bot group installations')}

      <div class="kpi-grid mb-lg" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">
        ${kpiCard('👥', 'Total Groups', fmt(d.total), '', '#D0BCFF')}
        ${kpiCard('✅', 'Active', fmt(d.active), '', '#A8D5A2')}
        ${kpiCard('❌', 'Inactive', fmt(d.inactive), 'bot removed', '#EF9A9A')}
      </div>

      <div class="card">
        <div class="card-title" style="margin-bottom:16px">Recent Groups</div>
        ${rows ? `
          <div style="overflow-x:auto">
            <table class="data-table">
              <thead><tr>
                <th>Title</th><th>Chat ID</th><th>Members</th><th>Status</th><th>Added</th>
              </tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        ` : '<div class="empty-state"><div class="empty-state-text">No groups yet</div></div>'}
      </div>
    `;
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

// ─── Page: Error Log ──────────────────────────────────────────────────────────
async function loadErrors() {
  const page = document.getElementById('page-errors');
  try {
    const d = await apiFetch(API.errors);
    if (!d) return;
    state.logData = d.errors || [];
    renderErrorLog(page);
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

function renderErrorLog(page) {
  const filtered = state.logFilter === 'ALL'
    ? state.logData
    : state.logData.filter(l => l.level === state.logFilter);

  const levels = ['ALL', 'ERROR', 'WARNING', 'INFO', 'CRITICAL'];

  const logLines = filtered.map(l => `
    <div class="log-line">
      <span class="log-ts">${l.timestamp || ''}</span>
      <span class="log-level log-level-${l.level}">${l.level}</span>
      <span class="log-msg">${escapeHtml(l.message)}</span>
    </div>
  `).join('');

  page.innerHTML = `
    ${makeTopBar('Error Log', 'logs/errors.log — newest first')}

    <div class="chip-row">
      ${levels.map(lvl => `
        <button class="chip${state.logFilter === lvl ? ' active' : ''}"
                onclick="filterLog('${lvl}')">
          ${lvl === 'ALL' ? 'All' : lvl}
          ${lvl === 'ERROR' ? `<span class="badge badge-error" style="padding:1px 6px;font-size:10px">${state.logData.filter(l=>l.level==='ERROR').length}</span>` : ''}
        </button>
      `).join('')}
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div class="card-title">
          ${filtered.length} line${filtered.length !== 1 ? 's' : ''}
          ${state.logFilter !== 'ALL' ? `(filtered: ${state.logFilter})` : ''}
        </div>
        <button class="btn btn-text btn-sm" onclick="loadErrors()">↻ Refresh</button>
      </div>
      <div class="log-viewer">
        ${logLines || '<div class="empty-state" style="padding:16px"><div class="empty-state-text">No log entries</div></div>'}
      </div>
    </div>
  `;
}

function filterLog(level) {
  state.logFilter = level;
  renderErrorLog(document.getElementById('page-errors'));
}

// ─── Page: Users ──────────────────────────────────────────────────────────────
async function loadUsers() {
  const page = document.getElementById('page-users');
  try {
    const d = await apiFetch(API.users);
    if (!d) return;

    const langRows = (d.by_language || []).slice(0, 8).map(l => `
      <tr>
        <td>${langFlag(l.language)} ${l.language}</td>
        <td class="text-mono">${fmt(l.count)}</td>
      </tr>
    `).join('');

    const userRows = (d.top_users || []).map((u, i) => `
      <tr>
        <td class="text-muted">${i + 1}</td>
        <td class="text-mono">${u.username ? '@' + escapeHtml(u.username) : escapeHtml(String(u.id))}</td>
        <td>${langFlag(u.language)} ${u.language}</td>
        <td>${u.premium ? '<span class="badge badge-warning">💎 Premium</span>' : '<span class="text-muted">—</span>'}</td>
        <td class="text-mono">${fmt(u.requests)}</td>
        <td class="text-muted body-small">${timeSince(u.last_active)}</td>
      </tr>
    `).join('');

    page.innerHTML = `
      ${makeTopBar('Users', 'User analytics & top users')}

      <div class="section-grid section-grid-2 mb-lg">
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">By Language</div>
          <table class="data-table">
            <thead><tr><th>Language</th><th>Users</th></tr></thead>
            <tbody>${langRows}</tbody>
          </table>
          <div class="chart-wrap-sm mt-md">
            <canvas id="lang-chart"></canvas>
          </div>
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Top Users by Requests</div>
          <div style="overflow-x:auto">
            <table class="data-table">
              <thead><tr><th>#</th><th>User</th><th>Lang</th><th>Plan</th><th>Reqs</th><th>Last seen</th></tr></thead>
              <tbody>${userRows}</tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // Language chart
    if (d.by_language?.length) {
      const top = d.by_language.slice(0, 7);
      renderDoughnutChart('lang-chart',
        top.map(l => l.language),
        top.map(l => l.count),
        ['#D0BCFF','#EFB8C8','#A8D5A2','#80DEEA','#FFD180','#CE93D8','#80CBC4']
      );
    }
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

function langFlag(code) {
  const flags = { en:'🇬🇧', uk:'🇺🇦', pl:'🇵🇱', cs:'🇨🇿', sk:'🇸🇰', de:'🇩🇪', fr:'🇫🇷' };
  return flags[code] || '🌐';
}

// ─── Page: Config ─────────────────────────────────────────────────────────────
async function loadConfig() {
  const page = document.getElementById('page-config');
  try {
    const d = await apiFetch(API.config);
    if (!d) return;

    const b = d.bot || {};
    const f = d.features || {};
    const p = d.parser || {};
    const dr = d.draft || {};
    const sec = d.security || {};
    const urls = d.urls || {};
    const i18n = d.i18n || {};

    page.innerHTML = `
      ${makeTopBar('Configuration', 'Editable settings from config/settings.json')}

      <div class="section-grid section-grid-2 mb-lg">

        <!-- 1. Features & Toggles -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Features & Toggles</div>
          ${toggleRow('groups_enabled', 'Group Mode', 'Allow bot to work in Telegram groups', f.groups_enabled)}
          ${toggleRow('inline_mode_enabled', 'Inline Mode', 'Allow @bot inline queries', f.inline_mode_enabled)}
          ${toggleRow('mini_app_enabled', 'Mini App', 'Enable Telegram Mini App integration', f.mini_app_enabled)}
        </div>

        <!-- 2. Bot Information -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Bot Information</div>
          <form id="form-cfg-bot" onsubmit="event.preventDefault(); saveConfigSection('bot')">
            <div class="text-field">
              <label for="cfg-bot-version">Bot Version</label>
              <input id="cfg-bot-version" name="version" type="text" value="${escapeHtml(b.version || '')}" />
            </div>
            ${formToggleRow('backup_enabled', 'Backup Enabled', 'Automatic database backups', b.backup_enabled)}
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save Bot Settings</button>
          </form>
        </div>

        <!-- 3. Parser Settings -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Parser Settings</div>
          <form id="form-cfg-parser" onsubmit="event.preventDefault(); saveConfigSection('parser')">
            ${formToggleRow('auto_update', 'Auto Update', 'Automatically fetch fiat, crypto, and stock rates', p.auto_update)}
            <div class="text-field">
              <label for="cfg-p-interval">Update Interval (seconds)</label>
              <input id="cfg-p-interval" name="update_interval_sec" type="number" value="${p.update_interval_sec || 7000}" />
            </div>
            <div class="text-field">
              <label for="cfg-p-url">Fiat Source URL</label>
              <input id="cfg-p-url" name="fiat_source_url" type="text" value="${escapeHtml(p.fiat_source_url || '')}" />
            </div>
            <div class="text-field">
              <label for="cfg-p-ttl">On-Demand Cache TTL (hours)</label>
              <input id="cfg-p-ttl" name="on_demand_cache_ttl_hours" type="number" value="${p.on_demand_cache_ttl_hours || 5}" />
            </div>
            <div class="text-field">
              <label for="cfg-p-cs-interval">Crypto/Stocks Interval (seconds)</label>
              <input id="cfg-p-cs-interval" name="crypto_stocks_interval_sec" type="number" value="${p.crypto_stocks_interval_sec || 10800}" />
            </div>
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save Parser Settings</button>
          </form>
        </div>

        <!-- 4. Draft Animation -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Draft Animation</div>
          <form id="form-cfg-draft" onsubmit="event.preventDefault(); saveConfigSection('draft')">
            ${formToggleRow('enabled', 'Animation Enabled', 'Show loading draft message animation', dr.enabled)}
            <div class="text-field">
              <label for="cfg-dr-thresh">Loading Threshold (sec)</label>
              <input id="cfg-dr-thresh" name="loading_threshold_sec" type="number" step="0.01" value="${dr.loading_threshold_sec || 0.05}" />
            </div>
            <div class="text-field">
              <label for="cfg-dr-anim">Animation Interval (sec)</label>
              <input id="cfg-dr-anim" name="animation_interval_sec" type="number" step="0.01" value="${dr.animation_interval_sec || 0.25}" />
            </div>
            <div class="text-field">
              <label for="cfg-dr-prev">Preview Delay (sec)</label>
              <input id="cfg-dr-prev" name="preview_delay_sec" type="number" step="0.01" value="${dr.preview_delay_sec || 0.15}" />
            </div>
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save Draft Settings</button>
          </form>
        </div>

        <!-- 5. Security & Rate Limits -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Security & Limits</div>
          <form id="form-cfg-security" onsubmit="event.preventDefault(); saveConfigSection('security')">
            <div class="text-field">
              <label for="cfg-sec-rate">Rate Limit (Requests per Window)</label>
              <input id="cfg-sec-rate" name="rate_limit_requests" type="number" value="${sec.rate_limit_requests || 30}" />
            </div>
            <div class="text-field">
              <label for="cfg-sec-win">Rate Limit Window (seconds)</label>
              <input id="cfg-sec-win" name="rate_limit_window_sec" type="number" value="${sec.rate_limit_window_sec || 60}" />
            </div>
            <div class="text-field">
              <label for="cfg-sec-maxmsg">Max Message Length (chars)</label>
              <input id="cfg-sec-maxmsg" name="max_message_length" type="number" value="${sec.max_message_length || 1000}" />
            </div>
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save Security Settings</button>
          </form>
        </div>

        <!-- 6. Project Links -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Project URLs</div>
          <form id="form-cfg-urls" onsubmit="event.preventDefault(); saveConfigSection('urls')">
            <div class="text-field">
              <label for="cfg-u-gh">GitHub URL</label>
              <input id="cfg-u-gh" name="github" type="text" value="${escapeHtml(urls.github || '')}" />
            </div>
            <div class="text-field">
              <label for="cfg-u-comm">Support / Chat URL</label>
              <input id="cfg-u-comm" name="communication" type="text" value="${escapeHtml(urls.communication || '')}" />
            </div>
            <div class="text-field">
              <label for="cfg-u-inv">Bot Invite URL</label>
              <input id="cfg-u-inv" name="invite" type="text" value="${escapeHtml(urls.invite || '')}" />
            </div>
            <div class="text-field">
              <label for="cfg-u-donate">Donation URL (Donatello)</label>
              <input id="cfg-u-donate" name="donatello" type="text" value="${escapeHtml(urls.donatello || '')}" />
            </div>
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save URL Settings</button>
          </form>
        </div>

        <!-- 7. i18n Settings -->
        <div class="card">
          <div class="card-title" style="margin-bottom:16px">Language & i18n</div>
          <form id="form-cfg-i18n" onsubmit="event.preventDefault(); saveConfigSection('i18n')">
            <div class="text-field">
              <label for="cfg-i18n-default">Default Language</label>
              <select id="cfg-i18n-default" name="default_language" class="text-field input" style="background:var(--md-surface-container-highest);color:var(--md-on-surface);padding:12px;border:none;border-bottom:2px solid var(--md-outline)">
                ${['en','uk','pl','cs','sk','de','fr'].map(l =>
                  `<option value="${l}" ${i18n.default_language === l ? 'selected' : ''}>${langFlag(l)} ${l}</option>`
                ).join('')}
              </select>
            </div>
            <button class="btn btn-filled btn-sm mt-md" type="submit">💾 Save Language Settings</button>
          </form>
        </div>

      </div>
    `;
  } catch (err) {
    page.innerHTML = errorState(err.message);
  }
}

async function saveConfigSection(section) {
  const form = document.getElementById(`form-cfg-${section}`);
  if (!form) return;

  const formData = new FormData(form);
  const settings = {};

  form.querySelectorAll('input, select').forEach(el => {
    if (!el.name) return;
    if (el.type === 'checkbox') {
      settings[el.name] = el.checked;
    } else if (el.type === 'number') {
      const v = el.value.trim();
      settings[el.name] = v.includes('.') ? parseFloat(v) : parseInt(v, 10);
    } else {
      settings[el.name] = el.value.trim();
    }
  });

  try {
    await apiFetch('/api/config/update', {
      method: 'POST',
      body: JSON.stringify({ section, settings }),
    });
    showSnack(`✅ Section '${section}' saved to settings.json!`, 'success');
  } catch (err) {
    showSnack(`Failed to save section: ${err.message}`, 'error');
  }
}

function toggleRow(featureKey, label, desc, currentValue) {
  const id = `toggle-${featureKey}`;
  return `
    <div class="toggle-row">
      <div class="toggle-info">
        <div class="toggle-label">${label}</div>
        <div class="toggle-desc">${desc}</div>
      </div>
      <div class="md-switch ${currentValue ? 'on' : ''}" id="${id}"
           onclick="toggleFeature('${featureKey}', '${id}')"></div>
    </div>
  `;
}

function formToggleRow(name, label, desc, isChecked) {
  return `
    <div class="toggle-row">
      <div class="toggle-info">
        <div class="toggle-label">${label}</div>
        <div class="toggle-desc">${desc}</div>
      </div>
      <input type="checkbox" name="${name}" class="md-switch" ${isChecked ? 'checked' : ''} />
    </div>
  `;
}

async function toggleFeature(key, elemId) {
  const el = document.getElementById(elemId);
  if (!el) return;
  const newVal = !el.classList.contains('on');
  el.classList.toggle('on', newVal);
  try {
    await apiFetch(API.configFeature, {
      method: 'PATCH',
      body: JSON.stringify({ feature: key, value: newVal }),
    });
    showSnack(`${key}: ${newVal ? 'ON' : 'OFF'}`, 'success');
  } catch (err) {
    el.classList.toggle('on', !newVal);
    showSnack('Failed: ' + err.message, 'error');
  }
}

// ─── Chart.js helpers ─────────────────────────────────────────────────────────
function renderLineChart(canvasId, labels, data, label, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  if (state.charts[canvasId]) state.charts[canvasId].destroy();

  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 240);
  gradient.addColorStop(0, color + '66');
  gradient.addColorStop(1, color + '00');

  state.charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: gradient,
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: color,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'var(--md-surface-container-highest)',
          titleColor: 'var(--md-on-surface)',
          bodyColor: 'var(--md-on-surface-variant)',
          borderColor: 'var(--md-outline-variant)',
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 } },
          beginAtZero: true,
        },
      },
    },
  });
}

function renderDoughnutChart(canvasId, labels, data, colors) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  if (state.charts[canvasId]) state.charts[canvasId].destroy();

  state.charts[canvasId] = new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderColor: 'var(--md-surface-container)',
        borderWidth: 2,
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: 'rgba(255,255,255,0.6)',
            font: { size: 11 },
            boxWidth: 10,
            padding: 8,
          },
        },
        tooltip: {
          backgroundColor: 'var(--md-surface-container-highest)',
          titleColor: 'var(--md-on-surface)',
          bodyColor: 'var(--md-on-surface-variant)',
        },
      },
    },
  });
}

// ─── Error / empty states ──────────────────────────────────────────────────────
function errorState(msg) {
  return `
    <div class="empty-state" style="padding:64px 24px">
      <div class="empty-state-icon">⚠️</div>
      <div class="empty-state-text">Failed to load data</div>
      <div class="empty-state-sub text-muted">${escapeHtml(msg)}</div>
    </div>
  `;
}

// ─── Theme ────────────────────────────────────────────────────────────────────
function toggleTheme() {
  const isLight = document.documentElement.dataset.theme === 'light';
  document.documentElement.dataset.theme = isLight ? '' : 'light';
  const btn = document.querySelector('.theme-btn');
  if (btn) btn.innerHTML = isLight ? '☀️' : '🌙';
  localStorage.setItem('theme', isLight ? 'dark' : 'light');
}

function loadTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  if (saved === 'light') document.documentElement.dataset.theme = 'light';
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
window.handleVerifyOtp   = handleVerifyOtp;
window.goBackToStep1     = goBackToStep1;
window.handleLogout      = handleLogout;
window.navigate          = navigate;
window.toggleFeature     = toggleFeature;
window.filterLog         = filterLog;
window.confirmRestart    = confirmRestart;
window.saveConfigSection = saveConfigSection;
window.otpValue        = '';
Object.defineProperty(window, 'otpValue', {
  get: () => otpValue,
  set: v => { otpValue = v; },
});

async function init() {
  loadTheme();
  renderLogin();

  const authed = await checkAuth();
  if (authed) {
    state.isLoggedIn = true;
    renderDashboard();
  }
}

document.addEventListener('DOMContentLoaded', init);
