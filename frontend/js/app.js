/* app.js — SPA routing, API config, global utilities */

const API_BASE = 'http://localhost:8000';

// ── View Router ──────────────────────────────────────────────
function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const view = document.getElementById(`view-${name}`);
  const nav  = document.getElementById(`nav-${name}`);
  if (view) view.classList.add('active');
  if (nav)  nav.classList.add('active');

  if (name === 'dashboard') loadDashboard();
  if (name === 'ledger')    loadLedger(1);
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

// ── Background Particles ─────────────────────────────────────
function initParticles() {
  const container = document.getElementById('bgParticles');
  for (let i = 0; i < 25; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 3 + 1;
    const colors = ['#4d9fff', '#00ff88', '#cc00ff', '#ff3366'];
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random()*100}%;
      top:${Math.random()*100}%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-duration:${8 + Math.random()*12}s;
      animation-delay:${Math.random()*10}s;
    `;
    container.appendChild(p);
  }
}
initParticles();

// ── API Health Check ─────────────────────────────────────────
async function checkHealth() {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      dot.className = 'status-dot online';
      text.textContent = 'API Online';
    } else throw new Error();
  } catch {
    dot.className = 'status-dot offline';
    text.textContent = 'API Offline';
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// ── Toast ────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icons = { success: '✓', error: '✗', info: 'ℹ' };
  el.innerHTML = `<span style="font-weight:700;color:var(--${type === 'success' ? 'safe' : type === 'error' ? 'danger' : 'accent'})">${icons[type] || '●'}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

// ── Helpers ──────────────────────────────────────────────────
function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  return isNaN(d) ? ts : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts.replace(' ', 'T'));
  return isNaN(d) ? ts : d.toLocaleString();
}

function getCategoryTag(cat) {
  const map = {
    SAFE:               'tag-safe',
    JAILBREAK:          'tag-jailbreak',
    ROLE_PLAY_BYPASS:   'tag-roleplay',
    PAYLOAD_INJECTION:  'tag-payload',
    SOCIAL_ENGINEERING: 'tag-social',
    DATA_EXFILTRATION:  'tag-exfil',
  };
  return `<span class="tag ${map[cat] || ''}">${cat?.replace(/_/g,' ') || '—'}</span>`;
}


function getRiskBadge(score) {
  let cls = score >= 70 ? 'risk-high' : score >= 40 ? 'risk-med' : 'risk-low';
  return `<span class="risk-badge ${cls}">${score}</span>`;
}

function getRiskColor(score) {
  if (score >= 70) return 'var(--danger)';
  if (score >= 40) return 'var(--warning)';
  return 'var(--safe)';
}

// Expose globals
window.API_BASE      = API_BASE;
window.showToast     = showToast;
window.formatTime    = formatTime;
window.formatDateTime= formatDateTime;
window.getCategoryTag= getCategoryTag;
window.getRiskBadge  = getRiskBadge;
window.getRiskColor  = getRiskColor;
window.switchView    = switchView;
