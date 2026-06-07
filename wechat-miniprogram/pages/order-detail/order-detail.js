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
    t: {},
    _theme: ''
  },

  onLoad(options) {
    this.setData({ t: getAllTexts(), STATUS_LABELS: getStatusLabels(), _theme: 'theme-' + (getApp().globalData.theme || 'orange') })
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
    wx.showLoading({ title: t('orderDetail.paying') })

    // 调用后端获取微信支付参数
    api.wechatPay(this.data.order.id).then(function (payParams) {
      wx.hideLoading()

      // 调起微信支付
      wx.requestPayment({
        timeStamp: payParams.timeStamp,
        nonceStr: payParams.nonceStr,
        package: payParams.package,
        signType: payParams.signType || 'RSA',
        paySign: payParams.paySign,
        success: function () {
          wx.showToast({ title: t('orderDetail.paySuccess'), icon: 'success' })
          // 刷新订单，显示已支付状态
          setTimeout(function () {
            self.loadOrder(self.data.order.id)
          }, 1200)
        },
        fail: function (payErr) {
          // 用户取消或其他错误
          if (payErr.errMsg && payErr.errMsg.indexOf('cancel') !== -1) {
            wx.showToast({ title: t('orderDetail.payCancelled'), icon: 'none' })
          } else {
            wx.showToast({ title: t('orderDetail.payFailed'), icon: 'none' })
            console.error('WeChat payment failed:', payErr)
          }
        }
      })
    }).catch(function (err) {
      wx.hideLoading()
      // 如果是 prod 模式下 /pay 接口返回的 400，降级使用旧接口
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
