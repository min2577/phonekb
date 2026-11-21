<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="brand-card">
    <view class="brand-icon">⌨</view>
    <text class="brand-name">手机键盘</text>
    <text class="brand-version">v{{ appVersion }}</text>
  </view>

  <view class="info-card">
    <view class="card-heading"><view class="heading-icon">链</view><text class="heading-title">连接信息</text></view>
    <view v-if="hello" class="info-row"><text class="info-label">服务器</text><text class="info-value">{{ hello.server }}</text></view>
    <view v-if="hello" class="info-row"><text class="info-label">协议版本</text><text class="info-value">{{ hello.proto }}</text></view>
    <view v-if="hello" class="info-row"><text class="info-label">布局数量</text><text class="info-value">{{ cached.layouts.length }}</text></view>
    <view v-if="hello" class="info-row"><text class="info-label">全局页面</text><text class="info-value">{{ cached.global_pages.length }}</text></view>
    <view v-if="!hello" class="empty-state">尚未连接服务器</view>
  </view>

  <view class="info-card action-card">
    <view class="card-heading"><view class="heading-icon">快</view><text class="heading-title">快捷操作</text></view>
    <view class="action-row" @tap="onCopyHello"><text class="action-label">复制握手信息</text><text class="action-arrow">›</text></view>
    <view class="action-row" @tap="onExportLogs"><text class="action-label">导出诊断数据</text><text class="action-arrow">›</text></view>
  </view>

  <view class="footer-safe"></view>
</view>
</template>

<script>
import WS from '@/utils/net.js'

export default {
  data() { return {
      statusBarHeight: 24,
    hello: null,
    cached: { layouts: [], global_pages: [] },
    appVersion: "0.3.3",
  } },

  onShow() {
    this.hello = WS.getHello() || (() => { try { return uni.getStorageSync("phonekb.hello") } catch (e) { return null } })()
    this.cached = (() => { try { return uni.getStorageSync("phonekb.last_layouts") || { layouts: [], global_pages: [] } } catch (e) { return { layouts: [], global_pages: [] } } })()
  },

    onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
onExportLogs() {
    try {
      const obj = {
        app: this.appVersion,
        hello: this.hello,
        layouts: this.cached,
        ts: new Date().toISOString(),
      }
      uni.setStorageSync("phonekb.diagnostic", obj)
      uni.setClipboardData({ data: JSON.stringify(obj) })
      uni.showModal({
        title: "诊断数据已复制",
        content: "可以直接粘贴给开发者。",
        showCancel: false,
      })
    } catch (e) {
      uni.showToast({ title: "导出失败", icon: "none" })
    }
  },

    onCopyHello() {
    if (!this.hello) { uni.showToast({ title: "尚未握手", icon: "none" }); return }
    uni.setClipboardData({ data: JSON.stringify(this.hello) })
  }
  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 20rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}
.brand-card,
.info-card {
  margin: 0 8rpx 16rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(47, 78, 113, 0.06);
}
.brand-card {
  padding: 30rpx 24rpx 26rpx;
  display: flex;
  align-items: center;
  flex-direction: column;
}
.brand-icon,
.heading-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #EAF3FF;
  color: #2F78F6;
  font-weight: 700;
}
.brand-icon {
  width: 74rpx;
  height: 74rpx;
  border-radius: 20rpx;
  font-size: 38rpx;
}
.brand-name {
  margin-top: 14rpx;
  color: #172033;
  font-size: 31rpx;
  font-weight: 750;
}
.brand-version {
  margin-top: 8rpx;
  padding: 4rpx 11rpx;
  border-radius: 10rpx;
  background: #EEF4FA;
  color: #6D7D91;
  font-size: 18rpx;
}
.info-card {
  padding: 18rpx 20rpx 6rpx;
}
.card-heading {
  min-height: 54rpx;
  display: flex;
  align-items: center;
  margin-bottom: 10rpx;
}
.heading-icon {
  width: 46rpx;
  height: 46rpx;
  margin-right: 14rpx;
  border-radius: 13rpx;
  font-size: 19rpx;
}
.heading-title {
  color: #172033;
  font-size: 25rpx;
  font-weight: 700;
}
.info-row,
.action-row {
  min-height: 66rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1rpx solid #E8EEF5;
}
.info-label {
  color: #6F7D91;
  font-size: 21rpx;
}
.info-value {
  color: #172033;
  font-size: 21rpx;
  font-weight: 650;
}
.empty-state {
  padding: 32rpx 0;
  color: #8B97A8;
  font-size: 21rpx;
  text-align: center;
}
.action-label {
  color: #172033;
  font-size: 23rpx;
  font-weight: 600;
}
.action-arrow {
  color: #91A0B2;
  font-size: 35rpx;
}
.footer-safe {
  height: 30rpx;
}

.statusbar-spacer { width: 100%; }
</style>
