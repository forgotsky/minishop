const { api } = require('../../utils/api')

const STATUS_TABS = ['all', 'pending', 'paid', 'shipped', 'delivered', 'completed', 'cancelled']
const STATUS_LABELS = { all: '全部', pending: '待付款', paid: '待发货', shipped: '待收货', delivered: '已完成', completed: '已完成', cancelled: '已取消' }

Page({
  data: {
    tabs: STATUS_TABS,
    currentTab: 'all',
    STATUS_LABELS: STATUS_LABELS,
    orders: [],
    page: 1,
    hasMore: true,
    loading: false,
  },

  onShow() {
    this.setData({ orders: [], page: 1, hasMore: true })
    this.loadOrders()
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.value
    if (tab === this.data.currentTab) return
    this.setData({ currentTab: tab, orders: [], page: 1, hasMore: true })
    this.loadOrders()
  },

  loadOrders() {
    if (this.data.loading) return
    this.setData({ loading: true })
    const status = this.data.currentTab === 'all' ? null : this.data.currentTab
    api.getOrders(this.data.page, status).then(data => {
      const newOrders = this.data.page === 1 ? data.orders : this.data.orders.concat(data.orders)
      this.setData({
        orders: newOrders,
        hasMore: this.data.page < data.pages,
        loading: false,
      })
    }).catch(() => {
      this.setData({ loading: false })
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
})