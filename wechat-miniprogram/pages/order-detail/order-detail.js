const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')

function getStatusLabels() {
  return {
    pending: t('orderDetail.status.pending'),
    paid: t('orderDetail.status.paid'),
    shipped: t('orderDetail.status.shipped'),
    delivered: t('orderDetail.status.delivered'),
    completed: t('orderDetail.status.completed'),
    cancelled: t('orderDetail.status.cancelled')
  }
}

Page({
  data: {
    order: null,
    STATUS_LABELS: {},
    t: {}
  },

  onLoad(options) {
    this.setData({ t: getAllTexts(), STATUS_LABELS: getStatusLabels() })
    this.loadOrder(options.id)
  },

  loadOrder(id) {
    var self = this
    api.getOrder(id).then(order => {
      self.setData({ order })
    }).catch(() => {
      wx.showToast({ title: t('orderDetail.loadFailed'), icon: 'none' })
    })
  },

  onPay() {
    var self = this
    api.payOrder(this.data.order.id).then(() => {
      wx.showToast({ title: t('orderDetail.paySuccess'), icon: 'success' })
      self.loadOrder(self.data.order.id)
    }).catch(err => {
      wx.showToast({ title: (err && err.detail) || t('orderDetail.payFailed'), icon: 'none' })
    })
  },

  onCancel() {
    var self = this
    wx.showModal({
      title: t('orderDetail.cancelTitle'),
      content: t('orderDetail.cancelContent'),
      success: res => {
        if (!res.confirm) return
        api.updateOrderStatus(self.data.order.id, 'cancel').then(() => {
          wx.showToast({ title: t('orderDetail.cancelled'), icon: 'success' })
          self.loadOrder(self.data.order.id)
        }).catch(err => {
          wx.showToast({ title: (err && err.detail) || t('orderDetail.cancelFailed'), icon: 'none' })
        })
      }
    })
  },

  onConfirmReceive() {
    var self = this
    wx.showModal({
      title: t('orderDetail.receiveTitle'),
      content: t('orderDetail.receiveContent'),
      success: res => {
        if (!res.confirm) return
        api.updateOrderStatus(self.data.order.id, 'complete').then(() => {
          wx.showToast({ title: t('orderDetail.received'), icon: 'success' })
          self.loadOrder(self.data.order.id)
        }).catch(err => {
          wx.showToast({ title: (err && err.detail) || t('orderDetail.opFailed'), icon: 'none' })
        })
      }
    })
  },

  onViewTracking() {
    var order = this.data.order
    if (!order.tracking) {
      wx.showToast({ title: t('orderDetail.trackingNoInfo'), icon: 'none' })
      return
    }
    wx.showModal({
      title: t('orderDetail.tracking'),
      content: t('orderDetail.courier') + ((order.tracking.company) || t('orderDetail.unknown')) + '\n' + t('orderDetail.trackingNo') + ((order.tracking.number) || t('orderDetail.unknown')),
      showCancel: false,
    })
  },

  refreshLang() {
    return { STATUS_LABELS: getStatusLabels() }
  },
})
