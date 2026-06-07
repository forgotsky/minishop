const { api } = require('./utils/api')
const { getLang, setLang } = require('./utils/i18n')

var THEMES = ['orange', 'blue', 'green', 'dark']

var THEME_CONFIG = {
  orange: {
    navbarBg: '#ff5500',
    navbarText: 'white',
    tabBarColor: '#999999',
    tabBarSelectedColor: '#ff5500',
  },
  blue: {
    navbarBg: '#1989fa',
    navbarText: 'white',
    tabBarColor: '#999999',
    tabBarSelectedColor: '#1989fa',
  },
  green: {
    navbarBg: '#07c160',
    navbarText: 'white',
    tabBarColor: '#999999',
    tabBarSelectedColor: '#07c160',
  },
  dark: {
    navbarBg: '#1a1a2e',
    navbarText: 'white',
    tabBarColor: '#777777',
    tabBarSelectedColor: '#d4a853',
  },
}

function getTheme() {
  var theme = wx.getStorageSync('theme')
  if (THEME_CONFIG[theme]) return theme
  return 'orange'
}

function getThemeClass(theme) {
  return 'theme-' + theme
}

function nextTheme(current) {
  var idx = THEMES.indexOf(current)
  if (idx < 0) idx = 0
  return THEMES[(idx + 1) % THEMES.length]
}

App({
  onLaunch() {
    // Init language
    this.globalData.lang = getLang()
    // Init theme
    this.globalData.theme = getTheme()
    this.autoLogin()
  },

  /** Switch app language */
  setAppLang(lang) {
    setLang(lang)
    this.globalData.lang = lang
  },

  /** Apply theme to navbar + tabBar + all open pages */
  applyTheme(theme) {
    if (!THEME_CONFIG[theme]) theme = 'orange'
    var config = THEME_CONFIG[theme]
    var themeClass = getThemeClass(theme)

    // Navbar
    wx.setNavigationBarColor({
      frontColor: config.navbarText === 'white' ? '#ffffff' : '#000000',
      backgroundColor: config.navbarBg,
    })

    // TabBar
    wx.setTabBarStyle({
      color: config.tabBarColor,
      selectedColor: config.tabBarSelectedColor,
    })

    // Persist
    wx.setStorageSync('theme', theme)
    this.globalData.theme = theme

    // Refresh all open pages
    var pages = getCurrentPages()
    for (var i = 0; i < pages.length; i++) {
      var page = pages[i]
      if (page && page.setData) {
        page.setData({ _theme: themeClass })
      }
    }
  },

  /** Cycle to next theme */
  cycleTheme() {
    var current = this.globalData.theme || 'orange'
    var next = nextTheme(current)
    this.applyTheme(next)
  },

  /** Get theme class for WXML root view */
  getThemeClassForPage() {
    return getThemeClass(this.globalData.theme || 'orange')
  },

  autoLogin() {
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
    cartCount: 0,
    theme: 'orange',
  }
})
