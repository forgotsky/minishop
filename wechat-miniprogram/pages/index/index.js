const { loadAllCategories } = require('../../utils/categories');

Page({
  data: {
    categories: []
  },

  onShow() {
    this.setData({
      categories: loadAllCategories()
    });
  },

  goToSkill(e) {
    const { categoryId, skillId } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/skill/skill?categoryId=${categoryId}&skillId=${skillId}`
    });
  },

  goToTemplate() {
    wx.navigateTo({
      url: '/pages/template/template'
    });
  }
});
