const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')

function addStatusLabel(coupons) {
  return coupons.map(function (c) {
    c._statusLabel = t('coupon.status.' + c.status)
    return c
  })
}

Page({
  data: { available: [], myCoupons: [], tab: 'mine', t: {} },

  onShow() {
    this.setData({ t: getAllTexts() })
    this.loadData()
  },

  loadData() {
    var self = this
    api.getAvailableCoupons().then(function (available) {
      self.setData({ available: available })
    }).catch(function (err) {
      console.error('load coupons failed:', err)
    })
    api.getMyCoupons().then(function (myCoupons) {
      self.setData({ myCoupons: addStatusLabel(myCoupons) })
    }).catch(function (err) {
      console.error('load my coupons failed:', err)
    })
  },

  onClaim(e) {
    var id = e.currentTarget.dataset.id
    wx.showLoading({ title: t('coupon.claiming') })
    var self = this
    api.claimCoupon(id).then(function () {
      wx.hideLoading()
      wx.showToast({ title: t('coupon.claimed'), icon: 'success' })
      self.loadData()
    }).catch(function (err) {
      wx.hideLoading()
      var msg = (err && err.detail) ? err.detail : ''
      wx.showToast({ title: msg || t('coupon.failed'), icon: 'none', duration: 3000 })
      console.error('claim failed:', err)
    })
  },

  setTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
  },

  refreshLang() {
    return { myCoupons: addStatusLabel(this.data.myCoupons) }
  },
})
