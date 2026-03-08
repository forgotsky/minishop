const { skillsData } = require('../data/skills');

const CUSTOM_KEY = 'custom_skill_categories_v1';

function loadCustomCategories() {
  return wx.getStorageSync(CUSTOM_KEY) || [];
}

function saveCustomCategories(items) {
  wx.setStorageSync(CUSTOM_KEY, items || []);
}

function loadAllCategories() {
  const custom = loadCustomCategories();
  return [...custom, ...skillsData];
}

function addCustomCategory(category) {
  if (!category) return;
  const current = loadCustomCategories();
  current.unshift(category);
  saveCustomCategories(current.slice(0, 20));
}

module.exports = {
  loadAllCategories,
  addCustomCategory
};
