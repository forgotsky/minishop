const PLAN_PREFIX = 'skill_plan_v1';
const PROGRESS_PREFIX = 'skill_progress_v1';

function getPlanKey(planId) {
  return `${PLAN_PREFIX}_${planId}`;
}

function getProgressKey(planId) {
  return `${PROGRESS_PREFIX}_${planId}`;
}

function toMinuteTask(hourTask, idx) {
  return {
    id: `task_${idx + 1}`,
    title: hourTask.slot,
    wordsText: hourTask.wordsText,
    sentence: hourTask.sentence,
    usage: hourTask.usage,
    estimateMin: 60
  };
}

function splitTask(task, targetMin, segmentIndex) {
  return {
    id: `${task.id}_seg_${segmentIndex + 1}`,
    title: `${task.title}（切分${segmentIndex + 1}）`,
    wordsText: task.wordsText,
    sentence: task.sentence,
    usage: task.usage,
    estimateMin: targetMin
  };
}

function normalizeDailyMinutes(dailyMinutes) {
  const min = Number(dailyMinutes || 30);
  if (Number.isNaN(min)) return 30;
  return Math.max(20, Math.min(min, 180));
}

function normalizeDays(daysPerWeek) {
  const days = Number(daysPerWeek || 5);
  if (Number.isNaN(days)) return 5;
  return Math.max(1, Math.min(days, 7));
}

function buildWeeklyPlan(hourTasks, dailyMinutes, daysPerWeek) {
  const normalizedMinutes = normalizeDailyMinutes(dailyMinutes);
  const normalizedDays = normalizeDays(daysPerWeek);
  const tasks = (hourTasks || []).map((task, idx) => toMinuteTask(task, idx));

  const expanded = [];
  tasks.forEach((task) => {
    if (task.estimateMin <= normalizedMinutes) {
      expanded.push(task);
      return;
    }
    const segCount = Math.ceil(task.estimateMin / normalizedMinutes);
    const segMin = Math.ceil(task.estimateMin / segCount);
    for (let i = 0; i < segCount; i += 1) {
      expanded.push(splitTask(task, segMin, i));
    }
  });

  const schedule = Array.from({ length: normalizedDays }).map((_, idx) => ({
    day: `Day ${idx + 1}`,
    minutes: 0,
    tasks: []
  }));

  expanded.forEach((task, idx) => {
    const dayIndex = idx % normalizedDays;
    schedule[dayIndex].tasks.push(task);
    schedule[dayIndex].minutes += task.estimateMin;
  });

  const planId = `${Date.now()}`;
  const flatTasks = schedule.flatMap((d) => d.tasks.map((t) => ({ day: d.day, ...t })));
  return {
    planId,
    dailyMinutes: normalizedMinutes,
    daysPerWeek: normalizedDays,
    totalTasks: flatTasks.length,
    schedule,
    flatTasks
  };
}

function savePlan(plan) {
  if (!plan || !plan.planId) return;
  wx.setStorageSync(getPlanKey(plan.planId), plan);
}

function loadPlan(planId) {
  if (!planId) return null;
  return wx.getStorageSync(getPlanKey(planId)) || null;
}

function saveProgress(planId, progressMap) {
  if (!planId) return;
  wx.setStorageSync(getProgressKey(planId), progressMap || {});
}

function loadProgress(planId) {
  if (!planId) return {};
  return wx.getStorageSync(getProgressKey(planId)) || {};
}

function computeProgress(plan, progressMap) {
  if (!plan || !plan.flatTasks) return { done: 0, total: 0, rate: 0 };
  const total = plan.flatTasks.length;
  const done = plan.flatTasks.filter((t) => Boolean(progressMap[t.id])).length;
  const rate = total === 0 ? 0 : Math.round((done / total) * 100);
  return { done, total, rate };
}

module.exports = {
  buildWeeklyPlan,
  savePlan,
  loadPlan,
  saveProgress,
  loadProgress,
  computeProgress
};
