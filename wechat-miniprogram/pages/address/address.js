const { api } = require('../../utils/api')

Page({
  data: { addresses: [] },

  onShow() {
    api.getAddresses().then(data => {
      this.setData({ addresses: data })
    })
  },

  onAdd() {
    wx.navigateTo({ url: '/pages/address-edit/address-edit' })
  },

  onEdit(e) {
    wx.navigateTo({ url: '/pages/address-edit/address-edit?id=' + e.currentTarget.dataset.id })
  },

  onDelete(e) {
    wx.showModal({
      title: 'Delete this address?',
      success: (res) => {
        if (res.confirm) {
          api.deleteAddress(e.currentTarget.dataset.id).then(() => this.onShow())
        }
      }
    })
  }
})
