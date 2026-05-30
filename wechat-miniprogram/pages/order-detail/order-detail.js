const { api } = require('../../utils/api')

Page({
  data: { order: null },

  onLoad(options) {
    api.getOrder(options.id).then(order => {
      this.setData({ order })
    })
  },

  onPay() {
    api.payOrder(this.data.order.id).then(() => {
      wx.showToast({ title: 'Paid!', icon: 'success' })
      this.onLoad({ id: this.data.order.id })
    })
  }
})
