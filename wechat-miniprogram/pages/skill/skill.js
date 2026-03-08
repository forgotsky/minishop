const { loadAllCategories } = require('../../utils/categories');
const {
  buildWeeklyPlan,
  savePlan,
  loadPlan,
  saveProgress,
  loadProgress,
  computeProgress
} = require('../../utils/learning');

const LAST_PLAN_KEY = 'last_plan_by_skill_v1';

function getFallback(categories) {
  const category = categories[0];
  const skill = category.topSkills[0];
  return { category, skill };
}

function findCategory(categories, categoryId) {
  return categories.find((item) => item.categoryId === categoryId) || null;
}

function findSkill(category, skillId) {
  if (!category) return null;
  return category.topSkills.find((item) => item.skillId === skillId) || null;
}

function buildPlanView(plan, progressMap) {
  if (!plan) return null;
  const schedule = (plan.schedule || []).map((dayBlock) => ({
    ...dayBlock,
    tasks: (dayBlock.tasks || []).map((task) => ({
      ...task,
      done: Boolean(progressMap[task.id])
    }))
  }));
  return {
    ...plan,
    schedule
  };
}

function getSkillKey(categoryId, skillId) {
  return `${categoryId}__${skillId}`;
}

function readLastPlanMap() {
  return wx.getStorageSync(LAST_PLAN_KEY) || {};
}

function writeLastPlanMap(data) {
  wx.setStorageSync(LAST_PLAN_KEY, data || {});
}

Page({
  data: {
    categories: [],
    categoryIndex: 0,
    activeCategoryId: '',
    activeSkillId: '',
    activeCategory: null,
    activeSkill: null,
    l1Mode: 'hour',
    dailyMinutes: 40,
    daysPerWeek: 5,
    plan: null,
    planView: null,
    progressMap: {},
    progressStats: { done: 0, total: 0, rate: 0 }
  },

  onLoad(options) {
    const categories = loadAllCategories();
    const fallback = getFallback(categories);
    const categoryId = options.categoryId || fallback.category.categoryId;
    const category = findCategory(categories, categoryId) || fallback.category;
    const skillId = options.skillId || category.topSkills[0].skillId;
    const skill = findSkill(category, skillId) || category.topSkills[0];
    const categoryIndex = categories.findIndex((item) => item.categoryId === category.categoryId);

    this.setData({
      categories,
      categoryIndex: categoryIndex < 0 ? 0 : categoryIndex,
      activeCategoryId: category.categoryId,
      activeSkillId: skill.skillId,
      activeCategory: category,
      activeSkill: skill
    });

    this.restorePlan(category.categoryId, skill.skillId);
  },

  onShow() {
    const categories = loadAllCategories();
    const { activeCategoryId, activeSkillId } = this.data;
    const fallback = getFallback(categories);
    const category = findCategory(categories, activeCategoryId) || fallback.category;
    const skill = findSkill(category, activeSkillId) || category.topSkills[0];
    const categoryIndex = categories.findIndex((item) => item.categoryId === category.categoryId);

    this.setData({
      categories,
      categoryIndex: categoryIndex < 0 ? 0 : categoryIndex,
      activeCategoryId: category.categoryId,
      activeSkillId: skill.skillId,
      activeCategory: category,
      activeSkill: skill
    });
  },

  restorePlan(categoryId, skillId) {
    const lastPlanMap = readLastPlanMap();
    const skillKey = getSkillKey(categoryId, skillId);
    const lastPlanId = lastPlanMap[skillKey];
    if (!lastPlanId) {
      this.setData({
        plan: null,
        planView: null,
        progressMap: {},
        progressStats: { done: 0, total: 0, rate: 0 }
      });
      return;
    }

    const plan = loadPlan(lastPlanId);
    if (!plan) return;
    const progressMap = loadProgress(lastPlanId);
    const progressStats = computeProgress(plan, progressMap);

    this.setData({
      dailyMinutes: plan.dailyMinutes,
      daysPerWeek: plan.daysPerWeek,
      plan,
      planView: buildPlanView(plan, progressMap),
      progressMap,
      progressStats
    });
  },

  onCategoryChange(e) {
    const categoryIndex = Number(e.detail.value || 0);
    const { categories } = this.data;
    const category = categories[categoryIndex];
    if (!category) return;
    const skill = category.topSkills[0];

    this.setData({
      categoryIndex,
      activeCategoryId: category.categoryId,
      activeSkillId: skill.skillId,
      activeCategory: category,
      activeSkill: skill,
      l1Mode: 'hour'
    });

    this.restorePlan(category.categoryId, skill.skillId);
  },

  onSkillChange(e) {
    const skillId = e.currentTarget.dataset.skillId;
    const { activeCategory } = this.data;
    const skill = findSkill(activeCategory, skillId);
    if (!skill) return;

    this.setData({
      activeSkillId: skillId,
      activeSkill: skill,
      l1Mode: 'hour'
    });

    this.restorePlan(activeCategory.categoryId, skillId);
  },

  onModeChange(e) {
    this.setData({
      l1Mode: e.currentTarget.dataset.mode
    });
  },

  onDailyMinutesInput(e) {
    this.setData({ dailyMinutes: e.detail.value });
  },

  onDaysPerWeekInput(e) {
    this.setData({ daysPerWeek: e.detail.value });
  },

  generatePlan() {
    const { activeCategoryId, activeSkillId, activeSkill, dailyMinutes, daysPerWeek } = this.data;
    const l1 = activeSkill.levels && activeSkill.levels[0];
    if (!l1 || !l1.microSplit || !l1.microSplit.hourTasks) {
      wx.showToast({ title: '该技能暂无L1切分', icon: 'none' });
      return;
    }

    const plan = buildWeeklyPlan(l1.microSplit.hourTasks, dailyMinutes, daysPerWeek);
    savePlan(plan);

    const lastPlanMap = readLastPlanMap();
    lastPlanMap[getSkillKey(activeCategoryId, activeSkillId)] = plan.planId;
    writeLastPlanMap(lastPlanMap);

    const progressMap = {};
    saveProgress(plan.planId, progressMap);
    const progressStats = computeProgress(plan, progressMap);

    this.setData({
      dailyMinutes: plan.dailyMinutes,
      daysPerWeek: plan.daysPerWeek,
      plan,
      planView: buildPlanView(plan, progressMap),
      progressMap,
      progressStats
    });
  },

  toggleTaskDone(e) {
    const { taskId } = e.currentTarget.dataset;
    const { plan, progressMap } = this.data;
    if (!plan || !taskId) return;

    const next = { ...progressMap, [taskId]: !progressMap[taskId] };
    saveProgress(plan.planId, next);
    const stats = computeProgress(plan, next);

    this.setData({
      progressMap: next,
      progressStats: stats,
      planView: buildPlanView(plan, next)
    });
  }
});
