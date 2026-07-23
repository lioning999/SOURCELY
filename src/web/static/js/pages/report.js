// ===== 风险 #10 #11：搜索按钮防重 + 异步轮询 =====
var searchBtn = document.getElementById('searchBtn');
var searchInput = document.getElementById('searchInput');
var searchHint = document.querySelector('.search-hint');
var isSearching = false;

searchBtn.addEventListener('click', function() {
  if (isSearching) return;  // L1 防重
  var url = searchInput.value.trim();
  if (!url) return;

  // L1 按钮 disabled + 文案
  isSearching = true;
  showSkeleton();
  searchBtn.disabled = true;
  searchBtn.textContent = '分析中...';
  searchHint.textContent = '正在获取 1688 商品数据，预计 20-40 秒...';

  startAnalysis(url);
});

/** 构造带 auth 的 headers（登录用户自动附带 token） */
function authHeaders() {
  var headers = { 'Content-Type': 'application/json' };
  var token = getToken && getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  return headers;
}

/** POST /api/analyze → 拿到 task_id → 开始轮询 */
function startAnalysis(url) {
  fetch('/api/analyze', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ url: url })
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code !== 200) {
        showError(data.message || '分析启动失败');
        return;
      }
      var taskId = data.data.task_id;
      // 保存 task_id 到 sessionStorage（风险 #15：切走页面再回来恢复轮询）
      sessionStorage.setItem('lastTaskId', taskId);
      pollTask(taskId, 0);
    })
    .catch(function(err) {
      showError('网络错误，请检查网络后重试');
      console.warn('Analyze start failed:', err);
    });
}

/** GET /api/analyze/{task_id} → 轮询直到 done/failed */
function pollTask(taskId, attempt) {
  // 超时保护：最多轮询 60 次（2 分钟）
  if (attempt > 60) {
    showError('分析超时，请稍后重试');
    return;
  }

  fetch('/api/analyze/' + taskId)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var task = data.data;
      if (!task) {
        showError('任务不存在或已过期');
        return;
      }

      if (task.status === 'done') {
        // 成功
        resetSearchButton();
        searchHint.textContent = '每日免费 3 次 · WhatsApp 登记后不限次数';
        sessionStorage.removeItem('lastTaskId');
        renderResult(task.result);
        if (task.warning) {
          showWarning(task.warning);
        }
      } else if (task.status === 'failed') {
        hideSkeleton();
        showError(task.error || '分析失败，请稍后重试');
        sessionStorage.removeItem('lastTaskId');
      } else {
        // pending / running → 继续轮询
        var elapsed = attempt * 2;
        if (elapsed >= 10) {
          searchHint.textContent = '正在获取商品数据，预计还需 ' + Math.max(5, 30 - elapsed) + ' 秒...';
        }
        setTimeout(function() { pollTask(taskId, attempt + 1); }, 2000);
      }
    })
    .catch(function(err) {
      showError('网络错误，请检查网络后重试');
      console.warn('Poll failed:', err);
      sessionStorage.removeItem('lastTaskId');
    });
}

function resetSearchButton() {
  isSearching = false;
  searchBtn.disabled = false;
  searchBtn.textContent = '分析';
}

function showSkeleton() {
  var skel = document.getElementById('loadingSkeleton');
  var card = document.getElementById('productCard');
  if (skel) skel.style.display = 'block';
  if (card) card.style.display = 'none';
}

function hideSkeleton() {
  var skel = document.getElementById('loadingSkeleton');
  if (skel) skel.style.display = 'none';
}

function showError(msg) {
  hideSkeleton();
  resetSearchButton();
  searchHint.textContent = msg;
  searchHint.style.color = 'var(--seal)';
  setTimeout(function() {
    searchHint.textContent = '每日免费 3 次 · WhatsApp 登记后不限次数';
    searchHint.style.color = '';
  }, 5000);
}

function showWarning(msg) {
  searchHint.textContent = '⚠ ' + msg;
  searchHint.style.color = 'var(--warn)';
}

// ===== 保存按钮 =====
var saveBar = document.getElementById('saveBar');
var saveBtn = document.getElementById('saveBtn');
var currentOfferId = null;

function showSaveBar(offerId) {
  if (!saveBar) return;
  currentOfferId = offerId;

  var user = checkAuth();
  if (!user) {
    // 未登录：保存按钮引导登录
    saveBar.style.display = 'flex';
    saveBar.className = 'save-bar login-hint';
    saveBtn.textContent = '💾 保存';
    saveBtn.disabled = false;
    saveBtn.classList.remove('saved');
    saveBtn.onclick = function() {
      window.location.href = '/api/auth/google/login';
    };
    return;
  }

  // 已登录：检查是否已保存
  var savedKey = 'saved_' + offerId;
  if (sessionStorage.getItem(savedKey)) {
    showSaved();
    return;
  }

  saveBar.style.display = 'flex';
  saveBar.className = 'save-bar';
  saveBtn.textContent = '💾 保存';
  saveBtn.disabled = false;
  saveBtn.classList.remove('saved');
  saveBtn.onclick = function() { doSave(); };
}

function showSaved() {
  saveBar.style.display = 'flex';
  saveBar.className = 'save-bar';
  saveBtn.textContent = '✓ 已保存';
  saveBtn.disabled = true;
  saveBtn.classList.add('saved');
  saveBtn.onclick = null;
}

function doSave() {
  if (!currentOfferId) return;
  saveBtn.disabled = true;
  saveBtn.textContent = '保存中...';

  var token = getToken();
  fetch('/api/save-report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({ offer_id: currentOfferId })
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.code === 200) {
        sessionStorage.setItem('saved_' + currentOfferId, '1');
        showSaved();
      } else if (data.code === 410) {
        saveBtn.textContent = '⚠ 已过期';
        saveBtn.disabled = true;
      } else if (data.code === 401) {
        saveBtn.textContent = '💾 保存';
        saveBtn.disabled = false;
      } else {
        saveBtn.textContent = '💾 保存';
        saveBtn.disabled = false;
      }
    })
    .catch(function() {
      saveBtn.textContent = '💾 保存';
      saveBtn.disabled = false;
    });
}

// ===== 渲染分析结果到页面 =====
var productData = { priceMin: 7.5, moq: 2, unit: '把' };  // 默认值

function renderResult(data) {
  // 切换骨架屏 → 卡片
  var skel = document.getElementById('loadingSkeleton');
  var card = document.getElementById('productCard');
  if (skel) skel.style.display = 'none';
  if (card) card.style.display = 'block';

  // 更新全局产品数据（成本计算器用）
  productData.priceMin = data.priceCNY ? data.priceCNY.low : 0;
  productData.moq = data.moq || 2;
  productData.unit = data.unit || '件';

  // 标题
  var titleEl = document.querySelector('.prod-title');
  if (titleEl) {
    titleEl.textContent = data.title || '';
    titleEl.title = data.title || '';
  }

  // 价格
  var priceEl = document.querySelector('.prod-price');
  if (priceEl) {
    var cnyLow = (data.priceCNY && data.priceCNY.low) ? '¥' + data.priceCNY.low : '';
    var cnyHigh = (data.priceCNY && data.priceCNY.high) ? ' – ¥' + data.priceCNY.high : '';
    var unitText = data.unit ? ' / ' + data.unit : '';
    var moqText = data.moq ? ' <span class="price-moq">· 起批 <strong>' + data.moq + ' 件</strong></span>' : '';
    var linkHtml = data.itemUrl ? ' <a href="' + data.itemUrl + '" target="_blank" class="price-link">1688 原页 →</a>' : '';
    priceEl.innerHTML = cnyLow + cnyHigh + '<em>' + unitText + '</em>' + moqText + linkHtml;
  }

  // 信任条：身份 + 累加销量 + 年限 + 数据完整度信号
  var tbLabel = document.querySelector('.tb-label');
  var tbSold = document.querySelector('.tb-sold');
  var tbYears = document.querySelector('.tb-years');
  var tierStars = document.getElementById('tierStars');

  if (tbLabel && data.sellerTierLabel) tbLabel.textContent = data.sellerTierLabel;
  if (tbSold && data.sold) tbSold.textContent = '已售 ' + formatNum(data.sold) + '+';
  if (tbYears && data.shop_years) tbYears.textContent = '开店' + data.shop_years + '年';

  // 数据完整度星级
  if (tierStars && data.dataTier) {
    var starMap = {
      sufficient: { stars: '★★★', label: '推荐' },
      partial:    { stars: '★★☆', label: '可考虑' },
      limited:    { stars: '★☆☆', label: '数据少' }
    };
    var s = starMap[data.dataTier] || starMap.limited;
    tierStars.textContent = s.stars + ' ' + s.label;
    tierStars.title = data.dataTierReason || '';
  }

  // Badge 行：7天退货 + 回头率 + 支持混批（动态）
  var badgeEl = document.querySelector('.badge-row');
  if (badgeEl) {
    var badges = [];
    // 7天无理由退货
    if (data.return7day === 'OK') badges.push('<span class="badge-sm green">7天无理由退货</span>');
    // 回头率
    if (data.repurchase) badges.push('<span class="badge-sm gold">回头率 ' + data.repurchase + '%</span>');
    // 支持混批
    if (data.badgeLabels && data.badgeLabels.some(function(b) { return b.label === '支持混批'; })) {
      badges.push('<span class="badge-sm green">支持混批</span>');
    }
    if (badges.length) {
      badgeEl.innerHTML = badges.join(' ');
      badgeEl.style.display = '';
    } else {
      badgeEl.style.display = 'none';
    }
  }

  // 工厂 tab（按 ID 定位各行）
  var factoryRows = document.querySelectorAll('#tab-factory .row');
  if (data.supplierName && factoryRows[0]) {
    var nameVal = factoryRows[0].querySelector('.row-value');
    if (nameVal) nameVal.textContent = data.supplierName;
  }
  if (data.shippingLocation && factoryRows[1]) {
    var addrVal = factoryRows[1].querySelector('.row-value');
    if (addrVal) addrVal.textContent = data.shippingLocation;
    if (data.industryCluster) {
      var addrExp = factoryRows[1].querySelector('.row-explain');
      if (addrExp) addrExp.textContent = data.industryCluster + '。源头产地，价格有优势。';
    }
  }

  // 商家身份（与 trust-bar 一致：源头工厂 / 贸易商）
  var sellerVal = document.getElementById('sellerVal');
  var sellerExp = document.getElementById('sellerExp');
  if (sellerVal && data.sellerTierLabel) {
    sellerVal.textContent = '🏭 ' + data.sellerTierLabel;
    if (sellerExp) {
      if (data.sellerTierLabel === '源头工厂') {
        sellerExp.textContent = '1688 平台认证的生产厂家，具备自主生产能力。';
      } else {
        sellerExp.textContent = '该商家为贸易商/代理商，非生产厂家。建议拿样验证货源品质。';
      }
    }
  } else if (factoryRows[2]) {
    factoryRows[2].style.display = 'none';
  }

  // 工厂实力
  var flagsVal = document.getElementById('flagsValue');
  var flagsExp = document.getElementById('flagsExplain');
  if (flagsVal && data.factoryFlags) {
    if (data.factoryFlags.indexOf('非生产厂家') !== -1) {
      flagsVal.textContent = '不适用';
      if (flagsExp) flagsExp.textContent = '贸易商无自有工厂产能，货源来自第三方供应商。';
    } else {
      flagsVal.textContent = data.factoryFlags;
      if (flagsExp) {
        if (data.factoryFlags.indexOf('超级工厂') !== -1) {
          flagsExp.textContent = '1688 最高规格验厂认证，自有工厂与生产线，小单试水到批量翻单都能接。';
        } else if (data.factoryFlags.indexOf('源头旗舰') !== -1) {
          flagsExp.textContent = '1688 现货赛道头部认证，主打现货库存，价格有优势。可放心采购，建议拿样确认。';
        } else if (data.factoryFlags.indexOf('实力工厂') !== -1) {
          flagsExp.textContent = '1688 官方验厂认证（体系更新中），具备稳定生产能力与基础品控。建议拿样试水。';
        } else {
          flagsExp.textContent = '自称工厂但未获 1688 高级验厂。建议先拿样，验证产线和品质。';
        }
      }
    }
  } else if (factoryRows[3]) {
    factoryRows[3].style.display = 'none';
  }

  // 认证类型（含 1688 店铺链接）
  var certVal = document.getElementById('certValue');
  var certExp = document.getElementById('certExplain');
  var certLink = document.getElementById('certReportLink');
  var shopLink = document.getElementById('certShopLink');
  var shopSep = document.getElementById('certShopSep');

  if (certVal && data.certType) {
    // 有认证
    certVal.innerHTML = '<span class="cert-badge">🔖 ' + data.certType + '</span>';
    if (certExp) certExp.textContent = '第三方机构实地验厂认证，核实企业生产资质与经营状况。';
    // 认证报告链接
    if (data.certReportUrl && certLink) {
      certLink.href = data.certReportUrl;
      certLink.style.display = '';
    } else if (certLink) {
      certLink.style.display = 'none';
    }
    // 店铺链接
    if (shopLink && data.shopUrl) {
      shopLink.href = data.shopUrl;
      shopLink.style.display = '';
      if (shopSep) shopSep.style.display = (data.certReportUrl && certLink) ? '' : 'none';
    } else {
      if (shopLink) shopLink.style.display = 'none';
      if (shopSep) shopSep.style.display = 'none';
    }
  } else if (certVal) {
    // 无认证
    certVal.innerHTML = '<span style="font-size:var(--fs-sm);color:var(--ink-3);">暂无认证</span>';
    if (certLink) certLink.style.display = 'none';
    if (shopLink && data.shopUrl) {
      // 没认证但有店铺链接
      if (certExp) certExp.textContent = '该商家暂未展示第三方验厂认证。';
      shopLink.href = data.shopUrl;
      shopLink.style.display = '';
      if (shopSep) shopSep.style.display = 'none';
    } else {
      if (certExp) certExp.textContent = '该商家暂未展示第三方验厂认证。建议拿样后确认品质。';
      if (shopLink) shopLink.style.display = 'none';
      if (shopSep) shopSep.style.display = 'none';
    }
  }

  // 品类排名
  var rankRow = factoryRows[5];
  if (data.rankText && rankRow) {
    var rVal = rankRow.querySelector('.row-value');
    if (rVal) rVal.textContent = '🏆 ' + data.rankText;
  } else if (rankRow) {
    var rVal = rankRow.querySelector('.row-value');
    var rExp = rankRow.querySelector('.row-explain');
    if (rVal) rVal.textContent = '暂无排名';
    if (rExp) rExp.textContent = '该商家暂未上榜 1688 品类排名榜单。';
  }

  // 判词
  updateVerdict('tab-product', data.verdict_product);
  updateVerdict('tab-factory', data.verdict_factory);
  updateVerdict('tab-sample',  data.verdict_sample);

  // 规格
  if (data.specs && data.specs.length) {
    var specEl = document.querySelector('.prod-specs');
    if (specEl) {
      specEl.innerHTML = data.specs.map(function(s) {
        return '<span class="spec-tag">' + s.name + ': ' + s.value + '</span>';
      }).join('');
    }
  }

  // 阶梯价格表
  var qpTbody = document.querySelector('.qp-table tbody');
  if (qpTbody && data.price_tiers && data.price_tiers.length) {
    qpTbody.innerHTML = data.price_tiers.map(function(t) {
      var qtyRange = t.qty_min + '~' + (t.qty_max || '以上') + data.unit;
      return '<tr><td>' + qtyRange + '</td><td>' + (t.qty_min || '') + '</td><td>¥' + t.unit_price + '</td></tr>';
    }).join('');
  } else if (qpTbody) {
    document.querySelector('.qp-table').style.display = 'none';
  }

  // SKU 图
  if (data.skus && data.skus.length) {
    var skuEl = document.querySelector('.sku-imgs');
    if (skuEl) {
      skuEl.innerHTML = data.skus.slice(0, 6).map(function(s) {
        var imgUrl = s.sku_image || s.imgUrl || s.image || s.picUrl || '';
        var name = s.sku_name || s.name || '';
        return '<img src="' + imgUrl + '" alt="' + name + '" title="' + name + '">';
      }).join('');
    }
  }

  // 销售数据行（产品 Tab 内）
  var salesRow = document.querySelector('#tab-product .row');
  if (salesRow && data.sold) {
    var salesVal = salesRow.querySelector('.row-value');
    if (salesVal) salesVal.textContent = formatNum(data.sold) + ' 件';
    var salesExp = salesRow.querySelector('.row-explain');
    if (salesExp && data.sold >= 1000) salesExp.textContent = '累计销量高说明市场验证通过，该品类有持续需求。';
  }

  // 主图 + 缩略图
  if (data.images && data.images.length) {
    var mainImg = document.getElementById('mainImg');
    if (mainImg) mainImg.src = data.images[0];

    var thumbCol = document.getElementById('thumbCol');
    if (thumbCol) {
      var imgs = thumbCol.querySelectorAll('img');
      var imgArr = data.images.slice(0, 5);
      imgArr.forEach(function(src, i) {
        if (imgs[i]) {
          imgs[i].src = src;
          imgs[i].dataset.full = src;
          if (i === 0) imgs[i].classList.add('active');
        }
      });
    }
  }

  // 更新成本计算器
  updateCost();

  // 显示保存按钮
  if (data.offerId) showSaveBar(data.offerId);
}

function updateVerdict(tabId, text) {
  if (!text) return;
  var panel = document.getElementById(tabId);
  if (!panel) return;
  var verdictEl = panel.querySelector('.verdict span:last-child');
  if (verdictEl) {
    verdictEl.textContent = text;
  }
}

function formatNum(n) {
  if (n >= 1000) return (n / 1000).toFixed(1).replace('.0', '') + 'k';
  return String(n);
}

// ===== 页面恢复：检查是否有未完成的任务（风险 #15） =====
(function() {
  var lastTaskId = sessionStorage.getItem('lastTaskId');
  if (lastTaskId) {
    searchHint.textContent = '检测到未完成的分析，正在恢复...';
    isSearching = true;
    showSkeleton();
    searchBtn.disabled = true;
    searchBtn.textContent = '分析中...';
    pollTask(lastTaskId, 0);
  }
})();

// ===== 静态样例加载：从首页示例卡跳转 → 加载本地 JSON，不调 API =====
(function() {
  var params = new URLSearchParams(window.location.search);
  var sample = params.get('sample');
  if (!sample) return;  // 非样例模式，跳过

  // 防止路径遍历：只允许字母数字和连字符
  if (!/^[a-zA-Z0-9_-]+$/.test(sample)) {
    searchHint.textContent = '无效的样例参数';
    return;
  }

  searchHint.textContent = '正在加载样例数据...';
  isSearching = true;
  showSkeleton();
  searchBtn.disabled = true;
  searchBtn.textContent = '加载中...';

  fetch('/samples/' + sample + '.json')
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(data) {
      renderResult(data);
      updateCost();
      hideSkeleton();
      searchHint.textContent = '静态样例 — 非实时数据，仅供演示';
      searchInput.value = data.itemUrl || '';
      isSearching = false;
      searchBtn.disabled = false;
      searchBtn.textContent = '分析';
      // 登录用户显示保存按钮
      if (data.offerId) showSaveBar(data.offerId);
    })
    .catch(function(err) {
      console.warn('Sample load failed:', err);
      hideSkeleton();
      searchHint.textContent = '样例加载失败，请粘贴链接搜索';
      isSearching = false;
      searchBtn.disabled = false;
      searchBtn.textContent = '分析';
    });
})();

// ===== URL 参数检测：从首页搜索/示例卡跳转过来 → 自动分析 =====
(function() {
  // 已有未完成任务在恢复中，不覆盖
  if (sessionStorage.getItem('lastTaskId')) return;

  var params = new URLSearchParams(window.location.search);
  var sample = params.get('sample');
  var offerId = params.get('offerId');
  var urlParam = params.get('url');

  if (sample) return;   // 样例模式，已由上方 IIFE 处理
  if (!offerId && !urlParam) return;  // 无参数 → 展示 demo，不调 API

  var targetUrl = offerId
    ? 'https://detail.1688.com/offer/' + offerId + '.html'
    : decodeURIComponent(urlParam);

  searchInput.value = targetUrl;
  searchHint.textContent = '正在获取 1688 商品数据，预计 20-40 秒...';
  isSearching = true;
  showSkeleton();
  searchBtn.disabled = true;
  searchBtn.textContent = '分析中...';
  startAnalysis(targetUrl);
})();

// ===== 国际运费表 (0.3-1kg 小包 · 经济方案) =====
// 每国分 eco（经济）和 exp（快线），eco 默认展示
var shipRates = {
  VN: { eco: [3, 5],  label: '🚛 陆运', days: '4-7天', exp: [7, 12], expLabel: '✈️ 空运', expDays: '2-3天' },
  TH: { eco: [5, 8],  label: '🚛 陆运', days: '5-7天', exp: [8, 15], expLabel: '✈️ 空运', expDays: '3-5天' },
  ID: { eco: [10, 18], label: '✈️ 空运', days: '5-10天', exp: null, expLabel: null, expDays: null },
  MY: { eco: [5, 8],  label: '🚛 陆运', days: '5-7天', exp: [8, 14], expLabel: '✈️ 空运', expDays: '3-5天' },
  PH: { eco: [10, 16], label: '✈️ 空运', days: '7-10天', exp: null, expLabel: null, expDays: null }
};

// ⚠ 与后端 Config.CNY_USD_RATE 保持同步。修改此处需同步改 config.py 默认值
var USD_RATE = 7.2;
var SERVICE_FEE = 10;
var DOMESTIC_FREIGHT = 10;  // ¥

var qtyVal = document.getElementById('qtyVal');
var qtyMinus = document.getElementById('qtyMinus');
var qtyPlus = document.getElementById('qtyPlus');
var destSel = document.getElementById('destSel');
var productFeeEl = document.getElementById('productFee');
var domesticFeeEl = document.getElementById('domesticFee');
var depositTotalEl = document.getElementById('depositTotal');
var shipFeeValEl = document.getElementById('shipFeeVal');
var shipMetaEl = document.getElementById('shipMeta');
var balanceTotalEl = document.getElementById('balanceTotal');
var totalFeeEl = document.getElementById('totalFee');

var qty = productData.moq;

function updateCost() {
  var cny = productData.priceMin * qty;
  var usd = (cny / USD_RATE).toFixed(2);
  var domUsd = (DOMESTIC_FREIGHT / USD_RATE).toFixed(2);
  var depCny = cny + DOMESTIC_FREIGHT;
  var depUsd = (depCny / USD_RATE).toFixed(2);

  // 定金段（双币显示：¥ ≈ $）
  if (productFeeEl) productFeeEl.textContent = '¥' + cny.toFixed(2) + ' ≈ $' + usd;
  if (domesticFeeEl) domesticFeeEl.textContent = '¥' + DOMESTIC_FREIGHT.toFixed(2) + ' ≈ $' + domUsd;
  if (depositTotalEl) depositTotalEl.textContent = '¥' + depCny.toFixed(2) + ' ≈ $' + depUsd;

  // 国际运费
  var dest = destSel.value;
  var ship = shipRates[dest];
  if (shipFeeValEl) shipFeeValEl.textContent = '$' + ship.eco[0] + ' – $' + ship.eco[1];
  if (shipMetaEl) shipMetaEl.textContent = ship.label + ship.days + ',按实重/体积计算';

  // 尾款小计
  var balLow = ship.eco[0] + SERVICE_FEE;
  var balHigh = ship.eco[1] + SERVICE_FEE;
  if (balanceTotalEl) balanceTotalEl.textContent = '$' + balLow + ' – $' + balHigh;

  // 预估总价
  var totalLow = (depCny / USD_RATE) + ship.eco[0] + SERVICE_FEE;
  var totalHigh = (depCny / USD_RATE) + ship.eco[1] + SERVICE_FEE;
  var totalStr = '$' + Math.round(totalLow) + ' – $' + Math.round(totalHigh);
  if (totalFeeEl) totalFeeEl.textContent = totalStr;
}

qtyMinus.addEventListener('click', function() {
  if (qty > productData.moq) { qty--; qtyVal.textContent = qty; updateCost(); }
});
qtyPlus.addEventListener('click', function() {
  if (qty < 50) { qty++; qtyVal.textContent = qty; updateCost(); }
});
destSel.addEventListener('change', updateCost);

// ===== 验货清单 toggle =====
document.getElementById('inspectToggle').addEventListener('click', function() {
  var d = document.getElementById('inspectDetail');
  if (d.style.display === 'none') { d.style.display = 'block'; this.classList.add('active'); }
  else { d.style.display = 'none'; this.classList.remove('active'); }
});

// ===== 缩略图切主图 =====
var mainImg = document.getElementById('mainImg');
var thumbVideo = document.getElementById('thumbVideo');
var videoUrl = 'https://cloud.video.taobao.com/play/u/2211084454599/p/2/e/6/t/1/525219744434.mp4';

document.querySelectorAll('#thumbCol img').forEach(function(thumb) {
  thumb.addEventListener('click', function() {
    document.querySelectorAll('#thumbCol img').forEach(function(t) { t.classList.remove('active'); });
    this.classList.add('active');
    mainImg.src = this.dataset.full;
    mainImg.style.display = 'block';
    var oldV = mainImg.parentNode.querySelector('video');
    if (oldV) oldV.remove();
  });
});

thumbVideo.addEventListener('click', function() {
  var wrap = mainImg.parentNode;
  var oldV = wrap.querySelector('video');
  if (oldV) oldV.remove();
  mainImg.style.display = 'none';
  var v = document.createElement('video');
  v.src = videoUrl;
  v.controls = true;
  v.style.width = '100%';
  v.style.borderRadius = '12px';
  v.style.background = '#000';
  v.play();
  wrap.appendChild(v);
  document.querySelectorAll('#thumbCol img').forEach(function(t) { t.classList.remove('active'); });
});

// ===== Tab 切换 =====
document.querySelectorAll('.tab').forEach(function(tab) {
  tab.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
    this.classList.add('active');
    document.getElementById('tab-' + this.dataset.tab).classList.add('active');
  });
});

// ===== 初始计算 =====
updateCost();

// ===== 分享功能 =====
var shareOverlay = document.getElementById('shareOverlay');
var sharePreviewImg = document.getElementById('sharePreviewImg');
var shareCardTmpl = document.getElementById('shareCardTmpl');
var shareBlob = null;
var shareFile = null;

function buildShareCard() {
  var mainImgSrc = document.getElementById('mainImg').src;
  var title = document.querySelector('.prod-title').textContent.trim();
  var priceText = document.querySelector('.prod-price').textContent.trim();
  var badges = document.querySelector('.badge-row').innerHTML;
  var trustHTML = document.querySelector('.trust-bar').innerHTML;

  var html = '<div style="padding:32px 28px 0;background:#FFFFFF;">';

  html += '<div style="margin-bottom:24px;">';
  html += '<div style="font-family:\'Noto Serif SC\',\'Songti SC\',serif;font-weight:700;font-size:22px;color:#232A38;letter-spacing:1px;">源采 SOURCELY</div>';
  html += '</div>';

  html += '<div style="width:694px;height:694px;border-radius:12px;overflow:hidden;background:#FAFAFA;margin-bottom:24px;">';
  html += '<img src="' + mainImgSrc + '" style="width:100%;height:100%;object-fit:cover;display:block;" crossorigin="anonymous">';
  html += '</div>';

  html += '<div style="font-family:\'Noto Serif SC\',\'Songti SC\',serif;font-weight:700;font-size:22px;color:#232A38;line-height:1.4;margin-bottom:12px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">' + escapeHTML(title) + '</div>';

  html += '<div style="font-family:\'JetBrains Mono\',\'SF Mono\',Menlo,monospace;font-size:30px;font-weight:700;color:#D6432F;margin-bottom:24px;">' + priceText + '</div>';

  html += '<div style="margin-bottom:16px;">' + badges + '</div>';

  html += '<div style="padding:10px 18px;background:#F8F7F3;border-left:4px solid #2F8A5B;border-radius:0 6px 6px 0;font-size:16px;font-weight:600;color:#232A38;display:flex;flex-wrap:wrap;gap:8px 20px;margin-bottom:24px;">' + trustHTML + '</div>';

  html += '<div style="background:#1E3A5F;margin:0 -28px;padding:16px 28px;display:flex;align-items:center;justify-content:space-between;">';
  html += '<div>';
  html += '<div style="font-weight:700;font-size:17px;color:#FFFFFF;letter-spacing:2px;">🔍 SOURCELY</div>';
  html += '<div style="font-size:13px;color:rgba(255,255,255,.75);margin-top:4px;">30秒看懂1688工厂</div>';
  html += '</div>';
  html += '<div style="font-size:14px;color:rgba(255,255,255,.6);font-family:\'JetBrains Mono\',\'SF Mono\',monospace;">sourcely.com</div>';
  html += '</div>';

  html += '</div>';

  shareCardTmpl.innerHTML = html;
  return shareCardTmpl.firstElementChild;
}

function escapeHTML(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderAndShow() {
  var card = buildShareCard();
  card.offsetHeight;

  html2canvas(card, {
    scale: 2,
    useCORS: true,
    allowTaint: true,
    backgroundColor: '#FFFFFF'
  }).then(function(canvas) {
    canvas.toBlob(function(blob) {
      shareBlob = blob;
      shareFile = new File([blob], 'sourcely-decision-card.png', { type: 'image/png' });
      sharePreviewImg.src = URL.createObjectURL(blob);
      shareOverlay.classList.add('show');
    }, 'image/png', 0.85);
  }).catch(function(err) {
    console.warn('html2canvas render error:', err);
    alert('图片生成失败，请重试。如持续失败请截图分享。');
  });
}

function closeSheet() {
  shareOverlay.classList.remove('show');
  shareCardTmpl.innerHTML = '';
}

function saveImage() {
  if (!shareBlob) return;
  var a = document.createElement('a');
  a.href = URL.createObjectURL(shareBlob);
  a.download = 'sourcely-decision-card.png';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function shareToApp() {
  if (!shareFile) return;
  if (navigator.share && navigator.canShare && navigator.canShare({ files: [shareFile] })) {
    navigator.share({
      files: [shareFile],
      title: 'Sourcely 产品决策卡',
      url: 'https://sourcely.com'
    }).catch(function(err) {
      if (err.name !== 'AbortError') {
        console.warn('Share failed:', err);
        saveImage();
      }
    });
  } else {
    saveImage();
  }
}

document.getElementById('shareBtnMain').addEventListener('click', renderAndShow);
document.getElementById('shareClose').addEventListener('click', closeSheet);
document.getElementById('shareSave').addEventListener('click', saveImage);
document.getElementById('shareSend').addEventListener('click', shareToApp);

shareOverlay.addEventListener('click', function(e) {
  if (e.target === shareOverlay) closeSheet();
});
