<template>
  <view class="widget-card" :class="{ 'is-collapsed': collapsed }">
    <view class="widget-card-head" hover-class="widget-card-head-hover" @tap="onTapHead">
      <text class="widget-card-icon">{{ icon }}</text>
      <text class="widget-card-title">{{ title }}</text>
      <text class="widget-card-chevron">⌃</text>
    </view>
    <view v-if="!collapsed" class="widget-card-body">
      <slot />
    </view>
  </view>
</template>

<script>
export default {
  name: 'WidgetCard',
  props: {
    title: { type: String, default: '' },
    icon: { type: String, default: '' },
    collapsed: { type: Boolean, default: false },
  },
  emits: ['toggle'],
  methods: {
    onTapHead() {
      this.$emit('toggle')
    },
  },
}
</script>

<style>
.widget-card {
  background: var(--color-card-acrylic);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: var(--radius-fluent-lg);
  box-shadow: var(--shadow-fluent-2);
  margin: 0 24rpx 16rpx;
  overflow: hidden;
}
.widget-card-head {
  min-height: 78rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  background: transparent;
  transition: background-color var(--duration-base) var(--ease-fluent);
}
.widget-card-head-hover { background: var(--color-primary-bg); }
.widget-card-icon {
  font-size: 32rpx;
  line-height: 1;
}
.widget-card-title {
  flex: 1;
  font-size: 30rpx;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.2rpx;
}
.widget-card-chevron {
  font-size: 32rpx;
  color: var(--color-text-mid);
  transition: transform var(--duration-base) var(--ease-fluent);
  line-height: 1;
}
.widget-card.is-collapsed .widget-card-chevron {
  transform: rotate(180deg);
}
.widget-card-body {
  padding: 16rpx 24rpx 24rpx;
}
</style>
