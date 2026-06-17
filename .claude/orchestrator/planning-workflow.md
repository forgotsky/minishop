# Planning 沙箱 Workflow

4-agent 开会拆 URS → 产出可执行的 Story 文件。

## 触发条件
- `board/backlog/` 有新 URS 文件
- Orchestrator 检测到 → 创建 Planning 沙箱

## 4-Agent 链式会议

### Stage 1: Business Analyst (BA)
**输入**: URS.md 原文
**输出**: 用户故事 + 验收标准
**提示**:
```
You are a Business Analyst. Read the URS below.
1. Extract all user stories (As a.. I want.. So that..)
2. Define acceptance criteria (Given/When/Then)
3. Clarify any ambiguities — if something is unclear, flag it with [QUESTION]
Output in markdown.
```

### Stage 2: Product Manager (PM)
**输入**: BA 输出 + URS 原文
**输出**: Story 拆分 + 优先级 + 估时
**提示**:
```
You are a Product Manager. Based on the BA analysis:
1. Break the feature into implementable stories (SHOP-XXX-A, SHOP-XXX-B, ...)
2. Assign priority (P0=blocking, P1=critical, P2=normal, P3=nice)
3. Estimate effort (S/M/L/XL)
4. For each story: list which agent types are needed
5. Identify dependencies between stories
Output in markdown with frontmatter for each story.
```

### Stage 3: Architect
**输入**: PM 输出 + 现有代码结构
**输出**: 技术方案 + DAG
**提示**:
```
You are a System Architect. Based on the PM's story breakdown:
1. For each story: design API endpoints, database changes, component tree
2. Define the dependency DAG between stories (which story must complete before which?)
3. Flag any risks or technical concerns
Output in markdown.
```

### Stage 4: Planner (Final拍板)
**输入**: 上面所有人的输出
**输出**: 写入 `board/ready/` 的 Story 文件
**提示**:
```
You are a Planner. Synthesize all analysis and write the final story files to board/ready/.

For EACH story, write a file with this exact format:

---
story: SHOP-XXX-A
priority: P0
agents: [backend-dev, tester, reviewer]
depends_on: []
---

# SHOP-XXX-A: [Title]

## 验收标准
...

## 步骤
- [ ] agent1: task description
- [ ] agent2: task description
- [HUMAN] UAT checkpoint

Also write board/ready/SHOP-XXX-DAG.md:
---
story: SHOP-XXX-DAG
priority: N/A
agents: []
depends_on: []
---

# DAG
A -> B
A -> C
B -> D
C -> D
```

## 输出结构
```
board/ready/
├── SHOP-XXX-A.md    ← 完整可执行的 Story
├── SHOP-XXX-B.md
├── SHOP-XXX-C.md
├── SHOP-XXX-DAG.md  ← 依赖关系图
└── SHOP-XXX-A.md    ← 每个都包含: frontmatter, 验收标准, checklist steps

board/backlog/SHOP-XXX.md  ← 原 URS 移到这里 (已拆解)
```
