async function searchLoads(params) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/shipments/search?${qs}`, {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Search failed');
  }
  return res.json();
}

function normalizePhoneDisplay(phone) {
  if (phone === undefined || phone === null) return '';
  const digits = String(phone).replace(/\D/g, '');
  return digits ? `+${digits}` : '';
}

function serializeForm(form) {
  const data = new FormData(form);
  const params = {};
  for (const [k, v] of data.entries()) {
    if (typeof v === 'string') {
      const trimmed = v.trim();
      if (trimmed !== '') params[k] = trimmed;
    } else if (v !== '') {
      params[k] = v;
    }
  }
  return params;
}

function renderRows(rows) {
  const tbody = document.querySelector('#results-table tbody');
  tbody.innerHTML = '';
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.tenant_id || ''}</td>
      <td>${r.shipment_id || ''}</td>
      <td>${r.load_id || ''}</td>
      <td>${r.job_id || ''}</td>
      <td>${r.fleet_name || ''}</td>
      <td>${normalizePhoneDisplay(r.fleet_phone)}</td>
      <td>${r.customer_name || ''}</td>
      <td>${r.carrier_id || ''}</td>
      <td>${formatDateTime(r.updated_at)}</td>
      <td>
        <button class="back-button" data-action="use-load" data-job-id="${r.job_id || ''}" ${r.job_id ? '' : 'disabled'} title="Use this load">Use</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function renderPagination(pagination, params) {
  const el = document.getElementById('pagination');
  const { limit, offset, count } = pagination || { limit: 10, offset: 0, count: 0 };
  el.innerHTML = '';
  const totalPages = limit > 0 ? Math.ceil(count / limit) : 1;
  const currentPage = limit > 0 ? Math.floor(offset / limit) + 1 : 1;

  // Hide pagination when not needed
  if (!count || count <= limit) {
    el.style.display = 'none';
    return;
  }
  el.style.display = '';

  const container = document.createElement('div');
  container.className = 'pagination';

  const prevOffset = Math.max(offset - limit, 0);
  const nextOffset = offset + limit;

  const prevBtn = document.createElement('button');
  prevBtn.textContent = 'Prev';
  prevBtn.disabled = currentPage <= 1;
  prevBtn.onclick = () => runSearch({ ...params, offset: prevOffset });

  const nextBtn = document.createElement('button');
  nextBtn.textContent = 'Next';
  nextBtn.disabled = currentPage >= totalPages;
  nextBtn.onclick = () => runSearch({ ...params, offset: nextOffset });

  container.append(prevBtn, nextBtn);
  el.append(container);
}

function extractRows(resp) {
  if (Array.isArray(resp?.data)) return resp.data;
  if (Array.isArray(resp?.data?.rows)) return resp.data.rows;
  if (Array.isArray(resp?.rows)) return resp.rows;
  return [];
}

function extractPagination(resp, rows) {
  const p = resp?.pagination || {};
  return {
    limit: typeof p.limit === 'number' ? p.limit : 10,
    offset: typeof p.offset === 'number' ? p.offset : 0,
    count: typeof p.count === 'number' ? p.count : (Array.isArray(rows) ? rows.length : 0)
  };
}

async function runSearch(params) {
  const errorEl = document.getElementById('error');
  errorEl.textContent = '';
  const overlay = document.getElementById('loads-loading');
  overlay && (overlay.style.display = 'flex');
  try {
    const resp = await searchLoads(params);
    console.debug('Search response', resp);
    const rows = extractRows(resp);
    const pagination = extractPagination(resp, rows);
    renderRows(rows);
    renderPagination(pagination, params);
    updateSummary(pagination);
  } catch (e) {
    console.error('Search failed', e);
    errorEl.textContent = e.message || 'Search failed';
    renderRows([]);
    renderPagination({ limit: 10, offset: 0, count: 0 }, params);
    updateSummary({ limit: 10, offset: 0, count: 0 });
  }
  overlay && (overlay.style.display = 'none');
}

function updateSummary(pagination) {
  const { limit = 10, offset = 0, count = 0 } = pagination || {};
  const end = Math.min(offset + limit, count);
  const summary = document.getElementById('results-summary');
  if (summary) summary.textContent = count ? `Showing ${offset + 1}-${end} of ${count}` : 'No results';
}

document.getElementById('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const params = collectParams();
  params.limit = params.limit || 10;
  params.offset = params.offset || 0;
  await runSearch(params);
});

// Quick search controls
document.getElementById('quick-search-button').addEventListener('click', () => {
  const params = collectParams();
  params.limit = params.limit || 10;
  params.offset = 0;
  runSearch(params);
});

document.getElementById('quick-value').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    document.getElementById('quick-search-button').click();
  }
});

document.getElementById('clear-filters').addEventListener('click', () => {
  // Clear quick
  document.getElementById('quick-value').value = '';
  // Clear advanced form
  const form = document.getElementById('search-form');
  form.reset();
  document.getElementById('error').textContent = '';
  // Do not clear current results; only reset filters
});

(() => {
  const btn = document.getElementById('toggle-advanced');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const adv = document.querySelector('.advanced-filters');
    if (!adv) return;
    const computed = window.getComputedStyle(adv);
    const isHidden = computed.display === 'none';
    adv.style.display = isHidden ? 'grid' : 'none';
  });
})();

function collectParams() {
  const field = document.getElementById('quick-field').value;
  const value = document.getElementById('quick-value').value.trim();
  const formParams = serializeForm(document.getElementById('search-form'));
  if (value) formParams[field] = value;
  // Sort direction from quick selector
  const sortSel = document.getElementById('sort-select');
  if (sortSel && sortSel.value) {
    formParams.sort_dir = sortSel.value;
  }
  // Normalize fleet phone for querying: use digits-only to be robust
  if (typeof formParams.fleet_phone === 'string') {
    const trimmed = formParams.fleet_phone.trim();
    if (trimmed) {
      const digitsOnly = trimmed.replace(/[^0-9]/g, '');
      formParams.fleet_phone = digitsOnly;
    }
  }
  return formParams;
}

// Default initial fetch of all loads
window.addEventListener('DOMContentLoaded', () => {
  const sortSel = document.getElementById('sort-select');
  const sort_dir = sortSel ? sortSel.value : 'desc';
  runSearch({ limit: 10, offset: 0, sort_dir });

  // Delegate click for Use buttons
  const table = document.getElementById('results-table');
  table.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action="use-load"]');
    if (!btn) return;
    const jobId = btn.getAttribute('data-job-id');
    if (!jobId) return;
    openFormChoiceModal(jobId);
  });
});

function formatDateTime(value) {
  if (!value) return '';
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  } catch (_) {
    return String(value);
  }
}

// Modal to choose which form to open
let pendingJobId = null;

function openFormChoiceModal(jobId) {
  pendingJobId = jobId;
  const overlay = document.getElementById('form-choice-overlay');
  const modal = document.getElementById('form-choice-modal');
  if (!overlay || !modal) {
    // Fallback: default to opening default form
    window.location.href = `/forms/?active_tab=default&job_id=${encodeURIComponent(jobId)}`;
    return;
  }
  overlay.style.display = 'flex';
}

function closeFormChoiceModal() {
  const overlay = document.getElementById('form-choice-overlay');
  if (overlay) overlay.style.display = 'none';
}

function confirmFormChoice() {
  const select = document.getElementById('form-choice-select');
  const tab = (select && select.value) ? select.value : 'default';
  if (!pendingJobId) return;
  const url = `/forms/?active_tab=${encodeURIComponent(tab)}&job_id=${encodeURIComponent(pendingJobId)}`;
  pendingJobId = null;
  closeFormChoiceModal();
  window.location.href = url;
}

// Wire modal buttons
(() => {
  const cancelBtn = document.getElementById('form-choice-cancel');
  const continueBtn = document.getElementById('form-choice-continue');
  const overlay = document.getElementById('form-choice-overlay');
  cancelBtn && cancelBtn.addEventListener('click', closeFormChoiceModal);
  continueBtn && continueBtn.addEventListener('click', confirmFormChoice);
  overlay && overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeFormChoiceModal();
  });
})();


