const { api } = require('../../utils/api')

Page({
  data: {
    id: null,
    full_name: '', phone: '', province: '', city: '', district: '', street: '', zip_code: '', is_default: false
  },

  onLoad(options) {
    if (options.id) {
      api.getAddresses().then(addresses => {
        const a = addresses.find(x => x.id === parseInt(options.id))
        if (a) this.setData({ id: a.id, ...a })
      })
    }
  },

  onInput(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }) },

  onDefaultChange(e) { this.setData({ is_default: e.detail.value }) },

  onSubmit() {
    const { id, full_name, phone, province, city, district, street, zip_code, is_default } = this.data
    if (!full_name || !phone || !province || !city || !district || !street) {
      wx.showToast({ title: 'Fill all required fields', icon: 'none' }); return
    }
    const payload = { full_name, phone, province, city, district, street, zip_code: zip_code || null, is_default }
    const req = id ? api.updateAddress(id, payload) : api.addAddress(payload)
    req.then(() => {
      wx.showToast({ title: 'Saved', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    }).catch(err => {
      wx.showToast({ title: err.detail || 'Save failed', icon: 'none' })
    })
  }
})
