const { api, imageUrl } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')
const app = getApp()

Page({
  data: { product: null, t: {}, _theme: '' },
  onLoad(options) {
    this._productId = options.id
    this.setData({ t: getAllTexts(), _theme: 'theme-' + (app.globalData.theme || 'orange') })
    wx.setNavigationBarTitle({ title: t('nav.title.product') })
    this._loadProduct()
  },
  _loadProduct() {
    if (!this._productId) return
    var self = this
    api.getProduct(this._productId).then(function (product) {
      product.image_url = imageUrl(product.image_url)
      self.setData({ product: product })
    })
  },
  refreshLang() {
    this._loadProduct()
    return {}
  },
  addToCart() {
    const p = this.data.product
    if (!p) return
    api.addToCart(p.id, 1).then(() => {
      wx.showToast({ title: t('toast.addedToCart'), icon: 'success' })
      app.refreshCartCount()
    })
  },
  buyNow() {
    const p = this.data.product
    if (!p) return
    api.addToCart(p.id, 1).then(() => {
      app.refreshCartCount()
      wx.switchTab({ url: '/pages/cart/cart' })
    })
  }
})
