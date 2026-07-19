// ============================================================
// Sourcely — Landing page interactions
// ============================================================

// ----- Sub-tab switching (产品 / 工厂 / 拿样) -----
var subBar = document.querySelector('.tabs');
if (subBar) {
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
  });
}

// ----- Search simulation -----
var searchBtn = document.getElementById('searchBtn');
var searchInput = document.getElementById('searchInput');

if (searchBtn && searchInput) {
  searchBtn.addEventListener('click', function() {
    var val = searchInput.value.trim();
    if (!val) {
      searchInput.style.borderColor = 'var(--bad)';
      searchInput.placeholder = '请输入有效的 1688 链接';
      setTimeout(function() {
        searchInput.style.borderColor = '';
        searchInput.placeholder = '粘贴 1688 商品链接...';
      }, 1500);
      return;
    }
    searchBtn.textContent = '分析中...';
    searchBtn.disabled = true;
    setTimeout(function() {
      searchBtn.textContent = '分析';
      searchBtn.disabled = false;
      var card = document.getElementById('productCard');
      if (card) {
        card.scrollIntoView({ behavior: 'smooth' });
        card.style.boxShadow = '0 0 0 3px rgba(30,58,95,.14)';
        setTimeout(function() { card.style.boxShadow = ''; }, 800);
      }
    }, 1000);
  });
}

// ----- Cost calculator -----
var qtyInput = document.getElementById('qty');
var destSelect = document.getElementById('dest');
var shipRates = { TH: 4.5, VN: 3.8, ID: 5.2, MY: 3.5, PH: 5.8 };

function getUnitPrice(qty) {
  if (qty >= 50) return 3.50;
  if (qty >= 10) return 4.40;
  return 5.20;
}

function updateCost() {
  var qty = parseInt(qtyInput.value) || 2;
  var dest = destSelect.value;
  var unitPrice = getUnitPrice(qty);
  var productCost = unitPrice * qty;
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

  if (shipCostEl) shipCostEl.textContent = '$' + shipLow.toFixed(1) + ' – $' + shipHigh.toFixed(1);
  if (totalCostEl) totalCostEl.textContent = '$' + totalLow.toFixed(2) + ' – $' + totalHigh.toFixed(2);
  if (productCostEl) productCostEl.textContent = '$' + productCost.toFixed(2);
  if (orderLink) orderLink.textContent = '拿样品 · 付 $' + deposit.toFixed(2) + ' 定金';
}

if (qtyInput) qtyInput.addEventListener('input', updateCost);
if (destSelect) destSelect.addEventListener('change', updateCost);
