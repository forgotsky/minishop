// i18n language pack - Chinese/English bilingual support
// WeChat mini-program compatibility: NO ?. optional chaining, NO ?? nullish coalescing

var texts = {
  zh: {
    // ---- Common ----
    'common.loading': '加载中...',
    'common.noData': '暂无数据',
    'common.confirm': '确认',
    'common.cancel': '取消',
    'common.save': '保存',
    'common.delete': '删除',
    'common.edit': '编辑',
    'common.default': '默认',
    'common.all': '全部',
    'common.total': '合计',
    'common.price': '价格',
    'common.stock': '库存',
    'common.switchLang': 'EN',
    'common.switchLangHint': '切换到英文',

    // ---- Search ----
    'search.placeholder': '搜索商品...',
    'search.btn': '搜索',

    // ---- Index / Product List ----
    'index.all': '全部',
    'index.sold': ' sold',
    'index.loadMore': '加载更多',
    'index.empty': '暂无商品',
    'index.loading': '加载中...',

    // ---- Product Detail ----
    'product.sold': ' sold',
    'product.stock': '库存: ',
    'product.addToCart': '加入购物车',
    'product.buyNow': '立即购买',
    'product.loading': '加载中...',

    // ---- Cart ----
    'cart.empty': '购物车是空的',
    'cart.all': '全选',
    'cart.total': '合计: ',
    'cart.checkout': '去结算',
    'cart.del': '删除',
    'cart.removeTitle': '移除商品？',
    'cart.removeContent': '确定要移除此商品吗？',
    'cart.selectFirst': '请先选择商品',

    // ---- Checkout ----
    'checkout.address': '收货地址',
    'checkout.newAddress': '+ 新地址',
    'checkout.noAddress': '暂无地址',
    'checkout.addOne': '添加地址',
    'checkout.items': '商品',
    'checkout.coupon': '优惠券',
    'checkout.orderSummary': '订单摘要',
    'checkout.subtotal': '小计',
    'checkout.discount': '优惠',
    'checkout.delivery': '运费',
    'checkout.total': '合计',
    'checkout.placeOrder': '提交订单',
    'checkout.selectAddress': '请选择地址',
    'checkout.orderPlaced': '下单成功',
    'checkout.tapSelectCoupon': '点击选择优惠券',
    'checkout.noCoupons': '暂无可用优惠券',
    'checkout.failed': '下单失败',

    // ---- Order List ----
    'order.tab.all': '全部',
    'order.tab.pending': '待付款',
    'order.tab.paid': '待发货',
    'order.tab.shipped': '待收货',
    'order.tab.delivered': '已完成',
    'order.tab.completed': '已完成',
    'order.tab.cancelled': '已取消',
    'order.empty': '暂无订单',
    'order.loading': '加载中...',
    'order.noMore': '— 没有更多了 —',
    'order.itemCount': '共{itemCount}件商品',

    // ---- Order Detail ----
    'orderDetail.status.pending': '待付款',
    'orderDetail.status.paid': '待发货',
    'orderDetail.status.shipped': '待收货',
    'orderDetail.status.delivered': '已完成',
    'orderDetail.status.completed': '已完成',
    'orderDetail.status.cancelled': '已取消',
    'orderDetail.orderNo': '订单号：',
    'orderDetail.createTime': '下单时间：',
    'orderDetail.payTime': '支付时间：',
    'orderDetail.shippingAddress': '收货地址',
    'orderDetail.items': '商品清单',
    'orderDetail.priceDetail': '价格明细',
    'orderDetail.subtotal': '商品总额',
    'orderDetail.discount': '优惠',
    'orderDetail.delivery': '运费',
    'orderDetail.paymentAmount': '实付金额',
    'orderDetail.tracking': '物流信息',
    'orderDetail.trackingTip': '点击查看物流详情',
    'orderDetail.trackingNoInfo': '暂无物流信息',
    'orderDetail.courier': '快递公司：',
    'orderDetail.trackingNo': '运单号：',
    'orderDetail.unknown': '未知',
    'orderDetail.payNow': '立即支付',
    'orderDetail.cancelOrder': '取消订单',
    'orderDetail.confirmReceive': '确认收货',
    'orderDetail.viewTracking': '查看物流',
    'orderDetail.loadFailed': '加载失败',
    'orderDetail.paying': '支付中...',
    'orderDetail.paySuccess': '支付成功',
    'orderDetail.payFailed': '支付失败',
    'orderDetail.payCancelled': '支付已取消',
    'orderDetail.cancelTitle': '确认取消',
    'orderDetail.cancelContent': '确定要取消此订单吗？',
    'orderDetail.cancelled': '已取消',
    'orderDetail.cancelFailed': '取消失败',
    'orderDetail.receiveTitle': '确认收货',
    'orderDetail.receiveContent': '确认已收到货物？',
    'orderDetail.received': '已确认收货',
    'orderDetail.opFailed': '操作失败',

    // ---- Coupon ----
    'coupon.myCoupons': '我的优惠券',
    'coupon.getMore': '领取更多',
    'coupon.noCoupons': '暂无优惠券',
    'coupon.claim': '领取',
    'coupon.claiming': '领取中...',
    'coupon.claimed': '已领取',
    'coupon.noMinSpend': '无门槛',
    'coupon.status.unused': '未使用',
    'coupon.status.used': '已使用',
    'coupon.status.expired': '已过期',
    'coupon.percentOff': '% Off',
    'coupon.failed': '领取失败',

    // ---- Address ----
    'address.noAddress': '暂无地址',
    'address.addAddress': '+ 添加地址',
    'address.default': '默认',
    'address.del': '删除',
    'address.deleteTitle': '删除此地址？',
    'address.deleteConfirm': '确定要删除此地址吗？',

    // ---- Address Edit ----
    'addressEdit.fullName': '姓名 *',
    'addressEdit.phone': '电话 *',
    'addressEdit.province': '省 *',
    'addressEdit.city': '市 *',
    'addressEdit.district': '区 *',
    'addressEdit.street': '街道 *',
    'addressEdit.zipCode': '邮编',
    'addressEdit.isDefault': '默认地址',
    'addressEdit.save': '保存地址',
    'addressEdit.update': '更新地址',
    'addressEdit.fillRequired': '请填写必填项',
    'addressEdit.saved': '已保存',
    'addressEdit.saveFailed': '保存失败',
    'addressEdit.namePlaceholder': '收件人姓名',
    'addressEdit.phonePlaceholder': '手机号码',
    'addressEdit.provincePlaceholder': '省份',
    'addressEdit.cityPlaceholder': '城市',
    'addressEdit.districtPlaceholder': '区/县',
    'addressEdit.streetPlaceholder': '详细地址',
    'addressEdit.zipPlaceholder': '邮政编码',

    // ---- Toast ----
    'toast.addedToCart': '已加入购物车',
    'toast.networkError': '网络错误',
    'toast.saved': '已保存',
    'toast.saveFailed': '保存失败',
    'toast.fillRequired': '请填写必填项',
    'toast.orderPlaced': '下单成功！',
    'toast.orderFailed': '下单失败',
    'toast.selectAddress': '请选择地址',
    'toast.selectItems': '请先选择商品',
  },

  en: {
    // ---- Common ----
    'common.loading': 'Loading...',
    'common.noData': 'No data',
    'common.confirm': 'Confirm',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.default': 'Default',
    'common.all': 'All',
    'common.total': 'Total',
    'common.price': 'Price',
    'common.stock': 'Stock',
    'common.switchLang': '中',
    'common.switchLangHint': 'Switch to Chinese',

    // ---- Search ----
    'search.placeholder': 'Search products...',
    'search.btn': 'Search',

    // ---- Index / Product List ----
    'index.all': 'All',
    'index.sold': ' sold',
    'index.loadMore': 'Load more',
    'index.empty': 'No products found',
    'index.loading': 'Loading...',

    // ---- Product Detail ----
    'product.sold': ' sold',
    'product.stock': 'Stock: ',
    'product.addToCart': 'Add to Cart',
    'product.buyNow': 'Buy Now',
    'product.loading': 'Loading...',

    // ---- Cart ----
    'cart.empty': 'Your cart is empty',
    'cart.all': 'All',
    'cart.total': 'Total: ',
    'cart.checkout': 'Checkout',
    'cart.del': 'Del',
    'cart.removeTitle': 'Remove item?',
    'cart.removeContent': 'Remove this item from cart?',
    'cart.selectFirst': 'Please select items first',

    // ---- Checkout ----
    'checkout.address': 'Delivery Address',
    'checkout.newAddress': '+ New',
    'checkout.noAddress': 'No address',
    'checkout.addOne': 'Add one',
    'checkout.items': 'Items',
    'checkout.coupon': 'Coupon',
    'checkout.orderSummary': 'Order Summary',
    'checkout.subtotal': 'Subtotal',
    'checkout.discount': 'Discount',
    'checkout.delivery': 'Delivery',
    'checkout.total': 'Total',
    'checkout.placeOrder': 'Place Order',
    'checkout.selectAddress': 'Select address',
    'checkout.orderPlaced': 'Order placed!',
    'checkout.tapSelectCoupon': 'Tap to select coupon',
    'checkout.noCoupons': 'No coupons available',
    'checkout.failed': 'Failed',

    // ---- Order List ----
    'order.tab.all': 'All',
    'order.tab.pending': 'Pending',
    'order.tab.paid': 'Paid',
    'order.tab.shipped': 'Shipped',
    'order.tab.delivered': 'Completed',
    'order.tab.completed': 'Completed',
    'order.tab.cancelled': 'Cancelled',
    'order.empty': 'No orders',
    'order.loading': 'Loading...',
    'order.noMore': '— End —',
    'order.itemCount': '{itemCount} items',

    // ---- Order Detail ----
    'orderDetail.status.pending': 'Pending Payment',
    'orderDetail.status.paid': 'Awaiting Shipment',
    'orderDetail.status.shipped': 'In Transit',
    'orderDetail.status.delivered': 'Completed',
    'orderDetail.status.completed': 'Completed',
    'orderDetail.status.cancelled': 'Cancelled',
    'orderDetail.orderNo': 'Order No: ',
    'orderDetail.createTime': 'Created: ',
    'orderDetail.payTime': 'Paid: ',
    'orderDetail.shippingAddress': 'Shipping Address',
    'orderDetail.items': 'Items',
    'orderDetail.priceDetail': 'Price Details',
    'orderDetail.subtotal': 'Subtotal',
    'orderDetail.discount': 'Discount',
    'orderDetail.delivery': 'Delivery Fee',
    'orderDetail.paymentAmount': 'Amount Paid',
    'orderDetail.tracking': 'Tracking',
    'orderDetail.trackingTip': 'Tap to view tracking details',
    'orderDetail.trackingNoInfo': 'No tracking info',
    'orderDetail.courier': 'Courier: ',
    'orderDetail.trackingNo': 'Tracking No: ',
    'orderDetail.unknown': 'Unknown',
    'orderDetail.payNow': 'Pay Now',
    'orderDetail.cancelOrder': 'Cancel Order',
    'orderDetail.confirmReceive': 'Confirm Receipt',
    'orderDetail.viewTracking': 'View Tracking',
    'orderDetail.loadFailed': 'Failed to load',
    'orderDetail.paying': 'Processing...',
    'orderDetail.paySuccess': 'Payment successful',
    'orderDetail.payFailed': 'Payment failed',
    'orderDetail.payCancelled': 'Payment cancelled',
    'orderDetail.cancelTitle': 'Cancel Order',
    'orderDetail.cancelContent': 'Are you sure you want to cancel this order?',
    'orderDetail.cancelled': 'Cancelled',
    'orderDetail.cancelFailed': 'Cancel failed',
    'orderDetail.receiveTitle': 'Confirm Receipt',
    'orderDetail.receiveContent': 'Have you received the goods?',
    'orderDetail.received': 'Received',
    'orderDetail.opFailed': 'Operation failed',

    // ---- Coupon ----
    'coupon.myCoupons': 'My Coupons',
    'coupon.getMore': 'Get More',
    'coupon.noCoupons': 'No coupons yet',
    'coupon.claim': 'Claim',
    'coupon.claiming': 'Claiming...',
    'coupon.claimed': 'Claimed!',
    'coupon.noMinSpend': 'No min spend',
    'coupon.status.unused': 'unused',
    'coupon.status.used': 'used',
    'coupon.status.expired': 'expired',
    'coupon.percentOff': '% Off',
    'coupon.failed': 'Failed',

    // ---- Address ----
    'address.noAddress': 'No addresses saved',
    'address.addAddress': '+ Add Address',
    'address.default': 'Default',
    'address.del': 'Del',
    'address.deleteTitle': 'Delete this address?',
    'address.deleteConfirm': 'Are you sure you want to delete this address?',

    // ---- Address Edit ----
    'addressEdit.fullName': 'Full Name *',
    'addressEdit.phone': 'Phone *',
    'addressEdit.province': 'Province *',
    'addressEdit.city': 'City *',
    'addressEdit.district': 'District *',
    'addressEdit.street': 'Street *',
    'addressEdit.zipCode': 'Zip Code',
    'addressEdit.isDefault': 'Default',
    'addressEdit.save': 'Save Address',
    'addressEdit.update': 'Update Address',
    'addressEdit.fillRequired': 'Fill all required fields',
    'addressEdit.saved': 'Saved',
    'addressEdit.saveFailed': 'Save failed',
    'addressEdit.namePlaceholder': 'Recipient name',
    'addressEdit.phonePlaceholder': 'Phone number',
    'addressEdit.provincePlaceholder': 'Province',
    'addressEdit.cityPlaceholder': 'City',
    'addressEdit.districtPlaceholder': 'District',
    'addressEdit.streetPlaceholder': 'Street address',
    'addressEdit.zipPlaceholder': 'Zip code',

    // ---- Toast ----
    'toast.addedToCart': 'Added to cart',
    'toast.networkError': 'Network error',
    'toast.saved': 'Saved',
    'toast.saveFailed': 'Save failed',
    'toast.fillRequired': 'Fill all required fields',
    'toast.orderPlaced': 'Order placed!',
    'toast.orderFailed': 'Order failed',
    'toast.selectAddress': 'Select address',
    'toast.selectItems': 'Please select items first',
  }
}

/**
 * Get a translated text by key
 * @param {string} key - translation key
 * @param {string} lang - optional language override, defaults to current language
 * @returns {string} translated text
 */
function t(key, lang) {
  lang = lang || getLang()
  var dict = texts[lang] || texts['zh']
  return dict[key] || key
}

/**
 * Get the current language from storage
 * @returns {string} 'zh' or 'en'
 */
function getLang() {
  var lang = wx.getStorageSync('lang')
  if (lang === 'en' || lang === 'zh') {
    return lang
  }
  return 'zh'
}

/**
 * Set and persist the current language
 * @param {string} lang - 'zh' or 'en'
 */
function setLang(lang) {
  if (lang !== 'zh' && lang !== 'en') {
    lang = 'zh'
  }
  wx.setStorageSync('lang', lang)
  var app = getApp()
  if (app) {
    app.globalData.lang = lang
  }
}

/**
 * Refresh all pages in the navigation stack with new language
 */
function refreshAllPages() {
  var pages = getCurrentPages()
  var allTexts = getAllTexts()
  for (var i = 0; i < pages.length; i++) {
    var page = pages[i]
    if (page && page.setData) {
      var updateData = { t: allTexts }
      // If page has a refreshLang handler, call it to get additional updates
      if (typeof page.refreshLang === 'function') {
        var extra = page.refreshLang()
        if (extra) {
          for (var k in extra) {
            if (extra.hasOwnProperty(k)) {
              updateData[k] = extra[k]
            }
          }
        }
      }
      page.setData(updateData)
    }
  }
}

/**
 * Get all translation texts for current or specified language
 * Use this in Page.setData to expose all texts to WXML
 * @param {string} lang - optional language override
 * @returns {object} all translation key-value pairs
 */
function getAllTexts(lang) {
  lang = lang || getLang()
  return texts[lang] || texts['zh']
}

/**
 * Toggle between zh and en
 * @returns {string} new language
 */
function toggleLang() {
  var current = getLang()
  var next = current === 'zh' ? 'en' : 'zh'
  setLang(next)
  refreshAllPages()
  return next
}

module.exports = {
  t: t,
  getLang: getLang,
  setLang: setLang,
  getAllTexts: getAllTexts,
  toggleLang: toggleLang,
  refreshAllPages: refreshAllPages,
}
