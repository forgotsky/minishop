const { api, imageUrl } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')
const app = getApp()

Page({
  data: { items: [], total: 0, selectedTotal: 0, allChecked: false, t: {}, _theme: '' },

  onShow() {
    this.setData({ t: getAllTexts(), _theme: 'theme-' + (app.globalData.theme || 'orange') })
    this.loadCart()
  },

  loadCart() {
    api.getCart().then(data => {
      const prevChecked = new Set(this.data.items.filter(i => i._checked).map(i => i.id))
      const items = data.items.map(i => ({
        ...i,
        product_image: imageUrl(i.product_image),
        _checked: prevChecked.has(i.id)
      }))
      this.setData({ items, total: data.total, ...this.calcSelected(items) })
      app.refreshCartCount()
    })
  },

  calcSelected(items) {
    let selectedTotal = 0
    let allChecked = items.length > 0
    for (const i of items) {
      if (i._checked) {
        selectedTotal += i.subtotal
      } else {
        allChecked = false
      }
    }
    return { selectedTotal: Math.round(selectedTotal * 100) / 100, allChecked }
  },

  onToggleItem(e) {
    const id = Number(e.currentTarget.dataset.id)
    const items = this.data.items.map(i => {
      if (i.id === id) i._checked = !i._checked
      return i
    })
    this.setData({ items, ...this.calcSelected(items) })
  },

  onToggleAll() {
    const next = !this.data.allChecked
    const items = this.data.items.map(i => ({ ...i, _checked: next }))
    this.setData({ items, ...this.calcSelected(items) })
  },

  onQtyChange(e) {
    const qty = parseInt(e.currentTarget.dataset.qty)
    if (qty < 1) return
    api.updateCartItem(e.currentTarget.dataset.id, qty).then(() => this.loadCart())
  },

  onRemove(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: t('cart.removeTitle'),
      success: (res) => {
        if (res.confirm) api.removeCartItem(id).then(() => this.loadCart())
      }
    })
  },

  onCheckout() {
    const checked = this.data.items.filter(i => i._checked)
    if (!checked.length) {
      wx.showToast({ title: t('cart.selectFirst'), icon: 'none' })
      return
    }
    app.globalData.checkoutItemIds = checked.map(i => i.id)
    wx.navigateTo({ url: '/pages/checkout/checkout' })
  }
})
