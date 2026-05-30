const { api } = require('../../utils/api')

Page({
  data: { orders: [], page: 1 },

  onShow() { this.loadOrders() },

  loadOrders() {
    api.getOrders(1).then(data => {
      this.setData({ orders: data })
    })
  },

  onOrderTap(e) {
    wx.navigateTo({ url: '/pages/order-detail/order-detail?id=' + e.currentTarget.dataset.id })
  }
})
