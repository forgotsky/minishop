const { api, imageUrl } = require('../../utils/api')
const app = getApp()

Page({
  data: {
    products: [],
    categories: [],
    activeCategory: '',
    search: '',
    page: 1,
    total: 0,
    loading: false
  },

  onShow() {
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
