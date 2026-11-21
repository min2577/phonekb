<template>
<view :class="['page', 'settings-page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>

  <view class="section">
    <view class="section-title">连接</view>
    <view class="row"><text class="label">自动重连</text><switch :checked="settings.autoReconnect" data-k="autoReconnect" @change="onToggle" /></view>
    <view class="row"><text class="label">重连次数上限</text><view class="stepper"><view class="step-btn" data-k="maxReconnect" data-step="-1" @tap="onStepper">−</view><text class="step-val">{{settings.maxReconnect}}</text><view class="step-btn" data-k="maxReconnect" data-step="1" @tap="onStepper">+</view></view></view>
    <view class="row"><text class="label">心跳间隔 (秒)</text><view class="stepper"><view class="step-btn" data-k="heartbeatSec" data-step="-5" @tap="onStepper">−</view><text class="step-val">{{settings.heartbeatSec}}</text><view class="step-btn" data-k="heartbeatSec" data-step="5" @tap="onStepper">+</view></view></view>
  </view>

  <view class="section">
    <view class="section-title">外观</view>
    <view class="appearance-mode" aria-label="全局外观模式">
      <view v-for="item in appearanceModes"
            :key="item.id"
            :class="['appearance-mode-item', appearanceMode === item.id ? 'active' : '']"
            :data-mode="item.id"
            @tap="onAppearanceModeTap">{{ item.label }}</view>
    </view>
    <view class="row" @tap="onGoAppearance">
      <view class="appearance-row-copy">
        <text class="label">页面背景与透明度</text>
        <text class="appearance-row-sub">每个页面可单独设置</text>
      </view>
      <text class="arrow">›</text>
    </view>
    <view class="row"><text class="label">网格列数</text><view class="stepper"><view class="step-btn" data-k="gridCols" data-step="-1" @tap="onStepper">−</view><text class="step-val">{{settings.gridCols}}</text><view class="step-btn" data-k="gridCols" data-step="1" @tap="onStepper">+</view></view></view>
  </view>

  <view class="section">
    <view class="section-title">触控板</view>
    <view class="row"><text class="label">光标速度</text><view class="stepper"><view class="step-btn" data-k="touchpadSensitivity" data-step="-0.1" @tap="onStepper">−</view><text class="step-val">{{settings.touchpadSensitivity}}</text><view class="step-btn" data-k="touchpadSensitivity" data-step="0.1" @tap="onStepper">+</view></view></view>
    <view class="row"><text class="label">滚动速度</text><view class="stepper"><view class="step-btn" data-k="touchpadScrollSensitivity" data-step="-0.1" @tap="onStepper">−</view><text class="step-val">{{settings.touchpadScrollSensitivity}}</text><view class="step-btn" data-k="touchpadScrollSensitivity" data-step="0.1" @tap="onStepper">+</view></view></view>
    <view class="row"><text class="label">轻点点击</text><switch :checked="settings.touchpadTapToClick" data-k="touchpadTapToClick" @change="onToggle" /></view>
    <view class="row"><text class="label">轻点后再次按住拖动</text><switch :checked="settings.touchpadTapDrag" data-k="touchpadTapDrag" @change="onToggle" /></view>
    <view class="row"><text class="label">自然滚动</text><switch :checked="settings.touchpadNaturalScroll" data-k="touchpadNaturalScroll" @change="onToggle" /></view>
    <view class="row"><text class="label">滚动惯性</text><switch :checked="settings.touchpadInertia" data-k="touchpadInertia" @change="onToggle" /></view>
  </view>

  <view class="section">
    <view class="section-title">反馈</view>
    <view class="row"><text class="label">震动</text><switch :checked="settings.vibrate" data-k="vibrate" @change="onToggle" /></view>
    <view class="row"><text class="label">操作提示</text><switch :checked="settings.toast" data-k="toast" @change="onToggle" /></view>
  </view>

  <view class="section" @tap="onGoPanelScheme">
    <view class="row single">
      <text class="label">面板方案 (自由编排)</text>
      <text class="arrow">›</text>
    </view>
  </view>

  <view class="section" @tap="onGoTabConfig">
    <view class="row single">
      <text class="label">底部 Tab 栏 (换位置/隐藏/新增)</text>
      <text class="arrow">›</text>
    </view>
  </view>

  <view class="section" @tap="onGoAbout">
    <view class="row single">
      <text class="label">关于 / 日志 / 诊断</text>
      <text class="arrow">›</text>
    </view>
  </view>

  <view class="footer-actions">
    <view class="btn-danger" @tap="onResetSettings">恢复默认</view>
  </view>
  <view class="footer-safe"></view>
  <CustomTabBar />
</view>
</template>

<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
import WS from '@/utils/net.js'
import { applyAppearance, loadAppearance, updateAppearanceMode } from '@/utils/appearanceConfig.js'
import { DEFAULT_SETTINGS, loadSettings, saveSettings } from '@/utils/appSettings.js'
let app = null
try { app = getApp({ allowDefault: true }) } catch (e) {}

export default {
  components: { CustomTabBar },
  data() { return {
      statusBarHeight: 24,
    settings: Object.assign({}, DEFAULT_SETTINGS),
    serverInfo: null,
    hello: null,
      appearanceMode: 'light',
      appearanceModes: [
        { id: 'light', label: '日间' },
        { id: 'dark', label: '暗色' },
        { id: 'system', label: '跟随系统' },
      ],
  } },

  onShow() {
    const settings = Object.assign({}, loadSettings(), (app && app.globalData || {}).settings || {})
    this.settings = settings; this.hello = WS.getHello() || (() => { try { return uni.getStorageSync("phonekb.hello") } catch (e) { return null } })()
    this.appearanceMode = loadAppearance().mode
  },

    onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
_save() {
    this.settings = saveSettings(this.settings)
    if (app && app.globalData) app.globalData.settings = this.settings
  },

  onToggle(e) {
    const k = e.currentTarget.dataset.k
    const settings = Object.assign({}, this.settings)
    settings[k] = !!e.detail.value
    this.settings = settings
    this._save()
  },

  onStepper(e) {
    const k = e.currentTarget.dataset.k
    const step = Number(e.currentTarget.dataset.step)
    const settings = Object.assign({}, this.settings)
    let v = (settings[k] || 0) + step
    if (k === "heartbeatSec") v = Math.max(5, Math.min(60, v))
    if (k === "maxReconnect") v = Math.max(1, Math.min(50, v))
    if (k === "touchpadSensitivity") v = Math.max(0.5, Math.min(3, Math.round(v * 10) / 10))
    if (k === "touchpadScrollSensitivity") v = Math.max(0.5, Math.min(3, Math.round(v * 10) / 10))
    if (k === "gridCols") v = Math.max(3, Math.min(5, v))
    settings[k] = v
    this.settings = settings
    this._save()
    if (k === "gridCols") {
      WS.send({ action: "set_grid_cols", cols: v })
    }
  },

  onResetSettings() {
    const self = this
    uni.showModal({
      title: "重置设置",
      content: "把所有选项恢复默认？",
      success: function(res) {
        if (res.confirm) {
          self.settings = Object.assign({}, DEFAULT_SETTINGS)
          self._save()
        }
      },
    })
  },

  onGoAbout() {
    uni.navigateTo({ url: "/pages/about/about" })
  },
  onGoPanelScheme() {
    uni.navigateTo({ url: "/pages/panel-scheme/panel-scheme" })
  },
  onAppearanceModeTap(e) {
    const mode = e.currentTarget.dataset.mode
    this.appearanceMode = mode
    const config = updateAppearanceMode(mode)
    applyAppearance('settings', config)
    this.$refreshAppAppearance()
    try { uni.vibrateShort({ type: 'light' }) } catch (error) {}
  },
  onGoAppearance() {
    uni.navigateTo({ url: '/pages/appearance/appearance' })
  },
    onGoTabConfig() {
      uni.navigateTo({ url: "/pages/tab-config/tab-config" })
    },

  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 28rpx 24rpx calc(148rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
  overflow-x: hidden;
  background: radial-gradient(82% 36% at 12% 0%, rgba(47,120,246,0.12) 0%, rgba(244,248,253,0) 76%), var(--color-bg);
  color: var(--color-text);
}
.statusbar-spacer { width: 100%; }
.section {
  margin: 0 0 20rpx;
  padding: 0 26rpx;
  overflow: hidden;
  background: rgba(255,255,255,0.95);
  border: 1rpx solid var(--fluent-hairline);
  border-radius: 24rpx;
  box-shadow: var(--shadow-fluent-2);
}
.section-title {
  padding: 22rpx 0 10rpx;
  color: #8793A3;
  font-size: 23rpx;
  font-weight: 600;
  line-height: 1.2;
}
.appearance-mode {
  height: 68rpx;
  margin: 4rpx 0 10rpx;
  padding: 5rpx;
  display: flex;
  gap: 5rpx;
  border: 1rpx solid var(--color-border);
  border-radius: 16rpx;
  background: var(--color-bg-alt);
}
.appearance-mode-item {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 11rpx;
  color: var(--color-text-mid);
  font-size: 23rpx;
  font-weight: 650;
}
.appearance-mode-item.active {
  background: var(--app-surface-strong, #FFFFFF);
  color: var(--color-primary);
  box-shadow: 0 2rpx 7rpx rgba(45,74,108,0.10);
}
.appearance-row-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 5rpx; }
.appearance-row-sub { color: var(--color-text-mid); font-size: 20rpx; }
.row,
.account-row {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 16rpx 0;
  border-bottom: 1rpx solid var(--color-divider);
}
.row:last-child,
.account-row:last-child { border-bottom: 0; }
.row.single { min-height: 94rpx; }
.label {
  flex: 1;
  min-width: 0;
  color: var(--color-text);
  font-size: 28rpx;
  line-height: 1.35;
}
.arrow,
.account-action {
  flex-shrink: 0;
  color: #A3ADBA;
  font-size: 36rpx;
  line-height: 1;
}
.account-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
  min-height: 112rpx;
  margin-bottom: 10rpx;
  padding: 18rpx 18rpx;
  background: #F7FAFE;
  border: 1rpx solid rgba(111,139,170,0.12);
  border-radius: 18rpx;
}
.account-card-hover { background: #EEF6FF; }
.account-avatar,
.account-wechat-icon {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #FFFFFF;
  font-size: 30rpx;
  font-weight: 650;
}
.account-avatar {
  border-radius: 22rpx;
  background: linear-gradient(145deg, #3DC77A 0%, #07A757 100%);
}
.account-wechat-icon {
  border-radius: 18rpx;
  background: #07C160;
}
.account-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.account-name {
  color: var(--color-text);
  font-size: 28rpx;
  font-weight: 650;
}
.account-sub {
  overflow: hidden;
  color: var(--color-text-mid);
  font-size: 21rpx;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-btn {
  flex-shrink: 0;
  padding: 12rpx 18rpx;
  background: #07B85C;
  border-radius: 14rpx;
  color: #FFFFFF;
  font-size: 23rpx;
  font-weight: 650;
  box-shadow: 0 5rpx 13rpx rgba(7,184,92,0.20);
}
.account-row .label { font-size: 28rpx; }
.tag {
  flex-shrink: 0;
  padding: 5rpx 12rpx;
  border-radius: 10rpx;
  background: #F1F5F9;
  color: #8793A3;
  font-size: 21rpx;
  font-weight: 600;
}
.tag.tag-on { background: #EAF8EF; color: #178B47; }
.stepper { display: flex; align-items: center; flex-shrink: 0; }
.step-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F7FAFE;
  border: 1rpx solid var(--color-border);
  border-radius: 16rpx;
  color: var(--color-primary);
  font-size: 32rpx;
  font-weight: 500;
  line-height: 1;
}
.step-btn:active { background: var(--color-primary-bg); transform: scale(0.96); }
.step-val {
  width: 88rpx;
  color: var(--color-text);
  font-size: 27rpx;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
switch { transform: scale(0.88); transform-origin: right center; }
.footer-actions { display: flex; padding: 2rpx 0 16rpx; }
.btn-danger {
  flex: 1;
  min-height: 78rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #FDECEE;
  border: 1rpx solid #F4C9CD;
  border-radius: 18rpx;
  color: #C43F48;
  font-size: 27rpx;
  font-weight: 650;
}
.btn-danger:active { background: #F9DADD; transform: scale(0.98); }
.footer-safe { height: 20rpx; }
</style>
