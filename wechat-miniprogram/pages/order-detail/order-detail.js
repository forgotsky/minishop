const { api } = require('../../utils/api')

const STATUS_LABELS = {
  pending: '待付款', paid: '待发货', shipped: '待收货',
  delivered: '待收货', completed: '已完成', cancelled: '已取消'
}

Page({
  data: {
    order: null,
    STATUS_LABELS: STATUS_LABELS,
  },

  onLoad(options) {
    this.loadOrder(options.id)
  },

  loadOrder(id) {
    api.getOrder(id).then(order => {
      this.setData({ order })
    }).catch(() => {
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  },

  onPay() {
    api.payOrder(this.data.order.id).then(() => {
      wx.showToast({ title: '支付成功', icon: 'success' })
      this.loadOrder(this.data.order.id)
    }).catch(err => {
      wx.showToast({ title: (err.detail || '支付失败'), icon: 'none' })
    })
  },

  onCancel() {
    wx.showModal({
      title: '确认取消',
      content: '确定要取消此订单吗？',
      success: res => {
        if (!res.confirm) return
        api.updateOrderStatus(this.data.order.id, 'cancel').then(() => {
          wx.showToast({ title: '已取消', icon: 'success' })
          this.loadOrder(this.data.order.id)
        }).catch(err => {
          wx.showToast({ title: (err.detail || '取消失败'), icon: 'none' })
        })
      }
    })
  },

  onConfirmReceive() {
    wx.showModal({
      title: '确认收货',
      content: '确认已收到货物？',
      success: res => {
        if (!res.confirm) return
        api.updateOrderStatus(this.data.order.id, 'complete').then(() => {
          wx.showToast({ title: '已确认收货', icon: 'success' })
          this.loadOrder(this.data.order.id)
        }).catch(err => {
          wx.showToast({ title: (err.detail || '操作失败'), icon: 'none' })
        })
      }
    })
  },

  onViewTracking() {
    const order = this.data.order
    if (!order.tracking) {
      wx.showToast({ title: '暂无物流信息', icon: 'none' })
      return
    }
    wx.showModal({
      title: '物流信息',
      content: '快递公司：' + (order.tracking.company || '未知') + '\n运单号：' + (order.tracking.number || '未知'),
      showCancel: false,
    })
  },
})