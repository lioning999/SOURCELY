// ============================================================
// Sourcely — i18n loader + currency formatter
// 3 locales: zh (HTML default), en, vi
// All locale data inlined — no fetch() needed (file:// safe).
// All prices stored in USD. Display formatted per locale.
// ============================================================
var I18N = (function() {
  'use strict';

  // ----- Static exchange rates (1 USD = X local units) -----
  // Update weekly.
  var RATES = {
    VND: 25450,  THB: 35.7,  IDR: 16100,  MYR: 4.65,  PHP: 57.2,
  };

  var SYMBOLS = {
    VND: '₫', THB: '฿', IDR: 'Rp', MYR: 'RM', PHP: '₱',
  };

  // ----- Locale config -----
  var LOCALES = {
    vi: { label: 'Tiếng Việt', currency: 'VND', flag: 'VN' },
    en: { label: 'English',    currency: 'USD', flag: 'US' },
    zh: { label: '中文',       currency: 'USD', flag: 'CN' },
  };

  // ----- All locale messages inlined (file:// safe) -----
  // zh is the HTML baseline — no messages needed.
  var MESSAGES = {};

  MESSAGES['en'] = {
    "nav.analyze": "Analyze", "nav.order": "Order", "nav.admin": "Admin",
    "search.placeholder": "Paste 1688 product link...",
    "search.hint": "3 free per day · Unlimited after WhatsApp registration",
    "search.button": "Analyze", "search.analyzing": "Analyzing...",
    "search.invalid": "Please enter a valid 1688 link",
    "stamp.l1": "Exclusive", "stamp.l2": "NO MATCH",
    "product.title": "Women's One-Piece Swimsuit",
    "product.unit": "/ pc", "product.original": "1688 Price",
    "warn": "This supplier does not ship directly to overseas individual buyers. We handle the full process: 1688 ordering, domestic receiving, inspection, and international shipping.",
    "tab.product": "Product", "tab.images": "Images", "tab.factory": "Factory", "tab.sample": "Sample",
    "gallery.product": "Product Images", "gallery.desc": "Description",
    "verdict.product": "Sellable — 7-day returns, steady sales, low MOQ",
    "verdict.factory": "Reliable factory — verified, direct source. Check shipping speed.",
    "row.7day.label": "7-Day Free Returns", "row.7day.value": "Supported",
    "row.7day.desc": "Factory confident in quality. Can return if defective — low trial cost.",
    "row.sales.label": "30-Day Sales", "row.sales.value": "156 orders · ¥6,240",
    "row.sales.desc": "Consistent turnover, 327 want-to-buy. Market validated.",
    "row.moq.label": "MOQ", "row.moq.value": "2 pcs minimum",
    "row.moq.desc": "Very low barrier, low-cost testing. ",
    "row.moq.link": "View on 1688 →",
    "row.service.label": "Service Guarantee", "row.service.value": "48h Shipping · Quality · Free Delivery",
    "row.service.desc": "Service tags promised by seller. More tags = more reliable fulfillment.",
    "sec.cert": "Factory Certifications · Xingcheng Daluoyou Garment Co., Ltd.",
    "row.verified.label": "1688 Verified Supplier", "row.verified.value": "Verified",
    "row.verified.desc": "Complete certifications. Trustworthy.",
    "row.mode.label": "Business Type", "row.mode.value": "Manufacturer",
    "row.mode.desc": "Direct source factory. No middleman markup.",
    "row.location.label": "Shipping From", "row.location.value": "Liaoning Xingcheng",
    "row.location.desc": "Liaoning Xingcheng — China's swimwear hub, 70% of national output. Source region = price advantage.",
    "row.cross.label": "Cross-Border Ready", "row.cross.value": "No Record",
    "row.cross.desc": "No overseas order history. Packaging & shipping workflow may not be familiar with international requirements.",
    "row.speed.label": "Shipping Speed", "row.speed.value": "Below Average",
    "row.speed.desc": "1688 shows slower than peers. Lock in delivery date when ordering, add buffer time.",
    "cost.breakdown": "Cost Breakdown",
    "cost.product": "Product Cost", "cost.shipping": "Intl. Shipping",
    "cost.service": "Service + Domestic Freight", "cost.total": "Delivered Estimate",
    "cost.note": "* Intl. shipping calculated by actual weight/volume. Final price confirmed before dispatch.",
    "cost.shippingNote": "* Estimate based on 0.3-1kg small package. Actual shipping confirmed before dispatch. Overcharge will be refunded.",
    "cost.qty": "Quantity", "cost.dest": "Destination",
    "sec.process": "Service Process",
    "process.step1": "1. 1688 Purchase", "process.step2": "2. Receive & Inspect",
    "process.step3": "3. Photos for Approval", "process.step4": "4. Intl. Shipping",
    "process.inspectTitle": "Upon receiving the goods, we check:",
    "process.inspect1": "Color matches product images",
    "process.inspect2": "Dimensions match spec parameters",
    "process.inspect3": "No visible damage or defects",
    "process.inspect4": "Quantity is correct",
    "process.inspect5": "Take 3-5 photos for your WhatsApp approval",
    "process.inspectNote": "⚠️ Quality issue found → We notify you → You decide refund or exchange → We execute. Service fee is non-refundable but we will help coordinate.",
    "process.fee": "$10 service fee covers all steps above.",
    "cta.button": "Order Sample · Pay {price} Deposit",
    "cta.sub": "We order on 1688 → Receive & inspect with photos → You confirm → Pay balance → Shipped to your door",
    "cta.deposit": "Only 50% deposit required. Pay balance after photo confirmation.",
    "wa.question": "Questions?", "wa.link": "WhatsApp: +86 138-xxxx-xxxx",
    "testimonial.text": "\"Ordered 3 times via the platform. Inspection photos are detailed, shipping on time.\"",
    "testimonial.name": "— Linh Nguyen", "testimonial.meta": "Ho Chi Minh City · Shopee Seller",
    "currency.ref": "≈ $USD · Reference rate · Settled in USD",
    "checkout.title": "Sample Order", "checkout.summary": "Order Summary",
    "checkout.qty": "Qty: 2 pcs",
    "checkout.estimated": "Estimated Total", "checkout.deposit": "Deposit (50%)",
    "checkout.balance": "Balance after photo confirmation. Pay only after you approve inspection photos.",
    "checkout.shipping": "Shipping Info",
    "checkout.name": "Full Name *", "checkout.phone": "Phone (with country code) *",
    "checkout.email": "Email *", "checkout.whatsapp": "WhatsApp (optional)",
    "checkout.address": "Shipping Address *",
    "checkout.address.placeholder": "Street, house number, city, province, postal code, country",
    "checkout.note": "Special Requests (optional)",
    "checkout.note.placeholder": "E.g.: Confirm fabric elasticity, check stitching, verify color is pure black",
    "checkout.pay": "Pay $13.45 Deposit", "checkout.problem": "Issues with your order?",
    "checkout.payment": "Payment Method",
    "checkout.alipayDesc": "Scan to pay · Instant settlement",
    "checkout.paypalDesc": "International · Buyer Protection",
    "modal.success": "Order Received!",
    "modal.msg1": "We will purchase your sample on 1688 within <strong>48 hours</strong>, receive it, take photos, and send them for your approval.",
    "modal.msg2": "You approve photos → Pay balance → We ship internationally.",
    "modal.step1": "1. Deposit Paid", "modal.step2": "2. Inspection & Photos", "modal.step3": "3. Shipped",
    "modal.back": "Back to Home",
    "admin.title": "Order Board", "admin.count": "3 orders · Deposit received $30.95",
    "admin.col.order": "Order #", "admin.col.product": "Product", "admin.col.customer": "Customer",
    "admin.col.deposit": "Deposit", "admin.col.status": "Status", "admin.col.action": "Action",
    "admin.st.pending": "Awaiting Purchase", "admin.st.ordered": "1688 Ordered",
    "admin.st.photos": "Photos Sent", "admin.st.paid": "Balance Paid", "admin.st.shipped": "Shipped",
    "admin.btn.ordered": "Ordered on 1688", "admin.btn.received": "Received & Photographed",
    "admin.btn.photos": "Photos Sent → Pay Balance", "admin.btn.paid": "Customer Paid Balance",
    "admin.btn.shipped": "Shipped",
    "admin.flow": "Customer Progress Bar",
    "admin.flow.step1": "1. Deposit Paid", "admin.flow.step2": "2. Inspected & Photos", "admin.flow.step3": "3. Shipped",
    "admin.customer1": "Zhang San · Thailand", "admin.customer2": "Linh · Vietnam", "admin.customer3": "Maria · Indonesia",
    "alipay.title": "Alipay Payment", "alipay.amount": "Payment Amount",
    "alipay.order": "Order #SAMPLE-001", "alipay.scan": "Scan with Alipay",
    "alipay.scanHint": "Open Alipay App → Scan → Confirm Payment",
    "alipay.or": "or", "alipay.card": "Card Payment",
    "alipay.cardNumber": "Card Number", "alipay.expiry": "Expiry", "alipay.cvv": "CVV",
    "alipay.cardName": "Cardholder Name",
    "alipay.pay": "Confirm Payment", "alipay.processing": "Processing...",
    "alipay.success": "Payment Successful!",
    "alipay.successMsg": "Payment received. We will begin processing your order.",
    "alipay.back": "Back to Order"
  };

  MESSAGES['vi'] = {
    "nav.analyze": "Phân Tích", "nav.order": "Đặt Hàng", "nav.admin": "Quản Lý",
    "search.placeholder": "Dán link sản phẩm 1688...",
    "search.hint": "3 lần/ngày miễn phí · Đăng ký WhatsApp để không giới hạn",
    "search.button": "Phân Tích", "search.analyzing": "Đang phân tích...",
    "search.invalid": "Vui lòng nhập link 1688 hợp lệ",
    "stamp.l1": "Độc Quyền", "stamp.l2": "NO MATCH",
    "product.title": "Đồ Bơi Một Mảnh Nữ",
    "product.unit": "/ cái", "product.original": "Giá Gốc",
    "warn": "Nhà cung cấp này không gửi trực tiếp cho người mua nước ngoài. Chúng tôi lo toàn bộ: đặt hàng 1688, nhận hàng nội địa, kiểm tra, và vận chuyển quốc tế.",
    "tab.product": "Sản Phẩm", "tab.images": "Hình Ảnh", "tab.factory": "Xưởng", "tab.sample": "Lấy Mẫu",
    "gallery.product": "Hình Sản Phẩm", "gallery.desc": "Mô Tả Chi Tiết",
    "verdict.product": "Bán được — đổi trả 7 ngày, bán đều, MOQ thấp",
    "verdict.factory": "Xưởng uy tín — đã xác minh, nguồn trực tiếp. Kiểm tra tốc độ giao.",
    "row.7day.label": "Đổi Trả 7 Ngày", "row.7day.value": "Hỗ Trợ",
    "row.7day.desc": "Xưởng tự tin về chất lượng. Có thể trả lại nếu lỗi — chi phí thử thấp.",
    "row.sales.label": "Doanh Số 30 Ngày", "row.sales.value": "156 đơn · ¥6,240",
    "row.sales.desc": "Bán đều đặn, 327 người muốn mua. Đã được thị trường kiểm chứng.",
    "row.moq.label": "MOQ", "row.moq.value": "Tối thiểu 2 cái",
    "row.moq.desc": "Rào cản rất thấp, thử nghiệm chi phí thấp. ",
    "row.moq.link": "Xem trên 1688 →",
    "row.service.label": "Đảm Bảo Dịch Vụ", "row.service.value": "Giao 48h · Chất Lượng · Miễn Phí Ship",
    "row.service.desc": "Thẻ dịch vụ từ người bán 1688. Càng nhiều thẻ càng đáng tin.",
    "sec.cert": "Chứng Nhận Xưởng · Xingcheng Daluoyou Garment Co., Ltd.",
    "row.verified.label": "Nhà Cung Cấp 1688 Đã Xác Minh", "row.verified.value": "Đã Xác Minh",
    "row.verified.desc": "Chứng nhận đầy đủ. Đáng tin cậy cao.",
    "row.mode.label": "Loại Hình Kinh Doanh", "row.mode.value": "Nhà Sản Xuất",
    "row.mode.desc": "Xưởng nguồn trực tiếp. Không qua trung gian.",
    "row.location.label": "Nơi Gửi Hàng", "row.location.value": "Liêu Ninh Xingcheng",
    "row.location.desc": "Liêu Ninh Xingcheng — trung tâm đồ bơi Trung Quốc, 70% sản lượng toàn quốc. Vùng nguồn = giá tốt.",
    "row.cross.label": "Sẵn Sàng Xuyên Biên Giới", "row.cross.value": "Chưa Có",
    "row.cross.desc": "Không có lịch sử đơn hàng nước ngoài. Đóng gói & vận chuyển có thể chưa quen yêu cầu quốc tế.",
    "row.speed.label": "Tốc Độ Giao Hàng", "row.speed.value": "Dưới Trung Bình",
    "row.speed.desc": "1688 hiển thị chậm hơn trung bình. Chốt ngày giao khi đặt hàng, thêm thời gian dự phòng.",
    "cost.breakdown": "Chi Tiết Chi Phí",
    "cost.product": "Tiền Hàng", "cost.shipping": "Phí Ship Quốc Tế",
    "cost.service": "Phí Dịch Vụ + Nội Địa", "cost.total": "Tổng Đến Tay (Ước Tính)",
    "cost.note": "* Phí ship quốc tế tính theo cân nặng/thể tích thực tế. Giá cuối xác nhận trước khi gửi.",
    "cost.shippingNote": "* Ước tính dựa trên gói nhỏ 0.3-1kg. Phí ship thực tế xác nhận trước khi gửi. Thu thừa sẽ hoàn lại.",
    "cost.qty": "Số Lượng", "cost.dest": "Nước Đến",
    "sec.process": "Quy Trình",
    "process.step1": "1. Đặt Hàng 1688", "process.step2": "2. Nhận & Kiểm Tra",
    "process.step3": "3. Gửi Ảnh Duyệt", "process.step4": "4. Ship Quốc Tế",
    "process.inspectTitle": "Khi nhận hàng, chúng tôi kiểm tra:",
    "process.inspect1": "Màu sắc khớp với ảnh sản phẩm",
    "process.inspect2": "Kích thước khớp với thông số kỹ thuật",
    "process.inspect3": "Không có hư hỏng hoặc lỗi",
    "process.inspect4": "Số lượng chính xác",
    "process.inspect5": "Chụp 3-5 ảnh gửi bạn duyệt qua WhatsApp",
    "process.inspectNote": "⚠️ Phát hiện vấn đề chất lượng → Báo bạn → Bạn quyết định hoàn tiền hoặc đổi hàng → Chúng tôi thực hiện. Phí dịch vụ không hoàn lại nhưng sẽ hỗ trợ bạn.",
    "process.fee": "Phí dịch vụ $10 bao gồm tất cả các bước trên.",
    "cta.button": "Đặt Mẫu · Trả Trước {price}",
    "cta.sub": "Chúng tôi đặt trên 1688 → Nhận & kiểm tra chụp ảnh → Bạn duyệt → Thanh toán phần còn lại → Gửi đến tận nhà",
    "cta.deposit": "Chỉ cần đặt cọc 50%. Thanh toán phần còn lại sau khi duyệt ảnh.",
    "wa.question": "Có thắc mắc?", "wa.link": "WhatsApp: +86 138-xxxx-xxxx",
    "testimonial.text": "\"Đã đặt 3 lần qua nền tảng. Ảnh kiểm tra chi tiết, giao hàng đúng hẹn.\"",
    "testimonial.name": "— Linh Nguyen", "testimonial.meta": "TP. Hồ Chí Minh · Người bán Shopee",
    "currency.ref": "≈ $USD · Tỷ giá tham khảo · Thanh toán bằng USD",
    "checkout.title": "Đặt Mẫu", "checkout.summary": "Tóm Tắt Đơn Hàng",
    "checkout.qty": "SL: 2 cái",
    "checkout.estimated": "Tổng Ước Tính", "checkout.deposit": "Đặt Cọc (50%)",
    "checkout.balance": "Phần còn lại sau khi duyệt ảnh. Chỉ thanh toán sau khi bạn đồng ý ảnh kiểm tra.",
    "checkout.shipping": "Thông Tin Nhận Hàng",
    "checkout.name": "Họ Tên *", "checkout.phone": "SĐT (có mã quốc gia) *",
    "checkout.email": "Email *", "checkout.whatsapp": "WhatsApp (tùy chọn)",
    "checkout.address": "Địa Chỉ Nhận Hàng *",
    "checkout.address.placeholder": "Số nhà, đường, thành phố, tỉnh, mã bưu chính, quốc gia",
    "checkout.note": "Yêu Cầu Đặc Biệt (tùy chọn)",
    "checkout.note.placeholder": "VD: Kiểm tra độ co giãn vải, kiểm tra đường may, xác nhận màu đen tuyền",
    "checkout.pay": "Thanh Toán $13.45", "checkout.problem": "Gặp vấn đề với đơn hàng?",
    "checkout.payment": "Phương Thức Thanh Toán",
    "checkout.alipayDesc": "Quét mã QR · Thanh toán ngay",
    "checkout.paypalDesc": "Quốc tế · Bảo Vệ Người Mua",
    "modal.success": "Đã Nhận Đơn Hàng!",
    "modal.msg1": "Chúng tôi sẽ mua mẫu của bạn trên 1688 trong vòng <strong>48 giờ</strong>, nhận hàng, chụp ảnh và gửi bạn duyệt.",
    "modal.msg2": "Bạn duyệt ảnh → Thanh toán phần còn lại → Chúng tôi gửi hàng quốc tế.",
    "modal.step1": "1. Đã Đặt Cọc", "modal.step2": "2. Kiểm Tra & Chụp Ảnh", "modal.step3": "3. Đã Gửi Hàng",
    "modal.back": "Về Trang Chủ",
    "admin.title": "Bảng Đơn Hàng", "admin.count": "3 đơn hàng · Đã nhận cọc $30.95",
    "admin.col.order": "Mã Đơn", "admin.col.product": "Sản Phẩm", "admin.col.customer": "Khách Hàng",
    "admin.col.deposit": "Đặt Cọc", "admin.col.status": "Trạng Thái", "admin.col.action": "Thao Tác",
    "admin.st.pending": "Chờ Mua Hàng", "admin.st.ordered": "Đã Đặt 1688",
    "admin.st.photos": "Đã Gửi Ảnh", "admin.st.paid": "Đã Thanh Toán", "admin.st.shipped": "Đã Gửi Hàng",
    "admin.btn.ordered": "Đã Đặt Trên 1688", "admin.btn.received": "Đã Nhận & Chụp Ảnh",
    "admin.btn.photos": "Đã Gửi Ảnh → Thanh Toán", "admin.btn.paid": "Khách Đã Thanh Toán",
    "admin.btn.shipped": "Đã Gửi Hàng",
    "admin.flow": "Thanh Tiến Độ Khách Hàng",
    "admin.flow.step1": "1. Đã Đặt Cọc", "admin.flow.step2": "2. Đã Kiểm Tra & Chụp Ảnh", "admin.flow.step3": "3. Đã Gửi Hàng",
    "admin.customer1": "Zhang San · Thái Lan", "admin.customer2": "Linh · Việt Nam", "admin.customer3": "Maria · Indonesia",
    "alipay.title": "Thanh Toán Alipay", "alipay.amount": "Số Tiền Thanh Toán",
    "alipay.order": "Đơn #SAMPLE-001", "alipay.scan": "Quét Mã QR Bằng Alipay",
    "alipay.scanHint": "Mở App Alipay → Quét Mã → Xác Nhận",
    "alipay.or": "hoặc", "alipay.card": "Thanh Toán Thẻ",
    "alipay.cardNumber": "Số Thẻ", "alipay.expiry": "Hết Hạn", "alipay.cvv": "CVV",
    "alipay.cardName": "Tên Chủ Thẻ",
    "alipay.pay": "Xác Nhận Thanh Toán", "alipay.processing": "Đang Xử Lý...",
    "alipay.success": "Thanh Toán Thành Công!",
    "alipay.successMsg": "Đã nhận thanh toán. Chúng tôi sẽ bắt đầu xử lý đơn hàng của bạn.",
    "alipay.back": "Quay Lại Đơn Hàng"
  };

  // ----- State -----
  var current = null;  // { lang, label, currency, flag }
  var messages = {};   // active locale strings
  var zhSnapped = false;

  // Snapshot Chinese text from HTML (run once before first apply)
  function snapshotZh() {
    if (zhSnapped) return;
    var zh = {};
    // data-i18n elements
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      if (key) zh[key] = els[i].innerHTML;
    }
    // data-i18n-placeholder elements
    var phs = document.querySelectorAll('[data-i18n-placeholder]');
    for (var j = 0; j < phs.length; j++) {
      var pk = phs[j].getAttribute('data-i18n-placeholder');
      if (pk) zh[pk] = phs[j].placeholder;
    }
    MESSAGES['zh'] = zh;
    zhSnapped = true;
  }

  // ----- Detect browser locale -----
  function detect() {
    var lang = (navigator.language || 'en').slice(0, 2).toLowerCase();
    if (lang === 'vi') return 'vi';
    if (lang === 'zh') return 'zh';
    return 'en'; // default: English
  }

  // ----- Load locale (sync — all data is already in memory) -----
  function load(lang) {
    snapshotZh(); // ensure zh snapshot exists
    current = LOCALES[lang];
    current.lang = lang;
    messages = MESSAGES[lang] || {};
    return Promise.resolve();
  }

  // ----- Apply translations to DOM -----
  function apply() {
    // data-i18n → innerHTML (supports <br>)
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      if (messages[key]) {
        els[i].innerHTML = messages[key];
      }
    }
    // data-i18n-placeholder → placeholder attr
    var phs = document.querySelectorAll('[data-i18n-placeholder]');
    for (var j = 0; j < phs.length; j++) {
      var pk = phs[j].getAttribute('data-i18n-placeholder');
      if (messages[pk]) phs[j].placeholder = messages[pk];
    }
    // data-i18n-alt → alt attr
    var alts = document.querySelectorAll('[data-i18n-alt]');
    for (var k = 0; k < alts.length; k++) {
      var ak = alts[k].getAttribute('data-i18n-alt');
      if (messages[ak]) alts[k].alt = messages[ak];
    }
    // Prices
    formatAllPrices();
    // HTML lang
    document.documentElement.lang = current.lang;

    // Sync lang switcher
    var sw = document.getElementById('langSwitcher');
    if (sw) sw.value = current.lang;
  }

  // ----- Bootstrap: detect → load → apply -----
  function init() {
    var lang = detect();
    return load(lang).then(apply);
  }

  // ----- Manual switch -----
  function switchTo(lang) {
    return load(lang).then(apply);
  }

  // ----- Currency formatting -----
  function formatPrice(usd) {
    if (!current || current.currency === 'USD') {
      return '$' + usd.toFixed(2);
    }
    var local = usd * RATES[current.currency];
    var symbol = SYMBOLS[current.currency] || '';

    if (current.currency === 'VND' || current.currency === 'IDR') {
      var rounded = Math.round(local / 1000) * 1000;
      return symbol + rounded.toLocaleString('en-US');
    }
    return symbol + local.toFixed(0);
  }

  function formatPriceRange(usdLow, usdHigh) {
    if (!current || current.currency === 'USD') {
      return '$' + usdLow.toFixed(2) + ' – $' + usdHigh.toFixed(2);
    }
    return formatPrice(usdLow) + ' – ' + formatPrice(usdHigh);
  }

  // Apply to all [data-price-usd] elements
  function formatAllPrices() {
    var els = document.querySelectorAll('[data-price-usd]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var usd = parseFloat(el.getAttribute('data-price-usd'));
      if (isNaN(usd)) continue;
      var rangeHigh = el.getAttribute('data-price-high');
      if (rangeHigh) {
        el.textContent = formatPriceRange(usd, parseFloat(rangeHigh));
      } else {
        el.textContent = formatPrice(usd);
      }
      el.setAttribute('data-last-usd', usd);
    }
  }

  // ----- Public -----
  function getCurrency() { return current && current.currency; }
  function getLocale()   { return current && current.lang; }
  function t(key)        { return messages[key] || ''; }
  function getLocales()  { return LOCALES; }

  // Export
  return {
    init: init, detect: detect, load: load, apply: apply, switchTo: switchTo,
    formatPrice: formatPrice, formatPriceRange: formatPriceRange,
    formatAllPrices: formatAllPrices,
    getCurrency: getCurrency, getLocale: getLocale, getLocales: getLocales,
    t: t, RATES: RATES, SYMBOLS: SYMBOLS,
  };
})();
