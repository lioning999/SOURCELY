/** 管理后台 API 调用 — 统一入口 */
const API_BASE = (() => {
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return location.protocol + '//' + location.hostname;
})();

function getToken() {
  const t = sessionStorage.getItem('admin_token');
  if (!t) { window.location.href = 'login.html'; throw new Error('未登录'); }
  return t;
}

function apiHeaders() {
  return {
    'Authorization': 'Bearer ' + getToken(),
    'Content-Type': 'application/json'
  };
}

async function handleResponse(resp) {
  if (resp.status === 401) {
    sessionStorage.removeItem('admin_token');
    window.location.href = 'login.html';
    throw new Error('登录已过期');
  }
  const data = await resp.json();
  if (data.code !== 200) throw new Error(data.message || '请求失败');
  return data;
}

// ── 认证 ──

export async function adminLogin(password) {
  const resp = await fetch(API_BASE + '/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  });
  return resp.json();
}

// ── Snapshots ──

export async function fetchSnapshots(page, pageSize, search) {
  const params = new URLSearchParams({ page, page_size: pageSize, search });
  const resp = await fetch(API_BASE + '/admin/snapshots?' + params, { headers: apiHeaders() });
  return handleResponse(resp);
}

export async function fetchSnapshotDetail(id) {
  const resp = await fetch(API_BASE + '/admin/snapshots/' + id, { headers: apiHeaders() });
  return handleResponse(resp);
}

export async function batchDeleteSnapshots(ids) {
  const resp = await fetch(API_BASE + '/admin/snapshots/batch-delete', {
    method: 'POST', headers: apiHeaders(), body: JSON.stringify({ ids })
  });
  return handleResponse(resp);
}

// ── Members ──

export async function fetchMembers(page, pageSize, search) {
  const params = new URLSearchParams({ page, page_size: pageSize, search });
  const resp = await fetch(API_BASE + '/admin/members?' + params, { headers: apiHeaders() });
  return handleResponse(resp);
}

export async function batchDeleteMembers(openids) {
  const resp = await fetch(API_BASE + '/admin/members/batch-delete', {
    method: 'POST', headers: apiHeaders(), body: JSON.stringify({ openids })
  });
  return handleResponse(resp);
}
