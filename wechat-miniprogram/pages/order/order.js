const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')

const STATUS_TABS = ['all', 'pending', 'paid', 'shipped', 'delivered', 'completed', 'cancelled']

function getStatusLabels() {
  return {
    all: t('order.tab.all'),
    pending: t('order.tab.pending'),
    paid: t('order.tab.paid'),
    shipped: t('order.tab.shipped'),
    delivered: t('order.tab.delivered'),
    completed: t('order.tab.completed'),
    cancelled: t('order.tab.cancelled')
  }
}

Page({
  data: {
    tabs: STATUS_TABS,
    currentTab: 'all',
    STATUS_LABELS: {},
    orders: [],
    page: 1,
    hasMore: true,
    loading: false,
    t: {}
  },

  onShow() {
    this.setData({ t: getAllTexts(), STATUS_LABELS: getStatusLabels() })
    this.setData({ orders: [], page: 1, hasMore: true })
    this.loadOrders()
  },

  onTabTap(e) {
    var tab = e.currentTarget.dataset.value
    if (tab === this.data.currentTab) return
    this.setData({ currentTab: tab, orders: [], page: 1, hasMore: true })
    this.loadOrders()
  },

  loadOrders() {
    if (this.data.loading) return
    this.setData({ loading: true })
    var status = this.data.currentTab === 'all' ? null : this.data.currentTab
    var self = this
    api.getOrders(this.data.page, status).then(data => {
      var newOrders = self.data.page === 1 ? data.orders : self.data.orders.concat(data.orders)
      // Add computed i18n labels
      var itemCountTemplate = t('order.itemCount')
      newOrders.forEach(function (o) {
        o._itemCountText = itemCountTemplate.replace('{itemCount}', o.items_count)
      })
      self.setData({
        orders: newOrders,
        hasMore: self.data.page < data.pages,
        loading: false,
      })
    }).catch(() => {
      self.setData({ loading: false })
    })
  },

  onReachBottom() {
    if (!this.data.hasMore) return
    this.setData({ page: this.data.page + 1 })
    this.loadOrders()
  },

  onOrderTap(e) {
    wx.navigateTo({ url: '/pages/order-detail/order-detail?id=' + e.currentTarget.dataset.id })
  },

  refreshLang() {
    var itemCountTemplate = t('order.itemCount')
    var refreshedOrders = this.data.orders.map(function (o) {
      o._itemCountText = itemCountTemplate.replace('{itemCount}', o.items_count)
      return o
    })
    return { STATUS_LABELS: getStatusLabels(), orders: refreshedOrders }
  },
})
