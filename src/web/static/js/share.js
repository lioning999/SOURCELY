// ===== 分享功能（html2canvas 生成图片） =====
// 依赖：html2canvas（CDN 加载）、DOM 元素 #shareOverlay / #shareCardTmpl / #mainImg / .prod-title / .prod-price / .badge-row / .trust-bar
var Share = (function () {
  'use strict';

  function escapeHTML(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function buildShareCard() {
    var mainImg = document.getElementById('mainImg');
    var mainImgSrc = mainImg ? mainImg.src : '';
    var titleEl = document.querySelector('.prod-title');
    var title = titleEl ? titleEl.textContent.trim() : '';
    var priceEl = document.querySelector('.prod-price');
    var priceText = priceEl ? priceEl.textContent.trim() : '';
    var badgeEl = document.querySelector('.badge-row');
    var badges = badgeEl ? badgeEl.innerHTML : '';
    var trustEl = document.querySelector('.trust-bar');
    var trustHTML = trustEl ? trustEl.innerHTML : '';
    var shareCardTmpl = document.getElementById('shareCardTmpl');

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

    if (shareCardTmpl) {
      shareCardTmpl.innerHTML = html;
      return shareCardTmpl.firstElementChild;
    }
    return null;
  }

  var shareBlob = null;
  var shareFile = null;

  function renderAndShow() {
    if (typeof html2canvas === 'undefined') {
      console.warn('html2canvas not loaded, share disabled');
      return;
    }
    var card = buildShareCard();
    if (!card) return;
    card.offsetHeight;

    html2canvas(card, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#FFFFFF'
    }).then(function (canvas) {
      canvas.toBlob(function (blob) {
        shareBlob = blob;
        shareFile = new File([blob], 'sourcely-decision-card.png', { type: 'image/png' });
        var sharePreviewImg = document.getElementById('sharePreviewImg');
        var shareOverlay = document.getElementById('shareOverlay');
        if (sharePreviewImg) sharePreviewImg.src = URL.createObjectURL(blob);
        if (shareOverlay) shareOverlay.classList.add('show');
      }, 'image/png', 0.85);
    }).catch(function (err) {
      console.warn('html2canvas render error:', err);
      alert('图片生成失败，请重试。如持续失败请截图分享。');
    });
  }

  function closeSheet() {
    var shareOverlay = document.getElementById('shareOverlay');
    var shareCardTmpl = document.getElementById('shareCardTmpl');
    if (shareOverlay) shareOverlay.classList.remove('show');
    if (shareCardTmpl) shareCardTmpl.innerHTML = '';
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
      }).catch(function (err) {
        if (err.name !== 'AbortError') {
          console.warn('Share failed:', err);
          saveImage();
        }
      });
    } else {
      saveImage();
    }
  }

  function bindEvents() {
    var shareBtnMain = document.getElementById('shareBtnMain');
    var shareClose = document.getElementById('shareClose');
    var shareSave = document.getElementById('shareSave');
    var shareSend = document.getElementById('shareSend');
    var shareOverlay = document.getElementById('shareOverlay');

    if (shareBtnMain) shareBtnMain.addEventListener('click', renderAndShow);
    if (shareClose) shareClose.addEventListener('click', closeSheet);
    if (shareSave) shareSave.addEventListener('click', saveImage);
    if (shareSend) shareSend.addEventListener('click', shareToApp);
    if (shareOverlay) {
      shareOverlay.addEventListener('click', function (e) {
        if (e.target === shareOverlay) closeSheet();
      });
    }
  }

  return {
    bindEvents: bindEvents,
    renderAndShow: renderAndShow,
    closeSheet: closeSheet,
    saveImage: saveImage
  };
})();
