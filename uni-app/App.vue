<template>
  <view class="app">
    <slot />
  </view>
</template>

<script>
export default {
  onLaunch() {}
};
</script>

<style>
page {
  background: linear-gradient(180deg, #f7fbff 0%, #eef4f9 100%);
  color: #1f2d3d;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 10rpx 30rpx rgba(13, 59, 102, 0.08);
}

.section-title {
  font-size: 34rpx;
  font-weight: 600;
  margin-bottom: 16rpx;
}
</style>
