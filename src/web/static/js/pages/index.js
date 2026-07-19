// ============================================================
// Sourcely — Landing page interactions
// ============================================================

// ----- CTA button templates (zh has no JSON, inline fallback) -----
var CTA_TEMPLATES = {
  zh: '拿样品 · 付 {price} 定金',
};

// ----- API base URL (auto-detect for file:// vs server) -----
var API_BASE = (window.location.protocol === 'file:')
  ? 'http://localhost:8000'
  : '';

// ----- Current product data (from API) -----
var currentProduct = null;

// ----- Sub-tab switching (产品 / 工厂 / 拿样) -----
function bindSubTabs() {
  var subBar = document.querySelector('.tabs');
  if (!subBar) return;
  subBar.addEventListener('click', function(e) {
    var tab = e.target.closest('.tab');
    if (!tab) return;
    var target = tab.dataset.tab;
    subBar.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    tab.classList.add('active');
    var card = tab.closest('.card');
    card.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
    var panel = card.querySelector('#tab-' + target);
    if (panel) panel.classList.add('active');
    if (target === 'sample') updateCost();
  });
}

// ----- Search — real API call -----
function bindSearch() {
  var searchBtn = document.getElementById('searchBtn');
  var searchInput = document.getElementById('searchInput');
  if (!searchBtn || !searchInput) return;

  searchBtn.addEventListener('click', function() {
    var val = searchInput.value.trim();
    if (!val) {
      showSearchError(I18N.t('search.invalid') || '请输入有效的 1688 链接');
      return;
    }
    if (!/1688\.com\/offer\/\d{8,}/.test(val)) {
      showSearchError('请粘贴完整的 1688 商品链接（detail.1688.com/offer/...）');
      return;
    }

    var analyzingMsg = I18N.t('search.analyzing') || '分析中...';
    searchBtn.textContent = analyzingMsg;
    searchBtn.disabled = true;

    fetch(API_BASE + '/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: val }),
    })
    .then(function(r) { return r.json(); })
    .then(function(json) {
      if (json.code === 200) {
        currentProduct = json.data;
        fillProductCard(json.data);
        // Scroll to card
        var card = document.getElementById('productCard');
        if (card) {
          card.scrollIntoView({ behavior: 'smooth' });
          flashCard(card);
        }
        // Reset to product tab
        resetTabs();
        // Update cost with real prices
        updateCost();
      } else if (json.code === 403 || json.code === 429) {
        showSearchError('今日免费次数已用完。WhatsApp +86 138-xxxx-xxxx 解锁不限次数。');
      } else {
        showSearchError(json.message || '分析失败，请重试');
      }
    })
    .catch(function(err) {
      console.warn('API call failed:', err);
      showSearchError('服务连接失败。请确认后端已启动（http://localhost:8000）');
    })
    .finally(function() {
      var doneMsg = I18N.t('search.button') || '分析';
      searchBtn.textContent = doneMsg;
      searchBtn.disabled = false;
    });
  });
}

function showSearchError(msg) {
  var input = document.getElementById('searchInput');
  if (!input) return;
  input.style.borderColor = 'var(--bad)';
  input.value = '';
  input.placeholder = msg;
  setTimeout(function() {
    input.style.borderColor = '';
    var orig = I18N.t('search.placeholder') || '粘贴 1688 商品链接...';
    input.placeholder = orig;
  }, 2500);
}

function flashCard(card) {
  card.style.boxShadow = '0 0 0 3px rgba(30,58,95,.14)';
  setTimeout(function() { card.style.boxShadow = ''; }, 800);
}

function resetTabs() {
  var tabs = document.querySelectorAll('.tab');
  var panels = document.querySelectorAll('.panel');
  tabs.forEach(function(t) { t.classList.remove('active'); });
  panels.forEach(function(p) { p.classList.remove('active'); });
  var firstTab = document.querySelector('.tab[data-tab="product"]');
  var firstPanel = document.getElementById('tab-product');
  if (firstTab) firstTab.classList.add('active');
  if (firstPanel) firstPanel.classList.add('active');
}

// ----- Fill product card with API data -----
function fillProductCard(data) {
  console.log('fillProductCard', data);

  // === Product Header ===
  var imgEl = document.querySelector('.prod-img');
  if (imgEl && data.image) imgEl.src = data.image;

  var titleEl = document.querySelector('.prod-title');
  if (titleEl && data.title) {
    titleEl.textContent = data.title;
    titleEl.removeAttribute('data-i18n');
  }

  // Spec tags
  var specsEl = document.getElementById('prodSpecs');
  if (specsEl && data.specs) {
    var specsHtml = '';
    (data.specs || []).forEach(function(s) {
      specsHtml += '<span class="spec-tag">' + s.name + ': ' + s.value + '</span>';
    });
    specsEl.innerHTML = specsHtml || '<span class="spec-tag">暂无规格</span>';
  }

  // Prices
  var priceSpan = document.querySelector('.prod-price span[data-price-usd]');
  if (priceSpan && data.priceLow != null) {
    priceSpan.textContent = I18N.formatPriceRange(data.priceLow, data.priceHigh || data.priceLow);
    priceSpan.setAttribute('data-price-usd', data.priceLow);
    if (data.priceHigh) priceSpan.setAttribute('data-price-high', data.priceHigh);
  }

  var rmbEl = document.querySelector('.prod-rmb');
  if (rmbEl && data.priceCNY) {
    var lo = data.priceCNY.low || '', hi = data.priceCNY.high || lo;
    rmbEl.innerHTML = '<span>原价</span> ¥' + lo + (hi !== lo ? ' – ¥' + hi : '');
    rmbEl.removeAttribute('data-i18n');
  }

  // Unit
  var unitEl = document.querySelector('.prod-price em');
  if (unitEl && data.unit) unitEl.textContent = '/ ' + data.unit;

  // === Tab Product (4 rows) ===
  var pVerdict = document.querySelector('#prodVerdict span:last-child');
  if (pVerdict) {
    var ok_7d = data.return7day === 'OK', ok_sales = data.sales30d !== 'N/A';
    var ok_moq = data.moq != null && data.moq <= 10;
    var allOk = ok_7d && ok_sales && ok_moq;
    pVerdict.textContent = allOk
      ? '产品可卖 — ' + [ok_7d?'支持7天无理由':'', ok_sales?'持续动销':'', ok_moq?'起批门槛低':''].filter(Boolean).join('，')
      : '产品需谨慎 — 部分指标不达标';
    var vBar = document.getElementById('prodVerdict');
    if (vBar) { vBar.classList.remove('g','y'); vBar.classList.add(allOk ? 'g' : 'y'); }
    pVerdict.removeAttribute('data-i18n');
  }

  // Row 0: 7天无理由
  setRow('tab-product', 0, data.return7day,
    '7 天无理由退货',
    data.return7day === 'OK' ? '支持' : '不支持',
    data.return7day === 'OK' ? '支持退货，降低试错成本。质量问题可退换。' : '不支持7天无理由，下单前需确认品质');

  // Row 1: 近30天成交 + 想买人数
  var hasSales = data.sales30d !== 'N/A';
  var salesVal = (data.sales30d || 'N/A') + (data.sales30dAmount !== 'N/A' ? ' · ' + data.sales30dAmount : '');
  var wantBuy = data.wantBuyCount ? data.wantBuyCount + ' 人想买' : '';
  var salesValue = salesVal + (wantBuy ? '，' + wantBuy : '');
  var salesExplain = hasSales
    ? (wantBuy ? '持续动销，' + wantBuy + '。市场验证通过。' : '持续动销，市场验证通过。')
    : '暂无成交数据，建议观望';
  setRow('tab-product', 1, hasSales ? 'OK' : 'NO',
    '近 30 天成交', salesValue, salesExplain);

  // Row 2: 起批条件 + 库存
  var moqOk = data.moq != null && data.moq <= 10;
  var moqExplain = moqOk ? '起批门槛低，可低成本测款。' : '起批量较高(' + (data.moq||'?') + '件)，建议先拿样品测试';
  // Stock hint
  var stockHint = '';
  if (data.isOutOfStock) {
    stockHint = ' ⚠ 该商品可能已停产';
  } else if (data.stock != null && data.stock > 10000) {
    stockHint = ' · 库存充足';
  } else if (data.stock != null && data.stock > 0) {
    stockHint = ' · 库存 ' + data.stock + ' 件';
  }
  moqExplain += stockHint;
  setRow('tab-product', 2, moqOk ? 'OK' : 'NO',
    '起批条件',
    data.moq != null ? data.moq + ' 件起批' : 'N/A',
    moqExplain);
  var moqLink = document.querySelector('#tab-product .row-explain a');
  if (moqLink && data.itemUrl) moqLink.href = data.itemUrl;
  // Also update #stockHint
  var stockEl = document.getElementById('stockHint');
  if (stockEl) stockEl.textContent = stockHint;

  // Row 3: 服务保障（translated services）
  var svcTags = data.serviceTags || [];
  var hasSvc = svcTags.length > 0;
  var svcValue = hasSvc ? svcTags.map(function(t) { return t.desc; }).join(' · ') : '无特殊保障';
  var svcEl = document.getElementById('serviceValue');
  if (svcEl) {
    svcEl.textContent = svcValue;
    svcEl.removeAttribute('data-i18n');
  }
  setRowTag('tab-product', 3, hasSvc ? 'OK' : 'NO');

  // === Tab Images ===
  var productGallery = document.getElementById('productGallery');
  if (productGallery && data.images) {
    var galleryHtml = '';
    (data.images || []).forEach(function(url) {
      galleryHtml += '<img src="' + url + '" loading="lazy" alt="商品图">';
    });
    productGallery.innerHTML = galleryHtml;
  }

  // === Tab Factory (4 rows) ===
  var fVerdict = document.querySelector('#tab-factory .verdict span:last-child');
  if (fVerdict) {
    var vTags = data.verifiedTags || [];
    var isGood = data.verified === 'OK' && data.businessType === '生产厂家';
    fVerdict.textContent = isGood
      ? '工厂可合作 — ' + vTags.slice(0, 3).join('、') + '，源头工厂直营'
      : '工厂需进一步确认 — 部分指标不达标';
    var fvBar = document.querySelector('#tab-factory .verdict');
    if (fvBar) { fvBar.classList.remove('g','y'); fvBar.classList.add(isGood ? 'g' : 'y'); }
    fVerdict.removeAttribute('data-i18n');
  }

  // Cert section
  var certEl = document.querySelector('#tab-factory .sec');
  if (certEl && data.supplierName) {
    certEl.textContent = '工厂认证 · ' + data.supplierName;
    certEl.removeAttribute('data-i18n');
  }

  // Row 0: 1688认证商家（cert-list）
  var CERT_DESC = {
    '超级工厂': '1688 官方认证头部大厂，年销售额超千万',
    '诚信通': '1688 基础企业认证，经营 2 年以上',
    'TP验厂': '第三方机构实地验厂通过',
    '厂货通': '1688 工厂直供频道认证',
    '实力工厂': '1688 认证的实力厂家',
    '品牌认证': '品牌方授权认证',
    '生产厂家': '企业工商注册为生产型',
    '第三方认证': '独立第三方机构验厂通过',
  };
  var vTagList = data.verifiedTags || [];
  var certHtml = '';
  if (data.verified === 'OK' && vTagList.length > 0) {
    certHtml = '<div class="cert-list">';
    vTagList.forEach(function(t) {
      var desc = CERT_DESC[t] || '';
      certHtml += '<div class="cert-item">✓ <span class="cert-name">' + t + '</span>' + (desc ? ' <span class="cert-desc">— ' + desc + '</span>' : '') + '</div>';
    });
    certHtml += '</div>';
  } else {
    certHtml = '<div class="cert-item" style="color:var(--ink-3);">⚠️ 仅基础认证</div>';
  }
  var certEl = document.getElementById('verifiedBadges');
  if (certEl) {
    certEl.innerHTML = certHtml;
    certEl.removeAttribute('data-i18n');
  }
  setRowTag('tab-factory', 0, data.verified);

  // Row 1: 经营模式（highlight）
  var isFactory = data.businessType === '生产厂家';
  var bizEl = document.getElementById('businessBadge');
  if (bizEl) {
    if (isFactory) {
      bizEl.innerHTML = '<span class="badge badge-factory">🏭 生产厂家</span>';
    } else if (data.businessType) {
      bizEl.innerHTML = '<span class="badge badge-yellow">' + data.businessType + '</span>';
    } else {
      bizEl.textContent = 'N/A';
    }
    bizEl.removeAttribute('data-i18n');
  }
  setRowTag('tab-factory', 1, isFactory ? 'OK' : 'NO');

  // Row 2: 发货地
  var location = data.shippingLocation || '';
  var cluster = data.industryCluster || '';
  var hasLoc = !!location;
  setRow('tab-factory', 2, hasLoc ? 'OK' : 'NO',
    '发货地',
    location || 'N/A',
    location ? (cluster || '发货地：' + location) : '暂无发货地信息');

  // Row 3: 发货速度
  setRow('tab-factory', 3, data.shippingSpeed,
    '发货速度',
    data.shippingSpeedLabel || 'N/A',
    data.shippingSpeed === 'OK' ? '发货速度正常，交期有保障。' : '发货偏慢。下单时锁定交期，预留缓冲时间。');

  // === Tab Sample ===
  var sVerdict = document.getElementById('sampleVerdict');
  if (sVerdict) sVerdict.removeAttribute('data-i18n');

  // Show card
  var card = document.getElementById('productCard');
  if (card) card.style.display = '';
}

// ----- Single row update (label + value + explain + tag) -----
function setRow(tabId, rowIndex, status, label, value, explain) {
  var panel = document.getElementById(tabId);
  if (!panel) return;
  var rows = panel.querySelectorAll('.row');
  if (rowIndex >= rows.length) return;
  var row = rows[rowIndex];

  // Tag
  var tag = row.querySelector('.row-tag');
  if (tag) {
    tag.className = 'row-tag ' + (status === 'OK' ? 'g' : 'r');
    tag.textContent = status === 'OK' ? 'OK' : 'NO';
  }
  // Label
  var labelEl = row.querySelector('.row-label');
  if (labelEl && label) labelEl.textContent = label;
  // Value
  var valueEl = row.querySelector('.row-value');
  if (valueEl && value) valueEl.textContent = value;
  // Explain
  var explainEl = row.querySelector('.row-explain');
  if (explainEl && explain) {
    // Preserve link if present
    var link = explainEl.querySelector('a');
    explainEl.textContent = explain;
    if (link) explainEl.appendChild(link);
  }
}

// ----- Single row update: tag only (for rows with custom value rendering) -----
function setRowTag(tabId, rowIndex, status) {
  var panel = document.getElementById(tabId);
  if (!panel) return;
  var rows = panel.querySelectorAll('.row');
  if (rowIndex >= rows.length) return;
  var row = rows[rowIndex];
  var tag = row.querySelector('.row-tag');
  if (tag) {
    tag.className = 'row-tag ' + (status === 'OK' ? 'g' : 'r');
    tag.textContent = status === 'OK' ? 'OK' : 'NO';
  }
}

// ----- Language switcher -----
function bindLangSwitcher() {
  var sw = document.getElementById('langSwitcher');
  if (!sw) return;
  sw.addEventListener('change', function() {
    I18N.switchTo(sw.value).then(function() {
      // Re-fill with current data if exists
      if (currentProduct) fillProductCard(currentProduct);
      updateCost();
    });
  });
}

// ----- Cost calculator -----
var shipRates = { TH: 4.5, VN: 3.8, ID: 5.2, MY: 3.5, PH: 5.8 };

function getUnitPrice(qty) {
  // Use API data if available
  if (currentProduct && currentProduct.priceLow != null) {
    if (qty >= 50) return Math.max(currentProduct.priceLow * 0.67, 0.01);
    if (qty >= 10) return Math.max(currentProduct.priceLow * 0.85, 0.01);
    return currentProduct.priceLow;
  }
  // Demo fallback
  if (qty >= 50) return 3.50;
  if (qty >= 10) return 4.40;
  return 5.20;
}

function updateCost() {
  var qtyInput = document.getElementById('qty');
  var destSelect = document.getElementById('dest');
  if (!qtyInput || !destSelect) return;

  var qty = parseInt(qtyInput.value) || 2;
  var dest = destSelect.value;
  var unitPrice = getUnitPrice(qty);
  var productCost = +(unitPrice * qty).toFixed(2);
  var domesticShip = 0.5;
  var shipRate = shipRates[dest] || 4.5;
  var shipLow = shipRate;
  var shipHigh = +(shipRate + Math.max(0, qty - 1) * 1.5).toFixed(1);
  var serviceFee = 10;
  var totalLow = +(productCost + domesticShip + shipLow + serviceFee).toFixed(2);
  var totalHigh = +(productCost + domesticShip + shipHigh + serviceFee).toFixed(2);
  var deposit = +((totalLow + totalHigh) / 4).toFixed(2);

  var shipCostEl = document.getElementById('shipCost');
  var totalCostEl = document.getElementById('totalCost');
  var productCostEl = document.getElementById('productCost');
  var orderLink = document.getElementById('orderLink');

  if (shipCostEl) shipCostEl.textContent = I18N.formatPriceRange(shipLow, shipHigh);
  if (totalCostEl) totalCostEl.textContent = I18N.formatPriceRange(totalLow, totalHigh);
  if (productCostEl) {
    productCostEl.textContent = I18N.formatPrice(productCost);
    productCostEl.setAttribute('data-price-usd', productCost);
  }

  // CTA button
  if (orderLink) {
    var template = I18N.t('cta.button');
    if (template.indexOf('{price}') === -1) {
      template = CTA_TEMPLATES['zh'];
    }
    orderLink.textContent = template.replace('{price}', I18N.formatPrice(deposit));
  }

  // Update verdict text
  var verdictEl = document.querySelector('#tab-sample .verdict span:last-child');
  if (verdictEl) {
    updateVerdictText(verdictEl, totalCostEl, deposit);
  }
}

function updateVerdictText(verdictEl, totalCostEl, deposit) {
  var totalText = totalCostEl ? totalCostEl.textContent : '';
  var locale = I18N.getLocale();
  var dp = I18N.formatPrice(deposit);

  if (locale === 'zh') {
    verdictEl.textContent = '样品到手 ' + totalText + '，付 ' + dp + ' 定金即可。验货确认后再付尾款。';
  } else if (locale === 'vi') {
    verdictEl.textContent = 'Mẫu đến tay ' + totalText + '. Trả trước ' + dp + '. Duyệt ảnh trước khi thanh toán.';
  } else {
    verdictEl.textContent = 'Sample delivered at ' + totalText + '. Pay ' + dp + ' deposit. Confirm photos before balance.';
  }
}

function bindCostInputs() {
  var qtyInput = document.getElementById('qty');
  var destSelect = document.getElementById('dest');
  if (qtyInput) qtyInput.addEventListener('input', updateCost);
  if (destSelect) destSelect.addEventListener('change', updateCost);
}

// ===== Inspect detail toggle =====
function bindInspectToggle() {
  var btn = document.getElementById('inspectToggle');
  var detail = document.getElementById('inspectDetail');
  if (!btn || !detail) return;
  btn.addEventListener('click', function() {
    var open = detail.style.display !== 'none';
    detail.style.display = open ? 'none' : 'block';
    btn.classList.toggle('active', !open);
    btn.textContent = open ? '?' : '×';
  });
}

// ===== Bootstrap: i18n first, then bind UI =====
I18N.init().then(function() {
  bindSubTabs();
  bindSearch();
  bindCostInputs();
  bindLangSwitcher();
  bindInspectToggle();
  updateCost();
});
