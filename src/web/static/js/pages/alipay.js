// ============================================================
// Sourcely — Alipay payment page
// ============================================================

// ----- Card form toggle -----
function bindCardToggle() {
  var toggle = document.getElementById('cardToggle');
  var form = document.getElementById('cardForm');
  if (!toggle || !form) return;

  toggle.addEventListener('click', function() {
    var visible = form.style.display === 'block';
    form.style.display = visible ? 'none' : 'block';
    toggle.classList.toggle('active', !visible);
  });
}

// ----- Payment simulation -----
function bindPayment() {
  var btn = document.getElementById('payConfirmBtn');
  var qrBox = document.getElementById('qrBox');
  var successCard = document.getElementById('successCard');
  var paymentCard = btn.closest('.card');

  if (!btn) return;

  btn.addEventListener('click', function() {
    btn.textContent = '...';
    btn.disabled = true;

    setTimeout(function() {
      // Hide payment card, show success
      if (paymentCard) paymentCard.style.display = 'none';
      if (successCard) successCard.style.display = 'block';
      if (successCard) {
        successCard.scrollIntoView({ behavior: 'smooth' });
      }
    }, 1200);
  });
}

// ----- Bootstrap -----
I18N.init().then(function() {
  bindCardToggle();
  bindPayment();

  // Lang switcher
  var sw = document.getElementById('langSwitcher');
  if (sw) {
    sw.addEventListener('change', function() {
      I18N.switchTo(sw.value).then(function() {
        I18N.formatAllPrices();
      });
    });
  }
});
