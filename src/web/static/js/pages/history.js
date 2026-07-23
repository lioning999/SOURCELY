// ===== 历史记录页 =====
// 登录用户查看过往分析记录（只读 DB，不调 Apify）

var historyList = document.getElementById('historyList');
var historyEmpty = document.getElementById('historyEmpty');
var loginPrompt = document.getElementById('loginPrompt');
var pageHint = document.getElementById('pageHint');

// ===== 加载历史 =====
var user = checkAuth();
if (!user) {
  loginPrompt.style.display = 'block';
  pageHint.textContent = '登录后可查看历史分析记录';
} else {
  loadHistory();
}

function loadHistory() {
  var token = getToken();
  fetch('/api/history', {
    headers: { 'Authorization': 'Bearer ' + token }
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 401) {
        loginPrompt.style.display = 'block';
        pageHint.textContent = '登录已过期，请重新登录';
        return;
      }

      var items = (data.data && data.data.items) || [];
      if (!items.length) {
        historyEmpty.style.display = 'block';
        return;
      }

      historyList.style.display = 'block';
      pageHint.textContent = '共 ' + items.length + ' 条记录';
      renderItems(items);
    })
    .catch(function(err) {
      console.warn('History load failed:', err);
      pageHint.textContent = '加载失败，请刷新页面重试';
    });
}

function renderItems(items) {
  var html = '';
  items.forEach(function(item) {
    var price = '';
    if (item.price_min != null) {
      price = '¥' + item.price_min;
      if (item.price_max && item.price_max !== item.price_min) {
        price += ' – ¥' + item.price_max;
      }
    }

    var timeAgo = formatTimeAgo(item.created_at);
    var imgHtml = item.image_url
      ? '<img class="hi-thumb" src="' + escapeAttr(item.image_url) + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">'
      : '<div class="hi-thumb hi-thumb-empty"></div>';

    html +=
      '<a href="report.html?offerId=' + escapeAttr(item.offer_id) + '" class="history-item">' +
        imgHtml +
        '<div class="hi-body">' +
          '<div class="hi-title">' + escapeHTML(item.title || '(无标题)') + '</div>' +
          '<div class="hi-meta">' +
            '<span class="hi-price">' + (price || '—') + '</span>' +
            '<span class="hi-time">' + timeAgo + '</span>' +
          '</div>' +
        '</div>' +
      '</a>';
  });
  historyList.innerHTML = html;
}

// ===== 工具函数 =====

function formatTimeAgo(dateStr) {
  if (!dateStr) return '';
  var now = Date.now();
  var then = new Date(dateStr.replace(' ', 'T') + (dateStr.indexOf('+') === -1 ? 'Z' : '')).getTime();
  if (isNaN(then)) return dateStr;
  var diff = Math.floor((now - then) / 1000);
  if (diff < 60) return '刚刚';
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
  if (diff < 604800) return Math.floor(diff / 86400) + ' 天前';
  return dateStr.slice(0, 10);
}

function escapeHTML(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
