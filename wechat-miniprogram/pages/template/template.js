const { generateSkillTemplate } = require('../../data/template-generator');
const { addCustomCategory } = require('../../utils/categories');

Page({
  data: {
    subjectInput: '英语',
    generated: null
  },

  onInput(e) {
    this.setData({
      subjectInput: e.detail.value
    });
  },

  generateTemplate() {
    const { subjectInput } = this.data;
    const generated = generateSkillTemplate(subjectInput || '通用学科');
    this.setData({ generated });
  },

  useTemplate() {
    const { generated } = this.data;
    if (!generated) {
      wx.showToast({ title: '请先生成模板', icon: 'none' });
      return;
    }

    addCustomCategory(generated);
    const firstSkill = generated.topSkills[0];
    wx.navigateTo({
      url: `/pages/skill/skill?categoryId=${generated.categoryId}&skillId=${firstSkill.skillId}`
    });
  }
});
