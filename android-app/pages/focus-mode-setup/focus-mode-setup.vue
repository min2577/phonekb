<template>
  <view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
    <view class="topbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="topbar-back" hover-class="topbar-back-hover" @tap="onBack">‹</view>
      <view class="topbar-center">
        <text class="topbar-title">设置专注模式</text>
        <text class="topbar-subtitle">选模式 · 选时长 · 选白名单</text>
      </view>
      <view class="topbar-spacer"></view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">模式</text>
      </view>
      <view class="mode-list">
        <view v-for="m in MODE_OPTIONS" :key="m.key"
              class="mode-row"
              :class="{ 'is-selected': cfg.mode === m.key }"
              hover-class="mode-row-hover"
              @tap="onPickMode(m.key)">
          <view class="mode-radio">
            <view class="mode-radio-dot" v-if="cfg.mode === m.key"></view>
          </view>
          <view class="mode-info">
            <text class="mode-label">{{ m.label }}</text>
            <text class="mode-desc">{{ m.desc }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">时长</text>
        <text class="section-meta">{{ formatDuration(cfg.durationSec) }}</text>
      </view>
      <view class="preset-row">
        <view v-for="p in PRESETS" :key="p.min"
              class="preset-chip"
              :class="{ 'is-selected': presetSelected(p) }"
              hover-class="preset-chip-hover"
              @tap="onPickPreset(p.min)">
          <text class="preset-chip-text">{{ p.min }} 分钟</text>
        </view>
        <view class="preset-chip"
              :class="{ 'is-selected': !isPresetMatched }"
              hover-class="preset-chip-hover"
              @tap="onPickCustom">
          <text class="preset-chip-text">自定义</text>
        </view>
      </view>
      <view v-if="!isPresetMatched" class="custom-row">
        <view class="custom-step" hover-class="custom-step-hover" @tap="onCustomStep(-60)">
          <text class="custom-step-icon">−</text>
        </view>
        <view class="custom-display">
          <text class="custom-display-value">{{ customMin }}</text>
          <text class="custom-display-unit">分钟</text>
        </view>
        <view class="custom-step" hover-class="custom-step-hover" @tap="onCustomStep(60)">
          <text class="custom-step-icon">＋</text>
        </view>
      </view>
    </view>

    <view v-if="cfg.mode === 'strict-lock'" class="section">
      <view class="section-head">
        <text class="section-title">严格程度</text>
      </view>
      <view class="strict-row">
        <view class="strict-item"
              :class="{ 'is-selected': cfg.strictMode }"
              hover-class="strict-item-hover"
              @tap="onPickStrict(true)">
          <text class="strict-icon">🔒</text>
          <text class="strict-label">严格</text>
          <text class="strict-sub">一周可紧急退出 2 次</text>
        </view>
        <view class="strict-item"
              :class="{ 'is-selected': !cfg.strictMode }"
              hover-class="strict-item-hover"
              @tap="onPickStrict(false)">
          <text class="strict-icon">🔓</text>
          <text class="strict-label">宽松</text>
          <text class="strict-sub">随时可退出</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">白名单</text>
        <text class="section-meta">{{ whitelistEntries.length }} 个</text>
      </view>
      <view class="whitelist-row" hover-class="whitelist-row-hover" @tap="onOpenWhitelist">
        <view class="whitelist-summary">
          <text class="whitelist-summary-line" v-if="whitelistEntries.length === 0">
            还没选 · 锁机期间将无法打开任何应用
          </text>
          <text class="whitelist-summary-line" v-else>
            {{ whitelistSummary }}
          </text>
        </view>
        <view class="whitelist-edit">
          <text class="whitelist-edit-text">管理</text>
          <text class="whitelist-edit-arrow">›</text>
        </view>
      </view>
      <view v-if="cfg.mode === 'strict-lock'" class="whitelist-hint">
        锁机期间只有白名单里的应用能用,其他全部无法操作
      </view>
    </view>

    <view class="footer-safe"></view>

    <view class="action-bar">
      <view class="btn-primary" hover-class="btn-primary-hover" @tap="onStart">
        <text class="btn-primary-text">开始专注</text>
      </view>
    </view>
  </view>
</template>

<script>
import {
  loadConfig,
  saveConfig,
  getDefaultConfig,
  MODE_OPTIONS,
  getWhitelistEntries,
  getWhitelistPackageNames,
} from '@/utils/focusConfig.js'
import {
  isAccessibilityEnabled,
  openAccessibilitySettings,
  isOverlayEnabled,
  openOverlaySettings,
  startFocus,
} from '@/utils/focusNative.js'

const PRESETS = [
  { min: 25 },
  { min: 50 },
  { min: 90 },
]

export default {
  data() {
    return {
      statusBarHeight: 24,
      MODE_OPTIONS: MODE_OPTIONS,
      PRESETS: PRESETS,
      cfg: getDefaultConfig(),
      customMin: 25,
      accessibilityEnabled: false,
      overlayEnabled: false,
    }
  },
  computed: {
    whitelistEntries() {
      return getWhitelistEntries(this.cfg)
    },
    whitelistSummary() {
      const list = this.whitelistEntries
      const names = list.slice(0, 3).map(function (e) { return e.name }).join('、')
      if (list.length > 3) return names + ' 等 ' + list.length + ' 个'
      return names
    },
    isPresetMatched() {
      const m = Math.round(this.cfg.durationSec / 60)
      return PRESETS.some(function (p) { return p.min === m })
    },
  },
  onLoad() {
    try {
      const sys = uni.getSystemInfoSync()
      if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight
    } catch (e) {}
    this.cfg = loadConfig()
    this.customMin = Math.max(1, Math.round(this.cfg.durationSec / 60))
    this._refreshPermission()
  },
  onShow() {
    // 从白名单页返回时重新加载
    this.cfg = loadConfig()
    this._refreshPermission()
  },
  methods: {
    _refreshPermission() {
      this.accessibilityEnabled = isAccessibilityEnabled()
      this.overlayEnabled = isOverlayEnabled()
    },
    onBack() {
      uni.navigateBack({ delta: 1, fail: function () { uni.switchTab({ url: '/pages/panel/panel' }) } })
    },
    onPickMode(key) {
      this.cfg.mode = key
    },
    presetSelected(p) {
      return Math.round(this.cfg.durationSec / 60) === p.min
    },
    onPickPreset(min) {
      this.cfg.durationSec = min * 60
      this.customMin = min
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onPickCustom() {
      // 进入自定义模式:如果当前时长是 preset 之一,跳到一个非 preset 的初始值(30 分钟)
      if (this.isPresetMatched) {
        this.customMin = 30
      }
      this.cfg.durationSec = this.customMin * 60
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onCustomStep(deltaMin) {
      const next = Math.max(1, Math.min(480, this.customMin + deltaMin))
      if (next === this.customMin) return
      this.customMin = next
      this.cfg.durationSec = next * 60
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    onPickStrict(v) { this.cfg.strictMode = !!v },
    onOpenWhitelist() {
      uni.navigateTo({ url: '/pages/focus-mode-whitelist/focus-mode-whitelist' })
    },
    formatDuration(sec) {
      sec = Math.max(0, Math.round(sec || 0))
      const m = Math.floor(sec / 60)
      if (m < 60) return m + ' 分钟'
      const h = Math.floor(m / 60)
      const mm = m % 60
      return h + ' 小时 ' + (mm ? mm + ' 分' : '')
    },
    onStart() {
      const self = this
      const proceed = function () {
        saveConfig(self.cfg)
        if (self.cfg.mode === 'strict-lock') {
          const started = startFocus(self.cfg.durationSec, getWhitelistPackageNames(self.cfg))
          if (!started) {
            uni.showModal({
              title: '无法启动专注服务',
              content: 'Android 后台服务没有启动成功，请检查通知权限和电池优化设置后重试。',
              showCancel: false,
            })
            return
          }
        }
        uni.redirectTo({ url: '/pages/focus-mode-running/focus-mode-running' })
      }
      if (this.cfg.mode === 'strict-lock' && !this.accessibilityEnabled) {
        uni.showModal({
          title: '需要开启无障碍服务',
          content: '严格应用阻断依赖 Android 无障碍服务。请在“无障碍 > 已下载的应用”中开启 PhoneKB，不是“显示在其他应用的上层”。开启后，非白名单应用会被拦截并返回 PhoneKB。',
          confirmText: '去开启',
          cancelText: '取消',
          success: function (res) {
            if (res.confirm && !openAccessibilitySettings()) {
              uni.showModal({
                title: '无法打开系统设置',
                content: '请手动打开“设置 > 系统设置 > 无障碍 > 已下载的应用”,找到 PhoneKB 并开启服务。',
                showCancel: false,
              })
            }
          },
        })
        return
      }
      if (this.cfg.mode === 'strict-lock' && !this.overlayEnabled) {
        uni.showModal({
          title: '需要允许悬浮窗覆盖',
          content: '锁机期间会在非白名单应用上显示触摸拦截层。请选择“允许显示在其他应用的上层”。',
          confirmText: '去开启',
          cancelText: '取消',
          success: function (res) {
            if (res.confirm && !openOverlaySettings()) {
              uni.showModal({
                title: '无法打开系统设置',
                content: '请手动打开“设置 > 应用 > 特殊应用权限 > 显示在其他应用的上层”，找到 PhoneKB 并允许。',
                showCancel: false,
              })
            }
          },
        })
        return
      }
      if (this.cfg.mode === 'strict-lock' && this.whitelistEntries.length === 0) {
        uni.showModal({
          title: '还没选白名单',
          content: '严格锁机模式下必须至少选 1 个白名单 App,否则电话都接不到。',
          confirmText: '去设置',
          cancelText: '仍要开始',
          success: function (res) {
            if (res.confirm) {
              uni.navigateTo({ url: '/pages/focus-mode-whitelist/focus-mode-whitelist' })
            } else if (res.cancel) {
              proceed()
            }
          },
        })
        return
      }
      proceed()
    },
  },
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding-bottom: 200rpx;
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}

.topbar {
  min-height: 92rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255,255,255,0.94);
  border-bottom: 1rpx solid #DCE6F1;
}
.topbar-back {
  width: 64rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #506177;
  font-size: 48rpx;
}
.topbar-back-hover { color: #2F78F6; }
.topbar-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rpx;
}
.topbar-title { font-size: 32rpx; font-weight: 750; color: #172033; }
.topbar-subtitle { font-size: 20rpx; color: #8996A7; }
.topbar-spacer { width: 64rpx; height: 60rpx; }

.section {
  margin: 24rpx 24rpx 0;
  padding: 22rpx 24rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(47, 78, 113, 0.05);
}
.section-head {
  min-height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14rpx;
}
.section-title { font-size: 24rpx; font-weight: 700; color: #53657B; letter-spacing: 0.5rpx; }
.section-meta {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #EEF4FA;
  color: #718196;
  font-size: 22rpx;
  font-weight: 650;
}

/* ===== mode ===== */
.mode-list { display: flex; flex-direction: column; gap: 12rpx; }
.mode-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 18rpx 18rpx;
  border-radius: 18rpx;
  border: 2rpx solid #E8EEF5;
  transition: border-color 120ms, background-color 120ms;
}
.mode-row-hover { background: #F7FAFE; }
.mode-row.is-selected {
  border-color: #2F78F6;
  background: rgba(47, 120, 246, 0.06);
}
.mode-radio {
  width: 36rpx; height: 36rpx;
  border-radius: 50%;
  border: 2rpx solid #C7D2DE;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.mode-row.is-selected .mode-radio { border-color: #2F78F6; }
.mode-radio-dot {
  width: 18rpx; height: 18rpx;
  border-radius: 50%;
  background: #2F78F6;
}
.mode-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4rpx; }
.mode-label { font-size: 28rpx; font-weight: 700; color: #172033; }
.mode-desc { font-size: 22rpx; color: #7E8B9E; }

/* ===== preset ===== */
.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}
.preset-chip {
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: #F1F5F9;
  color: #506177;
  font-size: 24rpx;
  font-weight: 600;
}
.preset-chip-hover { background: #E2E8F0; }
.preset-chip.is-selected {
  background: rgba(47, 120, 246, 0.10);
  color: #2F78F6;
  box-shadow: inset 0 0 0 2rpx #2F78F6;
}
.preset-chip-text { font-size: 24rpx; }

.custom-row {
  margin-top: 18rpx;
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 12rpx 20rpx;
  background: #F1F5F9;
  border-radius: 18rpx;
}
.custom-step {
  width: 96rpx; height: 96rpx;
  border-radius: 50%;
  background: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4rpx 14rpx rgba(47, 120, 246, 0.18);
  transition: transform 80ms ease-out;
}
.custom-step-hover { background: #EAF3FF; transform: scale(0.95); }
.custom-step-icon { font-size: 48rpx; color: #2F78F6; font-weight: 700; line-height: 1; }
.custom-display { flex: 1; text-align: center; display: flex; flex-direction: column; align-items: center; }
.custom-display-value { font-size: 48rpx; font-weight: 800; color: #172033; font-family: Consolas, monospace; }
.custom-display-unit { font-size: 22rpx; color: #7E8B9E; margin-top: -4rpx; }

/* ===== strict ===== */
.strict-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12rpx;
}
.strict-item {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  border: 2rpx solid #E8EEF5;
  background: #FFFFFF;
  text-align: center;
}
.strict-item.is-selected {
  border-color: #2F78F6;
  background: rgba(47, 120, 246, 0.06);
}
.strict-item-hover { background: #F7FAFE; }
.strict-icon { font-size: 36rpx; line-height: 1; }
.strict-label { font-size: 28rpx; font-weight: 700; color: #172033; }
.strict-sub { font-size: 20rpx; color: #7E8B9E; }

/* ===== whitelist ===== */
.whitelist-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 18rpx;
  border-radius: 18rpx;
  background: #F7FAFE;
  border: 2rpx solid #E8EEF5;
}
.whitelist-row-hover { background: #EEF4FA; }
.whitelist-summary { flex: 1; min-width: 0; }
.whitelist-summary-line { font-size: 26rpx; color: #172033; line-height: 1.4; }
.whitelist-edit {
  display: flex; align-items: center; gap: 4rpx;
  padding: 8rpx 16rpx;
  background: #2F78F6;
  border-radius: 999rpx;
}
.whitelist-edit-text { font-size: 22rpx; color: #FFFFFF; font-weight: 600; }
.whitelist-edit-arrow { font-size: 22rpx; color: #FFFFFF; line-height: 1; }
.whitelist-hint {
  margin-top: 12rpx;
  padding: 10rpx 14rpx;
  font-size: 22rpx;
  color: #B95A18;
  background: rgba(245, 158, 11, 0.08);
  border-radius: 12rpx;
  line-height: 1.4;
}

.footer-safe { height: 48rpx; }

.action-bar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  padding: 18rpx 24rpx calc(28rpx + env(safe-area-inset-bottom));
  background: rgba(244, 248, 253, 0.96);
  border-top: 1rpx solid #DCE6F1;
  backdrop-filter: blur(24rpx);
}
.btn-primary {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 96rpx;
  background: #2F78F6;
  color: #FFFFFF;
  border-radius: 22rpx;
  font-size: 32rpx;
  font-weight: 700;
}
.btn-primary-hover { background: #1E5BD0; }
.btn-primary-text { font-size: 32rpx; font-weight: 700; color: #FFFFFF; }
</style>
