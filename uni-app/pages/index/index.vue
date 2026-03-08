<template>
  <view class="page">
    <view class="hero card">
      <view class="hero-title">英语技能分级训练</view>
      <view class="hero-subtitle">先分类，再选Top3技能，再看L1-L6进阶和微切分任务</view>
      <button class="template-btn" size="mini" @click="goToTemplate">学科模板生成</button>
    </view>

    <view v-for="category in categories" :key="category.categoryId" class="card category-card">
      <view class="row">
        <view class="name">{{ category.categoryName }}</view>
        <view class="stage">{{ category.stage }}</view>
      </view>
      <view class="label">Top3技能</view>

      <view v-for="(skill, idx) in category.topSkills" :key="skill.skillId" class="skill-item">
        <view>
          <view class="skill-name">{{ idx + 1 }}. {{ skill.skillName }}</view>
          <view class="skill-summary">{{ skill.summary }}</view>
        </view>
        <button class="skill-btn" size="mini" @click="goToSkill(category.categoryId, skill.skillId)">查看</button>
      </view>
    </view>
  </view>
</template>

<script>
import { skillsData } from '../../data/skills';
import { mergeCategories } from '../../utils/categories';
import { fetchSkills } from '../../utils/api';

export default {
  data() {
    return {
      categories: []
    };
  },
  async onShow() {
    let base = [];
    try {
      const res = await fetchSkills();
      base = res.categories || [];
    } catch (err) {
      base = skillsData;
    }
    this.categories = mergeCategories(base);
  },
  methods: {
    goToSkill(categoryId, skillId) {
      uni.navigateTo({
        url: `/pages/skill/skill?categoryId=${categoryId}&skillId=${skillId}`
      });
    },
    goToTemplate() {
      uni.navigateTo({
        url: '/pages/template/template'
      });
    }
  }
};
</script>

<style scoped>
.page {
  padding: 24rpx;
}

.hero {
  margin-bottom: 20rpx;
  background: linear-gradient(130deg, #0d3b66 0%, #1d6fa5 100%);
  color: #fff;
}

.hero-title {
  font-size: 40rpx;
  font-weight: 700;
}

.hero-subtitle {
  margin-top: 12rpx;
  font-size: 26rpx;
  opacity: 0.9;
}

.template-btn {
  margin-top: 16rpx;
  background: #ffffff;
  color: #0d3b66;
  border: 1rpx solid #d9e8f7;
}

.category-card {
  margin-bottom: 18rpx;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 32rpx;
  font-weight: 700;
}

.stage {
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: #eef4ff;
  color: #2d4f73;
  font-size: 22rpx;
}

.label {
  margin: 14rpx 0;
  font-size: 24rpx;
  color: #5a6d80;
}

.skill-item {
  display: flex;
  justify-content: space-between;
  gap: 14rpx;
  border-top: 1rpx solid #edf1f5;
  padding: 14rpx 0;
}

.skill-name {
  font-size: 28rpx;
  font-weight: 600;
}

.skill-summary {
  margin-top: 6rpx;
  font-size: 23rpx;
  color: #6f7f8f;
}

.skill-btn {
  background: #0d3b66;
  color: #fff;
  margin: 0;
}
</style>
