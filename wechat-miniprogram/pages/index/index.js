const { api, imageUrl } = require('../../utils/api')
const { getAllTexts, toggleLang, t } = require('../../utils/i18n')
const app = getApp()

Page({
  data: {
    products: [],
    categories: [],
    activeCategory: '',
    search: '',
    page: 1,
    total: 0,
    loading: false,
    t: {},
    _theme: ''
  },

  onShow() {
    this.setData({ t: getAllTexts(), _theme: 'theme-' + (app.globalData.theme || 'orange') })
    wx.setNavigationBarTitle({ title: t('nav.title.shop') })
    this.loadCategories()
    this.loadProducts()
    app.refreshCartCount()
  },

  loadCategories() {
    api.getCategories().then(data => {
      this.setData({ categories: data.categories })
    })
  },

  loadProducts() {
    this.setData({ loading: true })
    const params = { page: this.data.page }
    if (this.data.activeCategory) params.category = this.data.activeCategory
    if (this.data.search) params.search = this.data.search
    api.getProducts(params).then(data => {
      data.products = data.products.map(p => ({ ...p, image_url: imageUrl(p.image_url) }))
      this.setData({ products: data.products, total: data.total, loading: false })
    })
  },

  onCategoryTap(e) {
    const cat = e.currentTarget.dataset.category
    this.setData({ activeCategory: cat === this.data.activeCategory ? '' : cat, page: 1 }, () => this.loadProducts())
  },

  onSearchInput(e) { this.setData({ search: e.detail.value }) },

  onSearch() { this.setData({ page: 1 }, () => this.loadProducts()) },

  onProductTap(e) {
    wx.navigateTo({ url: '/pages/product/product?id=' + e.currentTarget.dataset.id })
  },

  onSwitchLang() {
    toggleLang()
  },

  onSwitchTheme() {
    app.cycleTheme()
    this.setData({ _theme: 'theme-' + (app.globalData.theme || 'orange') })
  },

  onLoadMore() {
    if (this.data.products.length >= this.data.total) return
    this.setData({ page: this.data.page + 1 }, () => {
      const params = { page: this.data.page }
      if (this.data.activeCategory) params.category = this.data.activeCategory
      if (this.data.search) params.search = this.data.search
      api.getProducts(params).then(data => {
        data.products = data.products.map(p => ({ ...p, image_url: imageUrl(p.image_url) }))
        this.setData({ products: [...this.data.products, ...data.products] })
      })
    })
  }
})
