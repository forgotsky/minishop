import { skillsData } from '../data/skills';

const CUSTOM_KEY = 'custom_skill_categories_v1';

export function loadCustomCategories() {
  return uni.getStorageSync(CUSTOM_KEY) || [];
}

export function saveCustomCategories(items) {
  uni.setStorageSync(CUSTOM_KEY, items || []);
}

export function mergeCategories(baseCategories) {
  const custom = loadCustomCategories();
  if (Array.isArray(baseCategories) && baseCategories.length > 0) {
    return [...custom, ...baseCategories];
  }
  return [...custom, ...skillsData];
}

export function addCustomCategory(category) {
  if (!category) return;
  const current = loadCustomCategories();
  current.unshift(category);
  saveCustomCategories(current.slice(0, 20));
}
