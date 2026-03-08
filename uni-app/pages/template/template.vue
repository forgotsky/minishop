<template>
  <view class="page">
    <view class="card panel">
      <view class="section-title">学科模板生成</view>
      <view class="tip">输入学科名，自动生成Top3技能与L1-L6进阶。</view>
      <input class="subject-input" v-model="subjectInput" placeholder="例如：英语 / 数学 / 语文" />
      <button class="btn" @click="handleGenerate">生成模板</button>
    </view>

    <view class="card panel" v-if="generated">
      <view class="section-title">{{ generated.categoryName }}</view>
      <view class="tip">阶段：{{ generated.stage }}</view>

      <view v-for="skill in generated.topSkills" :key="skill.skillId" class="skill-box">
        <view class="skill-name">{{ skill.skillName }}</view>
        <view class="skill-summary">{{ skill.summary }}</view>
        <view class="level-row">
          <view v-for="level in skill.levels" :key="level.level" class="badge">{{ level.level }}</view>
        </view>
      </view>

      <button class="btn use" @click="useTemplate">加入分类并使用</button>
    </view>
  </view>
</template>

<script>
import { generateSkillTemplate } from '../../data/template-generator';
import { addCustomCategory } from '../../utils/categories';
import { generateTemplate } from '../../utils/api';

export default {
  data() {
    return {
      subjectInput: '英语',
      generated: null
    };
  },
  methods: {
    async handleGenerate() {
      const subject = this.subjectInput || '通用学科';
      try {
        const remote = await generateTemplate(subject);
        this.generated = remote.category;
      } catch (err) {
        this.generated = generateSkillTemplate(subject);
      }
    },
    useTemplate() {
      if (!this.generated) {
        uni.showToast({ title: '请先生成模板', icon: 'none' });
        return;
      }
      addCustomCategory(this.generated);
      const firstSkill = this.generated.topSkills[0];
      uni.navigateTo({
        url: `/pages/skill/skill?categoryId=${this.generated.categoryId}&skillId=${firstSkill.skillId}`
      });
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

.tip {
  color: #5e748b;
  font-size: 24rpx;
  margin-bottom: 10rpx;
}

.subject-input {
  background: #f4f8fc;
  border-radius: 10rpx;
  padding: 14rpx;
  font-size: 28rpx;
}

.btn {
  margin-top: 14rpx;
  background: #0d3b66;
  color: #fff;
}

.use {
  background: #136f63;
}

.skill-box {
  border-top: 1rpx solid #edf2f7;
  padding: 12rpx 0;
}

.skill-name {
  font-size: 28rpx;
  font-weight: 700;
}

.skill-summary {
  font-size: 23rpx;
  color: #60778f;
  margin-top: 4rpx;
}

.level-row {
  margin-top: 10rpx;
}

.badge {
  display: inline-block;
  margin-right: 8rpx;
  margin-bottom: 8rpx;
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: #e7f1fb;
  color: #0d3b66;
  font-size: 22rpx;
}
</style>
