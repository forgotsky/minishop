const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')
const app = getApp()

function couponDiscount(coupon, subtotal) {
  if (!coupon || subtotal < coupon.template.threshold) return 0
  if (coupon.template.type === 'full_reduction') return coupon.template.value
  return Math.round(subtotal * (1 - coupon.template.value / 100) * 100) / 100
}

function bestCoupon(coupons, subtotal) {
  let best = null, bestDiscount = 0
  for (const c of coupons) {
    const d = couponDiscount(c, subtotal)
    if (d > bestDiscount) { bestDiscount = d; best = c }
  }
  return best
}

Page({
  data: {
    addresses: [], selectedAddress: null,
    coupons: [], selectedCoupon: null, couponIndex: 0,
    items: [], subtotal: 0, delivery: 5, discount: 0, total: 0,
    t: {}, _theme: ''
  },

  goAddAddress() {
    wx.navigateTo({ url: '/pages/address-edit/address-edit' })
  },

  onShow() { this.setData({ t: getAllTexts(), _theme: 'theme-' + (app.globalData.theme || 'orange') }); this.loadData() },

  loadData() {
    const checkedIds = new Set(app.globalData.checkoutItemIds || [])
    Promise.all([api.getCart(), api.getAddresses(), api.getMyCoupons()]).then(([cart, addresses, coupons]) => {
      const selectedAddress = addresses.find(a => a.is_default) || addresses[0] || null
      const available = coupons.filter(c => c.status === 'unused')
      const items = cart.items.filter(i => checkedIds.has(i.id))
      const subtotal = Math.round(items.reduce((sum, i) => sum + i.subtotal, 0) * 100) / 100
      const selectedCoupon = bestCoupon(available, subtotal)
      const couponIndex = selectedCoupon ? available.indexOf(selectedCoupon) : 0
      this.setData({
        items, subtotal,
        addresses, selectedAddress,
        coupons: available, selectedCoupon, couponIndex,
      }, () => this.calcTotal())
    })
  },

  calcTotal() {
    const discount = couponDiscount(this.data.selectedCoupon, this.data.subtotal)
    const total = Math.round((this.data.subtotal - discount + this.data.delivery) * 100) / 100
    this.setData({ discount, total })
  },

  onSelectAddress(e) {
    const id = parseInt(e.detail.value)
    this.setData({ selectedAddress: this.data.addresses.find(a => a.id === id) }, () => this.calcTotal())
  },

  onSelectCoupon(e) {
    const idx = parseInt(e.detail.value)
    this.setData({
      couponIndex: idx,
      selectedCoupon: idx >= 0 ? this.data.coupons[idx] : null
    }, () => this.calcTotal())
  },

  onPlaceOrder() {
    if (!this.data.selectedAddress) {
      wx.showToast({ title: t('checkout.selectAddress'), icon: 'none' }); return
    }
    var self = this
    var itemIds = this.data.items.map(function (i) { return i.id })
    api.createOrder(self.data.selectedAddress.id, (self.data.selectedCoupon || {}).id, 'wechat', null, itemIds).then(function (order) {
      wx.showToast({ title: t('checkout.orderPlaced'), icon: 'success' })
      // 跳转到订单详情页，用户在那里进行微信支付
      setTimeout(function () {
        wx.redirectTo({ url: '/pages/order-detail/order-detail?id=' + order.id })
      }, 1000)
    }).catch(function (err) {
      wx.showToast({ title: (err && err.detail) || t('checkout.failed'), icon: 'none' })
    })
  }
})
