const { api, imageUrl } = require('../../utils/api')
const app = getApp()

Page({
  data: { product: null },
  onLoad(options) {
    api.getProduct(options.id).then(product => {
      product.image_url = imageUrl(product.image_url)
      this.setData({ product })
    })
  },
  addToCart() {
    const p = this.data.product
    if (!p) return
    api.addToCart(p.id, 1).then(() => {
      wx.showToast({ title: 'Added to cart', icon: 'success' })
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
