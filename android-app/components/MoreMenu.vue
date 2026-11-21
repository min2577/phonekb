<template>
  <view v-if="show" class="more-mask" @tap="onTapMask">
    <view class="more-menu" @tap.stop="">
      <view v-for="m in menuItems" :key="m.key"
            class="more-menu-item"
            :class="{ 'more-menu-item-disabled': m.disabled }"
            hover-class="more-menu-item-hover"
            @tap="onSelect(m)">
        <view class="more-menu-icon">
          <text class="more-menu-icon-text">{{ m.icon }}</text>
        </view>
        <view class="more-menu-text">
          <text class="more-menu-title">{{ m.title }}</text>
          <text v-if="m.subtitle" class="more-menu-subtitle">{{ m.subtitle }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: "MoreMenu",
  props: {
    show: { type: Boolean, default: false },
    allCollapsed: { type: Boolean, default: false },
  },
  emits: ["select", "close"],
  computed: {
    menuItems() {
      return [
        { key: "edit-layout",   icon: "\u270E", title: "\u7F16\u8F91\u9762\u677F", subtitle: "\u6DFB\u52A0\u3001\u5220\u9664\u6216\u6392\u5E8F\u7EC4\u4EF6" },
        { key: "switch-layout", icon: "\u25A3", title: "\u5207\u6362\u9762\u677F", subtitle: "\u5207\u6362\u5230\u5176\u4ED6\u9762\u677F\u65B9\u6848" },
        { key: "new-layout",    icon: "+",      title: "\u65B0\u5EFA\u9762\u677F", subtitle: "\u521B\u5EFA\u65B0\u7684\u9762\u677F\u65B9\u6848" },
        { key: "manage-layout", icon: "\u2637", title: "\u9762\u677F\u7BA1\u7406", subtitle: "\u91CD\u547D\u540D\u3001\u590D\u5236\u6216\u5220\u9664\u9762\u677F" },
      ]
    },
  },
  methods: {
    onTapMask() {
      this.$emit("close")
    },
    onSelect(m) {
      if (m && m.disabled) return
      this.$emit("select", m.key)
    },
  },
}
</script>

<style>
.more-mask {
  position: fixed; inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48rpx;
  background: rgba(31,48,70,0.28);
  backdrop-filter: blur(14rpx);
  -webkit-backdrop-filter: blur(14rpx);
  z-index: 300;
}
.more-menu {
  width: 100%;
  max-width: 640rpx;
  padding: 16rpx 14rpx;
  background: rgba(255,255,255,0.92);
  border: 1rpx solid rgba(121,146,173,0.18);
  border-radius: 28rpx;
  box-shadow: var(--shadow-fluent-flyout);
  backdrop-filter: blur(48rpx) saturate(160%);
  -webkit-backdrop-filter: blur(48rpx) saturate(160%);
  overflow: hidden;
}
.more-menu-item {
  display: flex;
  align-items: center;
  gap: 18rpx;
  min-height: 104rpx;
  padding: 14rpx 18rpx;
  border-radius: 18rpx;
  transition: background-color 120ms cubic-bezier(0.1,0.9,0.2,1);
}
.more-menu-item + .more-menu-item { margin-top: 4rpx; }
.more-menu-item-hover { background: var(--color-primary-bg); }
.more-menu-icon {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18rpx;
  background: #EDF4FC;
  color: #2F5E92;
  flex-shrink: 0;
}
.more-menu-icon-text {
  font-size: 34rpx;
  font-weight: 500;
  line-height: 1;
  text-align: center;
  font-family: "Segoe UI Symbol", "Segoe UI", system-ui, sans-serif;
}
.more-menu-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.more-menu-title {
  font-size: 29rpx;
  font-weight: 600;
  line-height: 1.25;
  color: var(--color-text);
  letter-spacing: 0.2rpx;
}
.more-menu-subtitle {
  font-size: 22rpx;
  line-height: 1.3;
  color: var(--color-text-light);
}
</style>
