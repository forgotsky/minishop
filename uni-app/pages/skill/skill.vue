<template>
  <view class="page" v-if="activeCategory && activeSkill">
    <view class="card panel">
      <view class="panel-title">分类选择</view>
      <picker mode="selector" :range="categories" range-key="categoryName" :value="categoryIndex" @change="onCategoryChange">
        <view class="picker">当前分类：{{ activeCategory.categoryName }}（{{ activeCategory.stage }}）</view>
      </picker>

      <view class="sub-title">Top3技能</view>
      <view class="chip-wrap">
        <view
          v-for="skill in activeCategory.topSkills"
          :key="skill.skillId"
          :class="['chip', skill.skillId === activeSkillId ? 'chip-active' : '']"
          @click="onSkillChange(skill.skillId)"
        >{{ skill.skillName }}</view>
      </view>
    </view>

    <view class="card panel">
      <view class="section-title">{{ activeSkill.skillName }}</view>
      <view class="desc">{{ activeSkill.summary }}</view>

      <view v-for="level in activeSkill.levels" :key="level.level" class="level-box">
        <view class="level-title">{{ level.level }} · {{ level.title }}</view>
        <view class="level-objective">目标：{{ level.objective }}</view>
        <view class="points-label">知识点：</view>
        <view v-for="point in level.points" :key="point" class="point">- {{ point }}</view>
      </view>
    </view>

    <view class="card panel" v-if="activeSkill.levels[0].microSplit">
      <view class="section-title">L1 微切分学习任务</view>
      <view class="load">建议强度：{{ activeSkill.levels[0].microSplit.dailyLoad }} ｜ {{ activeSkill.levels[0].microSplit.hourlyLoad }}</view>

      <view class="mode-row">
        <view :class="['mode', l1Mode === 'hour' ? 'mode-active' : '']" @click="l1Mode='hour'">按小时</view>
        <view :class="['mode', l1Mode === 'day' ? 'mode-active' : '']" @click="l1Mode='day'">按天</view>
      </view>

      <view v-if="l1Mode === 'hour'">
        <view v-for="task in activeSkill.levels[0].microSplit.hourTasks" :key="task.slot" class="task">
          <view class="task-title">{{ task.slot }}</view>
          <view class="task-text">词汇：{{ task.wordsText }}</view>
          <view class="task-text">例句：{{ task.sentence }}</view>
          <view class="task-text">应用：{{ task.usage }}</view>
        </view>
      </view>

      <view v-if="l1Mode === 'day'">
        <view v-for="task in activeSkill.levels[0].microSplit.dayTasks" :key="task.day" class="task">
          <view class="task-title">{{ task.day }}</view>
          <view class="task-text">学习目标：{{ task.target }}</view>
          <view class="task-text">验收标准：{{ task.deliverable }}</view>
        </view>
      </view>
    </view>

    <view class="card panel">
      <view class="section-title">学习计划生成器</view>
      <view class="plan-row">
        <view class="plan-input">
          <view class="plan-label">每天可学(分钟)</view>
          <input type="number" v-model="dailyMinutes" class="input" />
        </view>
        <view class="plan-input">
          <view class="plan-label">每周学习天数</view>
          <input type="number" v-model="daysPerWeek" class="input" />
        </view>
      </view>
      <button class="plan-btn" @click="generatePlan">生成周计划</button>

      <view v-if="planView">
        <view class="progress">完成率：{{ progressStats.rate }}%（{{ progressStats.done }}/{{ progressStats.total }}）</view>
        <view v-for="dayBlock in planView.schedule" :key="dayBlock.day" class="day-box">
          <view class="day-title">{{ dayBlock.day }} · 预计{{ dayBlock.minutes }}分钟</view>
          <view
            v-for="task in dayBlock.tasks"
            :key="task.id"
            :class="['task', 'task-check', task.done ? 'task-done' : '']"
            @click="toggleTaskDone(task.id)"
          >
            <view class="check">{{ task.done ? '已完成' : '待完成' }}</view>
            <view class="task-title">{{ task.title }}（{{ task.estimateMin }}分钟）</view>
            <view class="task-text">词汇：{{ task.wordsText }}</view>
            <view class="task-text">例句：{{ task.sentence }}</view>
            <view class="task-text">应用：{{ task.usage }}</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { skillsData } from '../../data/skills';
import { mergeCategories } from '../../utils/categories';
import { fetchSkills, generatePlan } from '../../utils/api';
import { savePlan, loadPlan, saveProgress, loadProgress, computeProgress } from '../../utils/learning';

const LAST_PLAN_KEY = 'last_plan_by_skill_v1';

function getFallback(categories) {
  const category = categories[0];
  const skill = category.topSkills[0];
  return { category, skill };
}

function getSkillKey(categoryId, skillId) {
  return `${categoryId}__${skillId}`;
}

function readLastPlanMap() {
  return uni.getStorageSync(LAST_PLAN_KEY) || {};
}

function writeLastPlanMap(data) {
  uni.setStorageSync(LAST_PLAN_KEY, data || {});
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

export default {
  data() {
    return {
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
    };
  },
  async onLoad(options) {
    let base = [];
    try {
      const res = await fetchSkills();
      base = res.categories || [];
    } catch (err) {
      base = skillsData;
    }
    const categories = mergeCategories(base);
    const fallback = getFallback(categories);
    const categoryId = options.categoryId || fallback.category.categoryId;
    const category = categories.find((item) => item.categoryId === categoryId) || fallback.category;
    const skillId = options.skillId || category.topSkills[0].skillId;
    const skill = category.topSkills.find((item) => item.skillId === skillId) || category.topSkills[0];
    const categoryIndex = categories.findIndex((item) => item.categoryId === category.categoryId);

    this.categories = categories;
    this.categoryIndex = categoryIndex < 0 ? 0 : categoryIndex;
    this.activeCategoryId = category.categoryId;
    this.activeSkillId = skill.skillId;
    this.activeCategory = category;
    this.activeSkill = skill;

    this.restorePlan(category.categoryId, skill.skillId);
  },
  methods: {
    onCategoryChange(e) {
      const categoryIndex = Number(e.detail.value || 0);
      const category = this.categories[categoryIndex];
      if (!category) return;
      const skill = category.topSkills[0];
      this.categoryIndex = categoryIndex;
      this.activeCategoryId = category.categoryId;
      this.activeSkillId = skill.skillId;
      this.activeCategory = category;
      this.activeSkill = skill;
      this.l1Mode = 'hour';
      this.restorePlan(category.categoryId, skill.skillId);
    },
    onSkillChange(skillId) {
      const skill = this.activeCategory.topSkills.find((item) => item.skillId === skillId);
      if (!skill) return;
      this.activeSkillId = skillId;
      this.activeSkill = skill;
      this.l1Mode = 'hour';
      this.restorePlan(this.activeCategory.categoryId, skillId);
    },
    restorePlan(categoryId, skillId) {
      const lastPlanMap = readLastPlanMap();
      const skillKey = getSkillKey(categoryId, skillId);
      const lastPlanId = lastPlanMap[skillKey];
      if (!lastPlanId) {
        this.plan = null;
        this.planView = null;
        this.progressMap = {};
        this.progressStats = { done: 0, total: 0, rate: 0 };
        return;
      }
      const plan = loadPlan(lastPlanId);
      if (!plan) return;
      const progressMap = loadProgress(lastPlanId);
      this.plan = plan;
      this.planView = buildPlanView(plan, progressMap);
      this.progressMap = progressMap;
      this.progressStats = computeProgress(plan, progressMap);
      this.dailyMinutes = plan.dailyMinutes;
      this.daysPerWeek = plan.daysPerWeek;
    },
    async generatePlan() {
      const l1 = this.activeSkill.levels && this.activeSkill.levels[0];
      if (!l1 || !l1.microSplit || !l1.microSplit.hourTasks) {
        uni.showToast({ title: '该技能暂无L1切分', icon: 'none' });
        return;
      }
      const payload = {
        hour_tasks: l1.microSplit.hourTasks,
        daily_minutes: Number(this.dailyMinutes || 40),
        days_per_week: Number(this.daysPerWeek || 5)
      };
      let plan = null;
      try {
        const res = await generatePlan(payload);
        plan = res.plan;
      } catch (err) {
        uni.showToast({ title: '后端未连接，已降级本地计划', icon: 'none' });
        plan = {
          planId: `${Date.now()}`,
          dailyMinutes: payload.daily_minutes,
          daysPerWeek: payload.days_per_week,
          schedule: l1.microSplit.dayTasks.map((day, idx) => ({
            day: day.day || `Day ${idx + 1}`,
            minutes: 40,
            tasks: l1.microSplit.hourTasks.slice(0, 1).map((task) => ({
              id: `task_${idx + 1}`,
              title: task.slot,
              wordsText: task.wordsText,
              sentence: task.sentence,
              usage: task.usage,
              estimateMin: 60
            }))
          }))
        };
        plan.flatTasks = plan.schedule.flatMap((d) => d.tasks.map((t) => ({ day: d.day, ...t })));
        plan.totalTasks = plan.flatTasks.length;
      }

      savePlan(plan);
      const lastPlanMap = readLastPlanMap();
      lastPlanMap[getSkillKey(this.activeCategoryId, this.activeSkillId)] = plan.planId;
      writeLastPlanMap(lastPlanMap);

      const progressMap = {};
      saveProgress(plan.planId, progressMap);
      this.plan = plan;
      this.planView = buildPlanView(plan, progressMap);
      this.progressMap = progressMap;
      this.progressStats = computeProgress(plan, progressMap);
      this.dailyMinutes = plan.dailyMinutes;
      this.daysPerWeek = plan.daysPerWeek;
    },
    toggleTaskDone(taskId) {
      if (!this.plan || !taskId) return;
      const next = { ...this.progressMap, [taskId]: !this.progressMap[taskId] };
      saveProgress(this.plan.planId, next);
      this.progressMap = next;
      this.progressStats = computeProgress(this.plan, next);
      this.planView = buildPlanView(this.plan, next);
    }
  }
};
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.panel {
  margin-bottom: 18rpx;
}

.panel-title {
  font-size: 30rpx;
  font-weight: 700;
  margin-bottom: 12rpx;
}

.picker {
  background: #f3f8fd;
  border-radius: 12rpx;
  padding: 16rpx;
  color: #274967;
  font-size: 26rpx;
}

.sub-title {
  margin-top: 16rpx;
  margin-bottom: 10rpx;
  color: #55677a;
  font-size: 24rpx;
}

.chip-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.chip {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #edf4fc;
  font-size: 24rpx;
  color: #325574;
}

.chip-active {
  background: #0d3b66;
  color: #ffffff;
}

.desc {
  color: #5f7286;
  margin-bottom: 12rpx;
  font-size: 24rpx;
}

.level-box {
  border-top: 1rpx solid #edf2f7;
  padding: 14rpx 0;
}

.level-title {
  font-size: 27rpx;
  font-weight: 700;
}

.level-objective {
  margin-top: 8rpx;
  color: #3a4f65;
  font-size: 24rpx;
}

.points-label {
  margin-top: 8rpx;
  color: #607387;
  font-size: 23rpx;
}

.point {
  color: #5a6b7d;
  font-size: 23rpx;
  margin-top: 4rpx;
}

.load {
  margin-top: 8rpx;
  color: #3a5f81;
  font-size: 24rpx;
}

.mode-row {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
}

.mode {
  flex: 1;
  text-align: center;
  border-radius: 10rpx;
  padding: 14rpx 0;
  background: #eef3f8;
  color: #4f657b;
  font-size: 24rpx;
}

.mode-active {
  background: #0d3b66;
  color: #fff;
}

.task {
  margin-top: 12rpx;
  background: #f8fbfe;
  border-radius: 12rpx;
  padding: 14rpx;
}

.task-title {
  font-size: 25rpx;
  font-weight: 700;
  margin-bottom: 6rpx;
}

.task-text {
  font-size: 23rpx;
  color: #53677a;
  margin-top: 2rpx;
}

.plan-row {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}

.plan-input {
  flex: 1;
}

.plan-label {
  font-size: 23rpx;
  color: #58708a;
  margin-bottom: 8rpx;
}

.input {
  background: #f4f8fc;
  border-radius: 10rpx;
  padding: 12rpx;
  font-size: 25rpx;
}

.plan-btn {
  margin-top: 14rpx;
  background: #0d3b66;
  color: #fff;
}

.progress {
  margin-top: 14rpx;
  font-size: 25rpx;
  color: #234d74;
  font-weight: 600;
}

.day-box {
  margin-top: 10rpx;
  border-top: 1rpx solid #edf2f7;
  padding-top: 10rpx;
}

.day-title {
  font-size: 24rpx;
  font-weight: 700;
  color: #294a68;
}

.task-check {
  border: 1rpx solid #e4edf5;
}

.task-done {
  background: #eefaf2;
  border-color: #ccead5;
}

.check {
  display: inline-block;
  margin-bottom: 8rpx;
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #edf3fa;
  color: #4b6480;
  font-size: 21rpx;
}
</style>
