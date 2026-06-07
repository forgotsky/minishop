const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')

Page({
  data: {
    id: null,
    full_name: '', phone: '', province: '', city: '', district: '', street: '', zip_code: '', is_default: false,
    t: {}, _theme: ''
  },

  onLoad(options) {
    this.setData({ t: getAllTexts(), _theme: 'theme-' + (getApp().globalData.theme || 'orange') })
    wx.setNavigationBarTitle({ title: t('nav.title.addressEdit') })
    if (options.id) {
      var self = this
      api.getAddresses().then(addresses => {
        var a = addresses.find(x => x.id === parseInt(options.id))
        if (a) self.setData({ id: a.id, ...a })
      })
    }
  },

  onInput(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }) },

  onDefaultChange(e) { this.setData({ is_default: e.detail.value }) },

  onSubmit() {
    var self = this
    var data = self.data
    var full_name = data.full_name
    var phone = data.phone
    var province = data.province
    var city = data.city
    var district = data.district
    var street = data.street
    var zip_code = data.zip_code
    var is_default = data.is_default
    var id = data.id
    if (!full_name || !phone || !province || !city || !district || !street) {
      wx.showToast({ title: t('addressEdit.fillRequired'), icon: 'none' }); return
    }
    var payload = { full_name: full_name, phone: phone, province: province, city: city, district: district, street: street, zip_code: zip_code || null, is_default: is_default }
    var req = id ? api.updateAddress(id, payload) : api.addAddress(payload)
    req.then(() => {
      wx.showToast({ title: t('addressEdit.saved'), icon: 'success' })
      setTimeout(() => wx.navigateBack(), 1000)
    }).catch(err => {
      wx.showToast({ title: (err && err.detail) || t('addressEdit.saveFailed'), icon: 'none' })
    })
  }
})
