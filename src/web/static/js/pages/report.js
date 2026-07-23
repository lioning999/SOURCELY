// ===== report.js — 1688 商品分析报告页 =====
// 依赖：api/core.js, verdict.js, share.js, i18n.js, components.js
(function () {
  'use strict';

  // ===== DOM 引用 =====
  var searchBtn = document.getElementById('searchBtn');
  var searchInput = document.getElementById('searchInput');
  var searchHint = document.querySelector('.search-hint');
  var isSearching = false;

  // ===== 搜索按钮 =====
  searchBtn.addEventListener('click', function () {
    if (isSearching) return;
    var url = searchInput.value.trim();
    if (!url) return;

    isSearching = true;
    showSkeleton();
    searchBtn.disabled = true;
    searchBtn.textContent = '分析中...';
    searchHint.textContent = '正在获取 1688 商品数据，预计 20-40 秒...';

    startAnalysis(url);
  });

  // ===== API 调用（委托给 api/core.js） =====

  function startAnalysis(url) {
    API.analyze(url)
      .then(function (data) {
        if (data.code !== 200) {
          showError(data.message || '分析启动失败');
          return;
        }
        var taskId = data.data.task_id;
        sessionStorage.setItem('lastTaskId', taskId);
        pollTask(taskId, 0);
      })
      .catch(function (err) {
        showError('网络错误，请检查网络后重试');
        console.warn('Analyze start failed:', err);
      });
  }

  function pollTask(taskId, attempt) {
    if (attempt > 60) {
      showError('分析超时，请稍后重试');
      return;
    }

    API.getTask(taskId)
      .then(function (data) {
        var task = data.data;
        if (!task) {
          showError('任务不存在或已过期');
          return;
        }

        if (task.status === 'done') {
          resetSearchButton();
          searchHint.textContent = '每日免费 3 次 · WhatsApp 登记后不限次数';
          sessionStorage.removeItem('lastTaskId');
          renderResult(task.result);
          if (task.warning) showWarning(task.warning);
        } else if (task.status === 'failed') {
          hideSkeleton();
          showError(task.error || '分析失败，请稍后重试');
          sessionStorage.removeItem('lastTaskId');
        } else {
          var elapsed = attempt * 2;
          if (elapsed >= 10) {
            searchHint.textContent = '正在获取商品数据，预计还需 ' + Math.max(5, 30 - elapsed) + ' 秒...';
          }
          setTimeout(function () { pollTask(taskId, attempt + 1); }, 2000);
        }
      })
      .catch(function (err) {
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
    // 统一 Toast（用户可能在页面下方，searchHint 不在视野内）
    if (typeof Toast !== 'undefined') {
      Toast.error(msg);
    }
    setTimeout(function () {
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
      saveBar.style.display = 'flex';
      saveBar.className = 'save-bar login-hint';
      saveBtn.textContent = '💾 保存';
      saveBtn.disabled = false;
      saveBtn.classList.remove('saved');
      saveBtn.onclick = function () {
        window.location.href = '/api/auth/google/login';
      };
      return;
    }

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
    saveBtn.onclick = function () { doSave(); };
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

    API.saveReport(currentOfferId)
      .then(function (data) {
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
      .catch(function () {
        saveBtn.textContent = '💾 保存';
        saveBtn.disabled = false;
      });
  }

  // ===== 渲染分析结果到页面 =====
  var productData = { priceMin: 7.5, moq: 2, unit: '把' };

  function renderResult(data) {
    var skel = document.getElementById('loadingSkeleton');
    var card = document.getElementById('productCard');
    if (skel) skel.style.display = 'none';
    if (card) card.style.display = 'block';

    productData.priceMin = data.priceCNY ? data.priceCNY.low : 0;
    productData.moq = data.moq || 2;
    productData.unit = data.unit || '件';

    renderProductCard(data);
    renderFactoryInfo(data);
    renderProductDetails(data);

    updateVerdict('tab-product', Verdict.buildProductVerdict(data));
    updateVerdict('tab-factory', Verdict.buildFactoryVerdict(data));
    updateVerdict('tab-sample',  data.verdict_sample);

    updateCost();
    if (data.offerId) showSaveBar(data.offerId);
  }

  function renderProductCard(data) {
    // 标题
    var titleEl = document.querySelector('.prod-title');
    if (titleEl) { titleEl.textContent = data.title || ''; titleEl.title = data.title || ''; }

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

    // 信任条
    var tbLabel = document.querySelector('.tb-label');
    var tbSold = document.querySelector('.tb-sold');
    var tbYears = document.querySelector('.tb-years');
    var tierStars = document.getElementById('tierStars');
    if (tbLabel && data.sellerTierLabel) tbLabel.textContent = data.sellerTierLabel;
    if (tbSold && data.sold) tbSold.textContent = '已售 ' + Verdict.formatNum(data.sold) + '+';
    if (tbYears && data.shop_years) tbYears.textContent = '开店' + data.shop_years + '年';
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

    // Badge 行
    var badgeEl = document.querySelector('.badge-row');
    if (badgeEl) {
      var badges = [];
      if (data.return7day === 'OK') badges.push('<span class="badge-sm green">7天无理由退货</span>');
      if (data.repurchase) badges.push('<span class="badge-sm gold">回头率 ' + data.repurchase + '%</span>');
      if (data.badgeLabels && data.badgeLabels.some(function (b) { return b.label === '支持混批'; })) {
        badges.push('<span class="badge-sm green">支持混批</span>');
      }
      badgeEl.innerHTML = badges.length ? badges.join(' ') : '';
      badgeEl.style.display = badges.length ? '' : 'none';
    }

    // 主图 + 缩略图
    if (data.images && data.images.length) {
      var mainImg = document.getElementById('mainImg');
      if (mainImg) mainImg.src = data.images[0];
      var thumbCol = document.getElementById('thumbCol');
      if (thumbCol) {
        var imgs = thumbCol.querySelectorAll('img');
        data.images.slice(0, 5).forEach(function (src, i) {
          if (imgs[i]) { imgs[i].src = src; imgs[i].dataset.full = src; if (i === 0) imgs[i].classList.add('active'); }
        });
      }
    }
  }

  function renderFactoryInfo(data) {
    // 公司名称（折叠区）
    var rowName = document.getElementById('row-name');
    if (data.supplierName && rowName) {
      var nameVal = rowName.querySelector('.row-value');
      if (nameVal) nameVal.textContent = data.supplierName;
    }
    // 地址（折叠区）
    var rowAddr = document.getElementById('row-addr');
    if (data.shippingLocation && rowAddr) {
      var addrVal = rowAddr.querySelector('.row-value');
      if (addrVal) addrVal.textContent = data.shippingLocation;
      if (data.industryCluster) {
        var addrExp = rowAddr.querySelector('.row-explain');
        if (addrExp) addrExp.textContent = data.industryCluster + '。源头产地，价格有优势。';
      }
    }
    // 商家身份（高亮区）
    var sellerVal = document.getElementById('sellerVal');
    var sellerExp = document.getElementById('sellerExp');
    var rowIdentity = document.getElementById('row-identity');
    if (sellerVal && data.sellerTierLabel) {
      sellerVal.textContent = '🏭 ' + data.sellerTierLabel;
      if (sellerExp) {
        sellerExp.textContent = data.sellerTierLabel === '源头工厂'
          ? '1688 平台认证的生产厂家，具备自主生产能力。'
          : '该商家为贸易商/代理商，非生产厂家。建议拿样验证货源品质。';
      }
    } else if (rowIdentity) { rowIdentity.style.display = 'none'; }

    // 工厂实力（次要区）
    var flagsVal = document.getElementById('flagsValue');
    var flagsExp = document.getElementById('flagsExplain');
    var rowFlags = document.getElementById('row-flags');
    if (flagsVal && data.factoryFlags) {
      if (data.factoryFlags.indexOf('非生产厂家') !== -1) {
        flagsVal.textContent = '不适用';
        if (flagsExp) flagsExp.textContent = '贸易商无自有工厂产能，货源来自第三方供应商。';
      } else {
        flagsVal.textContent = data.factoryFlags;
        if (flagsExp) {
          if (data.factoryFlags.indexOf('超级工厂') !== -1)
            flagsExp.textContent = '1688 最高规格验厂认证，自有工厂与生产线，小单试水到批量翻单都能接。';
          else if (data.factoryFlags.indexOf('源头旗舰') !== -1)
            flagsExp.textContent = '1688 现货赛道头部认证，主打现货库存，价格有优势。可放心采购，建议拿样确认。';
          else if (data.factoryFlags.indexOf('实力工厂') !== -1)
            flagsExp.textContent = '1688 官方验厂认证（体系更新中），具备稳定生产能力与基础品控。建议拿样试水。';
          else
            flagsExp.textContent = '自称工厂但未获 1688 高级验厂。建议先拿样，验证产线和品质。';
        }
      }
    } else if (rowFlags) { rowFlags.style.display = 'none'; }

    // 认证类型（高亮区）
    var certVal = document.getElementById('certValue');
    var certExp = document.getElementById('certExplain');
    var certLink = document.getElementById('certReportLink');
    var shopLink = document.getElementById('certShopLink');
    var shopSep = document.getElementById('certShopSep');
    if (certVal && data.certType) {
      certVal.innerHTML = '<span class="cert-badge">🔖 ' + data.certType + '</span>';
      if (certExp) certExp.textContent = '第三方机构实地验厂认证，核实企业生产资质与经营状况。';
      if (data.certReportUrl && certLink) { certLink.href = data.certReportUrl; certLink.style.display = ''; }
      else if (certLink) { certLink.style.display = 'none'; }
      if (shopLink && data.shopUrl) {
        shopLink.href = data.shopUrl; shopLink.style.display = '';
        if (shopSep) shopSep.style.display = (data.certReportUrl && certLink) ? '' : 'none';
      } else { if (shopLink) shopLink.style.display = 'none'; if (shopSep) shopSep.style.display = 'none'; }
    } else if (certVal) {
      certVal.innerHTML = '<span style="font-size:var(--fs-sm);color:var(--ink-3);">暂无认证</span>';
      if (certLink) certLink.style.display = 'none';
      if (shopLink && data.shopUrl) {
        if (certExp) certExp.textContent = '该商家暂未展示第三方验厂认证。';
        shopLink.href = data.shopUrl; shopLink.style.display = '';
        if (shopSep) shopSep.style.display = 'none';
      } else {
        if (certExp) certExp.textContent = '该商家暂未展示第三方验厂认证。建议拿样后确认品质。';
        if (shopLink) shopLink.style.display = 'none'; if (shopSep) shopSep.style.display = 'none';
      }
    }

    // 品类排名（次要区）
    var rankRow = document.getElementById('row-rank');
    if (rankRow) {
      var rVal = rankRow.querySelector('.row-value');
      var rExp = rankRow.querySelector('.row-explain');
      if (data.rankText) {
        if (rVal) rVal.textContent = '🏆 ' + data.rankText;
      } else {
        if (rVal) rVal.textContent = '暂无排名';
        if (rExp) rExp.textContent = '该商家暂未上榜 1688 品类排名榜单。';
      }
    }
  }

  function renderProductDetails(data) {
    // 规格
    if (data.specs && data.specs.length) {
      var specEl = document.querySelector('.prod-specs');
      if (specEl) {
        specEl.innerHTML = data.specs.map(function (s) {
          return '<span class="spec-tag">' + s.name + ': ' + s.value + '</span>';
        }).join('');
      }
    }
    // 阶梯价格表
    var qpTbody = document.querySelector('.qp-table tbody');
    if (qpTbody && data.price_tiers && data.price_tiers.length) {
      qpTbody.innerHTML = data.price_tiers.map(function (t) {
        var qtyRange = t.qty_min + '~' + (t.qty_max || '以上') + data.unit;
        return '<tr><td>' + qtyRange + '</td><td>' + (t.qty_min || '') + '</td><td>¥' + t.unit_price + '</td></tr>';
      }).join('');
    } else if (qpTbody) { document.querySelector('.qp-table').style.display = 'none'; }
    // SKU 图
    if (data.skus && data.skus.length) {
      var skuEl = document.querySelector('.sku-imgs');
      if (skuEl) {
        skuEl.innerHTML = data.skus.slice(0, 6).map(function (s) {
          var imgUrl = s.sku_image || s.imgUrl || s.image || s.picUrl || '';
          var name = s.sku_name || s.name || '';
          return '<img src="' + imgUrl + '" alt="' + name + '" title="' + name + '">';
        }).join('');
      }
    }
    // 销售数据行
    var salesRow = document.querySelector('#tab-product .row');
    if (salesRow && data.sold) {
      var salesVal = salesRow.querySelector('.row-value');
      if (salesVal) salesVal.textContent = Verdict.formatNum(data.sold) + ' 件';
      var salesExp = salesRow.querySelector('.row-explain');
      if (salesExp && data.sold >= 1000) salesExp.textContent = '累计销量高说明市场验证通过，该品类有持续需求。';
    }
  }

  function updateVerdict(tabId, text) {
    if (!text) return;
    var panel = document.getElementById(tabId);
    if (!panel) return;
    var verdictEl = panel.querySelector('.verdict span:last-child');
    if (verdictEl) verdictEl.textContent = text;
  }

  // ===== 页面恢复 =====
  (function () {
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

  // ===== 静态样例加载 =====
  (function () {
    var params = new URLSearchParams(window.location.search);
    var sample = params.get('sample');
    if (!sample) return;

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
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        renderResult(data);
        updateCost();
        hideSkeleton();
        searchHint.textContent = '静态样例 — 非实时数据，仅供演示';
        searchInput.value = data.itemUrl || '';
        isSearching = false;
        searchBtn.disabled = false;
        searchBtn.textContent = '分析';
        if (data.offerId) showSaveBar(data.offerId);
      })
      .catch(function (err) {
        console.warn('Sample load failed:', err);
        hideSkeleton();
        searchHint.textContent = '样例加载失败，请粘贴链接搜索';
        isSearching = false;
        searchBtn.disabled = false;
        searchBtn.textContent = '分析';
      });
  })();

  // ===== URL 参数自动分析 =====
  (function () {
    if (sessionStorage.getItem('lastTaskId')) return;

    var params = new URLSearchParams(window.location.search);
    var sample = params.get('sample');
    var offerId = params.get('offerId');
    var urlParam = params.get('url');

    if (sample) return;
    if (!offerId && !urlParam) return;

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

  // ===== 国际运费表 =====
  var shipRates = {
    VN: { eco: [3, 5],  label: '🚛 陆运', days: '4-7天', exp: [7, 12], expLabel: '✈️ 空运', expDays: '2-3天' },
    TH: { eco: [5, 8],  label: '🚛 陆运', days: '5-7天', exp: [8, 15], expLabel: '✈️ 空运', expDays: '3-5天' },
    ID: { eco: [10, 18], label: '✈️ 空运', days: '5-10天', exp: null, expLabel: null, expDays: null },
    MY: { eco: [5, 8],  label: '🚛 陆运', days: '5-7天', exp: [8, 14], expLabel: '✈️ 空运', expDays: '3-5天' },
    PH: { eco: [10, 16], label: '✈️ 空运', days: '7-10天', exp: null, expLabel: null, expDays: null }
  };

  var USD_RATE = 7.2;
  var SERVICE_FEE = 10;
  var DOMESTIC_FREIGHT = 10;

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

    if (productFeeEl) productFeeEl.textContent = '¥' + cny.toFixed(2) + ' ≈ $' + usd;
    if (domesticFeeEl) domesticFeeEl.textContent = '¥' + DOMESTIC_FREIGHT.toFixed(2) + ' ≈ $' + domUsd;
    if (depositTotalEl) depositTotalEl.textContent = '¥' + depCny.toFixed(2) + ' ≈ $' + depUsd;

    var dest = destSel.value;
    var ship = shipRates[dest];
    if (shipFeeValEl) shipFeeValEl.textContent = '$' + ship.eco[0] + ' – $' + ship.eco[1];
    if (shipMetaEl) shipMetaEl.textContent = ship.label + ship.days + ',按实重/体积计算';

    var balLow = ship.eco[0] + SERVICE_FEE;
    var balHigh = ship.eco[1] + SERVICE_FEE;
    if (balanceTotalEl) balanceTotalEl.textContent = '$' + balLow + ' – $' + balHigh;

    var totalLow = (depCny / USD_RATE) + ship.eco[0] + SERVICE_FEE;
    var totalHigh = (depCny / USD_RATE) + ship.eco[1] + SERVICE_FEE;
    if (totalFeeEl) totalFeeEl.textContent = '$' + Math.round(totalLow) + ' – $' + Math.round(totalHigh);
  }

  qtyMinus.addEventListener('click', function () {
    if (qty > productData.moq) { qty--; qtyVal.textContent = qty; updateCost(); }
  });
  qtyPlus.addEventListener('click', function () {
    if (qty < 50) { qty++; qtyVal.textContent = qty; updateCost(); }
  });
  destSel.addEventListener('change', updateCost);

  // ===== 折叠/展开 =====
  document.getElementById('factoryDetailToggle').addEventListener('click', function () {
    var d = document.getElementById('factoryDetail');
    var expanded = d.style.display !== 'none';
    if (expanded) {
      d.style.display = 'none';
      this.textContent = '📋 查看公司信息 ▾';
    } else {
      d.style.display = 'block';
      this.textContent = '📋 收起公司信息 ▴';
    }
  });

  document.getElementById('inspectToggle').addEventListener('click', function () {
    var d = document.getElementById('inspectDetail');
    if (d.style.display === 'none') { d.style.display = 'block'; this.classList.add('active'); }
    else { d.style.display = 'none'; this.classList.remove('active'); }
  });

  // ===== 缩略图切主图 =====
  var mainImg = document.getElementById('mainImg');
  var thumbVideo = document.getElementById('thumbVideo');
  var videoUrl = 'https://cloud.video.taobao.com/play/u/2211084454599/p/2/e/6/t/1/525219744434.mp4';

  document.querySelectorAll('#thumbCol img').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      document.querySelectorAll('#thumbCol img').forEach(function (t) { t.classList.remove('active'); });
      this.classList.add('active');
      mainImg.src = this.dataset.full;
      mainImg.style.display = 'block';
      var oldV = mainImg.parentNode.querySelector('video');
      if (oldV) oldV.remove();
    });
  });

  thumbVideo.addEventListener('click', function () {
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
    document.querySelectorAll('#thumbCol img').forEach(function (t) { t.classList.remove('active'); });
  });

  // ===== Tab 切换 =====
  document.querySelectorAll('.tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (t) { t.classList.remove('active'); });
      document.querySelectorAll('.panel').forEach(function (p) { p.classList.remove('active'); });
      this.classList.add('active');
      document.getElementById('tab-' + this.dataset.tab).classList.add('active');
    });
  });

  // ===== 初始化 =====
  updateCost();
  Share.bindEvents();

})();
