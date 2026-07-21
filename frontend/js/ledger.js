/* ledger.js — Threat Ledger with pagination, filtering, and CSV export */

let ledgerPage     = 1;
let ledgerPageSize = 20;
let ledgerFilter   = null;
let ledgerTotal    = 0;
let ledgerTotalPages = 1;
let ledgerCache    = [];

// ── Controls ──────────────────────────────────────────────────
document.getElementById('pageSizeSelect').addEventListener('change', e => {
  ledgerPageSize = parseInt(e.target.value);
  loadLedger(1);
});

document.querySelectorAll('.filter-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    ledgerFilter = btn.dataset.filter === 'all' ? null : btn.dataset.filter;
    loadLedger(1);
  });
});

document.getElementById('prevPage').addEventListener('click', () => {
  if (ledgerPage > 1) loadLedger(ledgerPage - 1);
});
document.getElementById('nextPage').addEventListener('click', () => {
  if (ledgerPage < ledgerTotalPages) loadLedger(ledgerPage + 1);
});

document.getElementById('exportBtn').addEventListener('click', exportCSV);

// ── Clear Ledger ──────────────────────────────────────────────
document.getElementById('clearLedgerBtn').addEventListener('click', async () => {
  if (confirm("Are you sure you want to completely clear the Threat Ledger? This cannot be undone.")) {
    try {
      const res = await fetch(`${API_BASE}/api/history`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Reload the ledger
      loadLedger(1);
    } catch (err) {
      console.error("Failed to clear ledger:", err);
      alert("Error clearing ledger. Is the server running?");
    }
  }
});

// ── Load Ledger ───────────────────────────────────────────────
async function loadLedger(page = 1) {
  ledgerPage = page;
  const body = document.getElementById('ledgerBody');
  body.innerHTML = '<tr><td colspan="7" class="empty-state">Loading...</td></tr>';

  try {
    let url = `${API_BASE}/api/history?page=${page}&page_size=${ledgerPageSize}`;
    if (ledgerFilter) url += `&verdict=${ledgerFilter}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    ledgerTotal      = data.total;
    ledgerTotalPages = data.total_pages;
    ledgerCache      = data.items;

    renderLedger(data.items);
    updatePagination();
  } catch (err) {
    body.innerHTML = `<tr><td colspan="7" class="empty-state">Failed to load data. Is the API running?</td></tr>`;
    showToast('Could not load ledger.', 'error');
  }
}

// ── Render Table ──────────────────────────────────────────────
function renderLedger(items) {
  const body = document.getElementById('ledgerBody');
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-state">No records found.</td></tr>';
    return;
  }

  body.innerHTML = items.map(item => `
    <tr>
      <td style="font-family:var(--font-mono);color:var(--text-muted);font-size:12px">#${item.id}</td>
      <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--font-mono);font-size:12px" title="${escapeHtml(item.prompt_preview)}">${escapeHtml(item.prompt_preview)}</td>
      <td>
        <span class="tag ${item.verdict === 'SAFE' ? 'tag-safe' : 'tag-blocked'}">
          ${item.verdict}
        </span>
      </td>
      <td>${getCategoryTag(item.category)}</td>
      <td style="font-family:var(--font-mono)">${item.confidence}%</td>
      <td>${getRiskBadge(item.risk_score)}</td>
      <td style="font-size:12px;color:var(--text-muted);white-space:nowrap">${formatDateTime(item.timestamp)}</td>
    </tr>
  `).join('');
}

// ── Pagination ────────────────────────────────────────────────
function updatePagination() {
  document.getElementById('pageInfo').textContent =
    `Page ${ledgerPage} of ${ledgerTotalPages}  (${ledgerTotal} records)`;
  document.getElementById('prevPage').disabled = ledgerPage <= 1;
  document.getElementById('nextPage').disabled = ledgerPage >= ledgerTotalPages;
}

// ── CSV Export ────────────────────────────────────────────────
function exportCSV() {
  if (!ledgerCache.length) { showToast('No data to export.', 'error'); return; }
  const headers = ['ID','Prompt Preview','Verdict','Category','Confidence','Risk Score','Timestamp'];
  const rows = ledgerCache.map(r =>
    [r.id, `"${r.prompt_preview.replace(/"/g,'""')}"`, r.verdict, r.category, r.confidence, r.risk_score, r.timestamp].join(',')
  );
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `ai_firewall_log_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  showToast('CSV exported successfully.', 'success');
}

// ── Helpers ───────────────────────────────────────────────────
function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
