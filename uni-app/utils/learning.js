const PLAN_PREFIX = 'skill_plan_v1';
const PROGRESS_PREFIX = 'skill_progress_v1';

function getPlanKey(planId) {
  return `${PLAN_PREFIX}_${planId}`;
}

function getProgressKey(planId) {
  return `${PROGRESS_PREFIX}_${planId}`;
}

export function savePlan(plan) {
  if (!plan || !plan.planId) return;
  uni.setStorageSync(getPlanKey(plan.planId), plan);
}

export function loadPlan(planId) {
  if (!planId) return null;
  return uni.getStorageSync(getPlanKey(planId)) || null;
}

export function saveProgress(planId, progressMap) {
  if (!planId) return;
  uni.setStorageSync(getProgressKey(planId), progressMap || {});
}

export function loadProgress(planId) {
  if (!planId) return {};
  return uni.getStorageSync(getProgressKey(planId)) || {};
}

export function computeProgress(plan, progressMap) {
  if (!plan || !plan.flatTasks) return { done: 0, total: 0, rate: 0 };
  const total = plan.flatTasks.length;
  const done = plan.flatTasks.filter((t) => Boolean(progressMap[t.id])).length;
  const rate = total === 0 ? 0 : Math.round((done / total) * 100);
  return { done, total, rate };
}
