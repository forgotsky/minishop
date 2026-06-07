const BASE_URL = 'https://renewshuttle.cn'
const { t, getLang } = require('./i18n')

const handle401 = () => {
  wx.removeStorageSync('token')
  const app = getApp()
  if (app) {
    app.globalData.loggedIn = false
    app.devLogin()
  }
}

const request = (method, path, data, needAuth) => {
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    // 传递语言偏好给后端
    var lang = getLang()
    header['Accept-Language'] = lang === 'zh' ? 'zh-CN' : 'en'
    if (needAuth !== false) {
      const token = wx.getStorageSync('token')
      if (token) header['Authorization'] = 'Bearer ' + token
    }
    wx.request({
      url: BASE_URL + path,
      method: method,
      data: data || {},
      header: header,
      timeout: 10000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          if (res.statusCode === 401) handle401()
          reject(res.data)
        }
      },
      fail(err) {
        wx.showToast({ title: t('toast.networkError'), icon: 'none' })
        reject(err)
      }
    })
  })
}

const api = {
  // Auth
  login: (code, nickname, avatar) =>
    request('POST', '/api/auth/login', { code, nickname, avatar }, false),

  // Products
  getProducts: (params) => {
    const qs = []
    if (params) {
      if (params.category) qs.push('category=' + encodeURIComponent(params.category))
      if (params.search) qs.push('search=' + encodeURIComponent(params.search))
      if (params.page) qs.push('page=' + params.page)
      if (params.page_size) qs.push('page_size=' + params.page_size)
    }
    return request('GET', '/api/products' + (qs.length ? '?' + qs.join('&') : ''))
  },
  getProduct: (id) => request('GET', '/api/products/' + id),
  getCategories: () => request('GET', '/api/categories'),

  // Cart
  getCart: () => request('GET', '/api/cart'),
  addToCart: (productId, quantity) => request('POST', '/api/cart/items', { product_id: productId, quantity }),
  updateCartItem: (itemId, quantity) => request('PUT', '/api/cart/items/' + itemId + '?quantity=' + quantity),
  removeCartItem: (itemId) => request('DELETE', '/api/cart/items/' + itemId),
  clearCart: () => request('DELETE', '/api/cart'),

  // Orders
  createOrder: (addressId, couponId, paymentMethod, remark, itemIds) =>
    request('POST', '/api/orders', { address_id: addressId, coupon_id: couponId || null, payment_method: paymentMethod || 'wechat', remark, item_ids: itemIds }),
  getOrders: (page, status) => {
    let path = '/api/orders?page=' + (page || 1)
    if (status) path += '&status=' + status
    return request('GET', path)
  },
  getOrder: (id) => request('GET', '/api/orders/' + id),
  payOrder: (id) => request('POST', '/api/orders/' + id + '/pay'),
  wechatPay: (id) => request('POST', '/api/orders/' + id + '/wechat-pay'),
  updateOrderStatus: (id, action) => request('PATCH', '/api/orders/' + id + '/status', { action }),
  getOrderTracking: (id) => request('GET', '/api/orders/' + id + '/tracking'),

  // Addresses
  getAddresses: () => request('GET', '/api/addresses'),
  addAddress: (data) => request('POST', '/api/addresses', data),
  updateAddress: (id, data) => request('PUT', '/api/addresses/' + id, data),
  deleteAddress: (id) => request('DELETE', '/api/addresses/' + id),

  // Coupons
  getAvailableCoupons: () => request('GET', '/api/coupons'),
  claimCoupon: (templateId) => request('POST', '/api/coupons/' + templateId + '/claim'),
  getMyCoupons: () => request('GET', '/api/user/coupons'),

  // Profile
  getProfile: () => request('GET', '/api/user/profile'),
  updateProfile: (data) => request('PUT', '/api/user/profile', data),

  // Account
  deleteAccount: () => request('DELETE', '/api/user/account'),
}

const imageUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return BASE_URL + path
}

module.exports = { BASE_URL, imageUrl, api }
