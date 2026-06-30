---
name: img2obsidian
description: 单张图片或整个文件夹 → AI 分析 → 结构化笔记 → 自动保存到 Obsidian 分类目录
model: deepseek-v4-flash
---

# img2obsidian — 图片转 Obsidian 笔记

## 触发

```
/img2obsidian f:/Screenshots/photo.png          ← 单张图
/img2obsidian f:/Screenshots/                   ← 整个文件夹
/img2obsidian f:/Pictures/photo.jpg --dry-run   ← 只预览不写入
```

## 分类规则

根据图片内容判断，存入 `f:/Knowledge/` 的对应目录：

| 图片内容 | → 目录 |
|---------|--------|
| AI/模型/Agent/架构图/LLM | 3-Resources/AI |
| 代码/终端/Tech/API | 3-Resources/编程 |
| 设计稿/UI/原型/产品 | 3-Resources/产品设计 |
| 生活/健康/运动/饮食 | 2-Areas |
| 财务/投资/收入 | 2-Areas |
| 课件/书籍/学习资料 | 3-Resources/读书笔记 |
| MiniShop/微信商城 | 1-Projects/MiniShop |
| 无法判断 | 0-Inbox |

## 执行流程

1. 如果是文件夹 → 找所有 png/jpg/jpeg/webp/bmp 文件
2. 逐张 Read 图片
3. 分析内容 → 输出: title, summary, category, tags(3个), key_points(3条), action_items
4. 按 category 写入 Obsidian，格式：

```markdown
---
created: YYYY-MM-DD
tags: [tag1, tag2, tag3]
source: 原始文件路径
---

# 标题

![image](原始文件路径)

## 摘要
2-3 句中文总结

## 要点
- 要点 1
- 要点 2
- 要点 3

## 行动
- [ ] 行动项 1

## 相关
- [[AI开发]] | [[MiniShop]]
```

5. 全部完成后报告: "N 张图片已处理 → f:/Knowledge/目录/"

## 重要

- 文件名用中文标题
- 不要覆盖已有文件（加时间戳）
- 批量模式每张图处理完报告进度
- 如果图片无法识别内容 → 放 0-Inbox
