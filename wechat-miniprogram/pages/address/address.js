const { api } = require('../../utils/api')
const { t, getAllTexts } = require('../../utils/i18n')

Page({
  data: { addresses: [], t: {} },

  onShow() {
    this.setData({ t: getAllTexts() })
    var self = this
    api.getAddresses().then(data => {
      self.setData({ addresses: data })
    })
  },

  onAdd() {
    wx.navigateTo({ url: '/pages/address-edit/address-edit' })
  },

  onEdit(e) {
    wx.navigateTo({ url: '/pages/address-edit/address-edit?id=' + e.currentTarget.dataset.id })
  },

  onDelete(e) {
    var id = e.currentTarget.dataset.id
    var self = this
    wx.showModal({
      title: t('address.deleteTitle'),
      success: (res) => {
        if (res.confirm) {
          api.deleteAddress(id).then(() => self.onShow())
        }
      }
    })
  }
})
