const baseLevels = [
  { level: 'L1', title: '基础识别', objective: '建立最小可用词汇与句型。', points: ['核心词汇', '基础句型', '输入-输出对照'] },
  { level: 'L2', title: '稳定应用', objective: '能在固定场景中稳定使用。', points: ['词块积累', '句型替换', '主题表达'] },
  { level: 'L3', title: '场景迁移', objective: '可迁移到新场景并完成表达。', points: ['扩展词汇', '表达变体', '理解与复述'] },
  { level: 'L4', title: '结构化输出', objective: '形成段落级输出能力。', points: ['结构组织', '逻辑连接', '准确性检查'] },
  { level: 'L5', title: '策略化提升', objective: '可在任务中选择策略解决问题。', points: ['任务拆解', '策略选择', '复盘修正'] },
  { level: 'L6', title: '综合实战', objective: '在复杂任务中保持质量与效率。', points: ['综合应用', '限时完成', '质量评估'] }
];

const subjectTopSkills = {
  english: ['词汇与表达', '阅读理解', '写作输出'],
  math: ['概念与公式', '题型策略', '综合建模'],
  chinese: ['基础字词', '阅读分析', '写作表达'],
  physics: ['核心概念', '公式推导', '实验与综合题'],
  chemistry: ['基础理论', '方程式应用', '实验分析'],
  biology: ['概念系统', '图表解读', '综合应用']
};

function normalizeSubject(subject) {
  const txt = (subject || '').toLowerCase().trim();
  if (txt.includes('english') || txt.includes('英语')) return 'english';
  if (txt.includes('math') || txt.includes('数学')) return 'math';
  if (txt.includes('chinese') || txt.includes('语文')) return 'chinese';
  if (txt.includes('physics') || txt.includes('物理')) return 'physics';
  if (txt.includes('chemistry') || txt.includes('化学')) return 'chemistry';
  if (txt.includes('biology') || txt.includes('生物')) return 'biology';
  return 'generic';
}

function buildL1Micro(subject, skillName) {
  const s = normalizeSubject(subject);
  if (s === 'english') {
    return {
      dailyLoad: '40分钟/天',
      hourlyLoad: '每小时 6词 + 2例句 + 1应用',
      hourTasks: [
        { slot: '第1小时', words: ['book', 'class', 'teacher', 'student', 'read', 'write'], wordsText: 'book / class / teacher / student / read / write', sentence: 'I read a book in class.', usage: '用学校场景说2句。' },
        { slot: '第2小时', words: ['happy', 'busy', 'early', 'late', 'always', 'often'], wordsText: 'happy / busy / early / late / always / often', sentence: 'I am always early for class.', usage: '描述你的一天习惯。' },
        { slot: '第3小时', words: ['go', 'come', 'eat', 'drink', 'play', 'study'], wordsText: 'go / come / eat / drink / play / study', sentence: 'I study English every day.', usage: '围绕放学后活动说3句。' }
      ],
      dayTasks: [
        { day: 'Day 1', target: '学校主题词汇+一般现在时', deliverable: '掌握6词，输出2句。' },
        { day: 'Day 2', target: '状态和频率副词', deliverable: '掌握6词，输出2句。' },
        { day: 'Day 3', target: '动作动词表达', deliverable: '掌握6词，输出3句。' }
      ]
    };
  }

  return {
    dailyLoad: '40分钟/天',
    hourlyLoad: `每小时 3概念 + 2例子 + 1应用（${skillName}）`,
    hourTasks: [
      { slot: '第1小时', words: ['概念A', '概念B', '概念C'], wordsText: '概念A / 概念B / 概念C', sentence: `这是${skillName}的基础定义。`, usage: '用自己的话复述定义。' },
      { slot: '第2小时', words: ['规则A', '规则B', '规则C'], wordsText: '规则A / 规则B / 规则C', sentence: `在${skillName}题目中应用规则A。`, usage: '做1道对应练习并讲解过程。' }
    ],
    dayTasks: [
      { day: 'Day 1', target: '基础定义', deliverable: '复述3个核心概念。' },
      { day: 'Day 2', target: '规则应用', deliverable: '完成2道基础题。' }
    ]
  };
}

function buildLevels(subject, skillName) {
  return baseLevels.map((lvl) => ({
    level: lvl.level,
    title: `${lvl.title}（${skillName}）`,
    objective: lvl.objective,
    points: lvl.points,
    microSplit: lvl.level === 'L1' ? buildL1Micro(subject, skillName) : undefined
  }));
}

function generateSkillTemplate(subjectInput) {
  const subject = (subjectInput || '通用学科').trim();
  const key = normalizeSubject(subject);
  const topSkills = (subjectTopSkills[key] || ['基础能力', '关键方法', '综合应用']).map((name, idx) => ({
    skillId: `tpl_${idx + 1}`,
    skillName: name,
    summary: `${subject} · ${name}`,
    levels: buildLevels(subject, name)
  }));

  return {
    categoryId: `tpl_${Date.now()}`,
    categoryName: `${subject} 模板`,
    stage: '自动生成',
    topSkills
  };
}

module.exports = {
  generateSkillTemplate
};
