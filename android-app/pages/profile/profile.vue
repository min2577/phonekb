<template>
<view :class="['page', 'profile-page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <!-- 用户卡片 -->
  <view class="user-card">
    <view class="user-avatar">⌨</view>
    <view class="user-info">
      <text class="user-name">键盘用户</text>
      <text class="user-sub">
        <text v-if="connected">● 已连接 · {{host}}</text>
        <text v-else>○ 未连接</text>
      </text>
    </view>
    <text class="user-arrow">›</text>
  </view>

  <!-- 三个快捷入口 -->
  <view class="quick-card">
    <view class="quick-item" hover-class="quick-item-hover" @tap="onCustomizeApp">
      <text class="quick-icon">◫</text>
      <text class="quick-label">自定义App</text>
      <text class="quick-sub">底部Tab编辑</text>
    </view>
    <view class="quick-divider"></view>
    <view class="quick-item" hover-class="quick-item-hover" @tap="onManageWidgets">
      <text class="quick-icon">◇</text>
      <text class="quick-label">组件管理</text>
      <text class="quick-sub">添加/移除组件</text>
    </view>
    <view class="quick-divider"></view>
    <view class="quick-item" hover-class="quick-item-hover" @tap="onMyDevices">
      <text class="quick-icon">▤</text>
      <text class="quick-label">我的设备</text>
      <text class="quick-sub">{{connected ? '已连接' : '未连接'}}</text>
    </view>
  </view>

  <!-- 列表入口 -->
  <view class="list-card">
    <view class="list-item" hover-class="list-item-hover" @tap="onAbout">
      <text class="list-icon">i</text>
      <text class="list-label">关于我们</text>
      <text class="list-arrow">›</text>
    </view>
    <view class="list-divider"></view>
    <view class="list-item" hover-class="list-item-hover" @tap="onInvite">
      <text class="list-icon">↗</text>
      <text class="list-label">邀请好友</text>
      <text class="list-arrow">›</text>
    </view>
    <view class="list-divider"></view>
    <view class="list-item" hover-class="list-item-hover" @tap="onFeedback">
      <text class="list-icon">✉</text>
      <text class="list-label">意见反馈</text>
      <text class="list-arrow">›</text>
    </view>
    <view class="list-divider"></view>
    <view class="list-item" hover-class="list-item-hover" @tap="onHelp">
      <text class="list-icon">?</text>
      <text class="list-label">帮助中心</text>
      <text class="list-arrow">›</text>
    </view>
    <view class="list-divider"></view>
    <view class="list-item" hover-class="list-item-hover" @tap="onSettings">
      <text class="list-icon">⚙</text>
      <text class="list-label">设置</text>
      <text class="list-arrow">›</text>
    </view>
  </view>

  <view class="version-row">
    <text class="version-text">手机键盘 · v0.3.2</text>
  </view>

    <CustomTabBar />
  </view>
</template>


<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
import Net from '@/utils/net.js'

export default {
  components: { CustomTabBar },
  data() {
    return {
      statusBarHeight: 24,
      host: '',
      connected: false,
    }
  },
  onShow() {
    const self = this
    let gd = {}
    try { const _app = getApp({ allowDefault: true }); if (_app) gd = _app.globalData || {} } catch (e) { gd = {} }
    self.host = gd.host || ''
    self.connected = Net.isConnected()
  },
  onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
    onCustomizeApp() {
      uni.navigateTo({ url: '/pages/tab-config/tab-config' })
    },
    onManageWidgets() {
      uni.navigateTo({ url: '/pages/widgets-manage/widgets-manage' })
    },
    onMyDevices() {
      uni.navigateTo({ url: '/pages/devices/devices' })
    },
    onAbout() {
      uni.navigateTo({ url: '/pages/about/about' })
    },
    onInvite() {
      uni.showToast({ title: '邀请好友功能开发中', icon: 'none', duration: 1200 })
    },
    onFeedback() {
      uni.showToast({ title: '意见反馈功能开发中', icon: 'none', duration: 1200 })
    },
    onHelp() {
      uni.showToast({ title: '帮助中心功能开发中', icon: 'none', duration: 1200 })
    },
    onSettings() {
      uni.navigateTo({ url: '/pages/settings/settings' })
    },
  },
}
</script>


<style>
.profile-page {
  font-family: Roboto, "Noto Sans CJK SC", "Noto Sans SC", sans-serif;
}
.profile-page .user-card {
  min-height: 126rpx;
  padding: 24rpx 26rpx;
  margin-bottom: 18rpx;
  border-radius: 22rpx;
}
.profile-page .user-avatar {
  width: 78rpx;
  height: 78rpx;
  border-radius: 20rpx;
  font-size: 36rpx;
  color: var(--color-primary);
  font-family: "Segoe UI Symbol", sans-serif;
}
.profile-page .user-name { font-size: 30rpx; font-weight: 700; }
.profile-page .user-sub { font-size: 21rpx; }
.profile-page .user-arrow { color: var(--color-text-light); font-size: 34rpx; }
.profile-page .quick-card { padding: 10rpx; margin-bottom: 18rpx; border-radius: 22rpx; }
.profile-page .quick-item { min-height: 124rpx; padding: 16rpx 4rpx; border-radius: 16rpx; }
.profile-page .quick-icon {
  width: 52rpx;
  height: 52rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-family: "Segoe UI Symbol", sans-serif;
  font-size: 28rpx;
}
.profile-page .quick-label { font-size: 22rpx; }
.profile-page .quick-sub { font-size: 17rpx; }
.profile-page .list-card { border-radius: 22rpx; margin-bottom: 20rpx; }
.profile-page .list-item { min-height: 78rpx; padding: 14rpx 22rpx; gap: 16rpx; }
.profile-page .list-icon { width: 46rpx; height: 46rpx; border-radius: 13rpx; font-size: 24rpx; font-weight: 700; }
.profile-page .list-label { font-size: 25rpx; font-weight: 600; }
.profile-page .list-divider { margin-left: 84rpx; }
.profile-page .version-row { padding: 12rpx 0; }
page {
  background: var(--color-bg);
}

/* 页面级 */
.page { min-height: 100vh; padding: 24rpx 24rpx 48rpx; }

/* 用户卡片 */
.user-card {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 28rpx 32rpx;
  background: var(--color-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin-bottom: 24rpx;
}
.user-avatar {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-bg) 0%, var(--color-primary-subtle) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 56rpx;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}
.user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.user-name {
  font-size: 36rpx;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 0.5rpx;
}
.user-sub {
  font-size: 24rpx;
  color: var(--color-text-mid);
  font-family: Consolas, monospace;
}

/* 三个快捷入口 */
.quick-card {
  display: flex;
  align-items: stretch;
  background: var(--color-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin-bottom: 24rpx;
  padding: 24rpx 0;
}
.quick-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 8rpx;
  transition: background-color var(--duration-base) var(--ease-fluent);
  border-radius: var(--radius-md);
  margin: 0 8rpx;
}
.quick-item-hover { background: var(--color-bg-alt); }
.quick-icon { font-size: 56rpx; line-height: 1; }
.quick-label { font-size: 26rpx; font-weight: 600; color: var(--color-text); margin-top: 4rpx; }
.quick-sub { font-size: 20rpx; color: var(--color-text-light); }
.quick-divider {
  width: 1rpx;
  background: var(--color-divider);
  margin: 24rpx 0;
}

/* 列表卡片 */
.list-card {
  background: var(--color-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  margin-bottom: 32rpx;
}
.list-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 28rpx 32rpx;
  transition: background-color var(--duration-base) var(--ease-fluent);
}
.list-item-hover { background: var(--color-bg-alt); }
.list-icon { font-size: 36rpx; line-height: 1; flex-shrink: 0; width: 44rpx; text-align: center; }
.list-label {
  flex: 1;
  font-size: 30rpx;
  color: var(--color-text);
  font-weight: 500;
}
.list-arrow {
  font-size: 36rpx;
  color: var(--color-text-light);
  line-height: 1;
}
.list-divider {
  height: 1rpx;
  background: var(--color-divider);
  margin: 0 32rpx;
}

/* 版本 */
.version-row {
  text-align: center;
  padding: 24rpx 0;
}
.version-text {
  font-size: 22rpx;
  color: var(--color-text-light);
  font-family: Consolas, monospace;
}

.statusbar-spacer { width: 100%; }
</style>

<style>
.page {
  min-height: 100vh;
  padding: 28rpx 24rpx calc(140rpx + env(safe-area-inset-bottom));
  background: radial-gradient(82% 36% at 12% 0%, rgba(47,120,246,0.12) 0%, rgba(244,248,253,0) 76%), var(--color-bg);
}
.user-card,
.quick-card,
.list-card {
  background: rgba(255,255,255,0.94);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: 28rpx;
  box-shadow: var(--shadow-fluent-2);
}
.user-card { padding: 32rpx 30rpx; margin-bottom: 22rpx; position: relative; overflow: hidden; backdrop-filter: blur(20rpx); -webkit-backdrop-filter: blur(20rpx); }
.user-avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 24rpx;
  background: linear-gradient(145deg, #F7FBFF 0%, var(--color-primary-bg) 100%);
  border: 1rpx solid rgba(47,120,246,0.18);
  box-shadow: none;
  font-size: 46rpx;
}
.user-name { font-size: 34rpx; font-weight: 650; color: var(--color-text); }
.user-sub { color: var(--color-text-mid); font-family: inherit; }
.quick-card { padding: 12rpx; margin-bottom: 20rpx; }
.quick-item {
  min-height: 154rpx;
  margin: 0 4rpx;
  padding: 18rpx 6rpx;
  background: #F7FAFE;
  border: 1rpx solid rgba(111,139,170,0.10);
  border-radius: 20rpx;
}
.quick-item-hover { background: var(--color-primary-bg); transform: scale(0.98); }
.quick-icon { font-size: 42rpx; }
.quick-label { font-size: 24rpx; color: var(--color-text); }
.quick-sub { font-size: 19rpx; color: var(--color-text-light); }
.quick-divider { width: 8rpx; background: transparent; margin: 0; }
.list-card { overflow: hidden; margin-bottom: 26rpx; background: #FFFFFF; border-radius: 22rpx; }
.list-item { min-height: 96rpx; padding: 22rpx 26rpx; gap: 20rpx; }
.list-item-hover { background: #F3F7FB; }
.list-icon {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #EAF4FF;
  color: var(--color-primary);
  font-size: 30rpx;
  border-radius: 14rpx;
  flex-shrink: 0;
}
.list-label { font-size: 28rpx; font-weight: 550; }
.list-divider { background: var(--color-divider); margin: 0 26rpx 0 96rpx; }
.version-row { padding: 18rpx 0; }

/* 外观设置启用后，保留卡片层级并让透明度真正作用到内部组件。 */
.profile-page.app-appearance-active .user-card,
.profile-page.app-appearance-active .quick-card,
.profile-page.app-appearance-active .list-card {
  background: var(--app-surface);
  border-color: var(--app-color-border);
}
.profile-page.app-appearance-active .quick-item {
  background: var(--app-surface-strong);
  border-color: var(--app-color-divider);
}
.profile-page.app-appearance-active .user-avatar,
.profile-page.app-appearance-active .list-icon {
  background: var(--app-color-primary-bg);
  border-color: var(--app-color-border);
}
.profile-page.app-appearance-active .list-item-hover,
.profile-page.app-appearance-active .quick-item-hover {
  background: var(--app-color-primary-bg);
}
</style>
