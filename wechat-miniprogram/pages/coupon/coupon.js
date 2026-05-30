const { api } = require('../../utils/api')

Page({
  data: { available: [], myCoupons: [], tab: 'mine' },

  onShow() { this.loadData() },

  loadData() {
    Promise.all([api.getAvailableCoupons(), api.getMyCoupons()]).then(([available, myCoupons]) => {
      this.setData({ available, myCoupons })
    })
  },

  onClaim(e) {
    api.claimCoupon(e.currentTarget.dataset.id).then(() => {
      wx.showToast({ title: 'Claimed!', icon: 'success' })
      this.loadData()
    }).catch(err => {
      wx.showToast({ title: err.detail || 'Failed', icon: 'none' })
    })
  },

  setTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
  }
})
