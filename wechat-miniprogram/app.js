const { api } = require('./utils/api')

App({
  onLaunch() {
    this.autoLogin()
  },

  autoLogin() {
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.loggedIn = true
      return
    }
    wx.login({
      success: (res) => {
        if (res.code) {
          api.login(res.code, '', '').then(data => {
            wx.setStorageSync('token', data.token)
            this.globalData.loggedIn = true
            this.globalData.userId = data.user_id
          }).catch(() => {
            this.devLogin()
          })
        } else {
          this.devLogin()
        }
      },
      fail: () => this.devLogin()
    })
  },

  devLogin() {
    api.login('dev_' + Date.now(), 'DevUser', '').then(data => {
      wx.setStorageSync('token', data.token)
      this.globalData.loggedIn = true
      this.globalData.userId = data.user_id
    })
  },

  refreshCartCount() {
    if (!this.globalData.loggedIn) return
    api.getCart().then(data => {
      const count = data.items.reduce((s, i) => s + i.quantity, 0)
      this.globalData.cartCount = count
      if (count > 0) {
        wx.setTabBarBadge({ index: 1, text: String(count) })
      } else {
        wx.removeTabBarBadge({ index: 1 })
      }
    }).catch(() => {})
  },

  globalData: {
    loggedIn: false,
    userId: null,
    cartCount: 0
  }
})
