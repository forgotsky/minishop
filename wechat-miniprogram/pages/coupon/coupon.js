const { api } = require('../../utils/api')

Page({
  data: { available: [], myCoupons: [], tab: 'mine' },

  onShow() { this.loadData() },

  loadData() {
    api.getAvailableCoupons().then(available => {
      this.setData({ available })
    }).catch(err => {
      console.error('load coupons failed:', err)
    })
    api.getMyCoupons().then(myCoupons => {
      this.setData({ myCoupons })
    }).catch(err => {
      console.error('load my coupons failed:', err)
    })
  },

  onClaim(e) {
    const id = e.currentTarget.dataset.id
    wx.showLoading({ title: 'Claiming...' })
    api.claimCoupon(id).then(() => {
      wx.hideLoading()
      wx.showToast({ title: 'Claimed!', icon: 'success' })
      this.loadData()
    }).catch(err => {
      wx.hideLoading()
      const msg = (err && err.detail) ? err.detail : JSON.stringify(err)
      wx.showToast({ title: msg || 'Failed', icon: 'none', duration: 3000 })
      console.error('claim failed:', err)
    })
  },

  setTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
  }
})
