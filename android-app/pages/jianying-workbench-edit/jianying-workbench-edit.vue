<template>
<view class="jy-edit-page">
  <view class="jy-statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="jy-edit-topbar">
    <view class="jy-back" @tap="goBack">‹ 返回</view>
    <text class="jy-topbar-title">编辑剪映控制</text>
    <view class="jy-done" @tap="goBack">完成</view>
  </view>

  <scroll-view class="jy-edit-scroll" scroll-y>
    <view class="jy-edit-content">
      <view class="jy-section-head">
        <text>2 × 4 快捷键</text>
        <text>点击编辑 · 按住排序</text>
      </view>
      <view class="jy-card jy-key-card">
        <view class="jy-edit-grid">
          <view
            v-for="(item, index) in config.shortcuts"
            :key="item.id || index"
            class="jy-edit-key"
            :class="{ selected: dragState && dragState.index === index }"
            @tap="editShortcut(index)"
            @touchstart="onDragStart($event, index)"
            @touchmove.stop.prevent="onDragMove"
            @touchend="onDragEnd"
            @touchcancel="onDragEnd"
          >
            <text class="jy-key-index">{{ padIndex(index) }}</text>
            <text class="jy-key-drag">⠿</text>
            <text class="jy-key-label">{{ item.label }}</text>
            <text class="jy-key-sub">{{ item.sub }}</text>
          </view>
        </view>
      </view>
      <view class="jy-two-actions">
        <view class="jy-button jy-button-primary" @tap="editShortcut(0)">＋ 编辑快捷键</view>
        <view class="jy-button" @tap="resetShortcuts">↺ 重置按键</view>
      </view>

      <view class="jy-section-head jy-timeline-heading">
        <text>时间轴控制区</text>
        <text>点击下方按键可编辑</text>
      </view>
      <view class="jy-card jy-timeline-card">
        <view class="jy-timeline-preview" :class="{ disabled: !config.timeline.enabled }">
          <view class="jy-timeline-head"><text>时间轴手势区</text><text class="jy-size-badge">4 × 2</text></view>
          <view class="jy-ruler"><view class="jy-ruler-marks"></view></view>
          <view class="jy-playhead"></view>
          <view class="jy-preview-actions">
            <view v-for="(item, index) in config.timelineButtons" :key="item.id || index" class="jy-preview-key" @tap.stop="editTimelineButton(index)">
              <text>{{ timelineButtonSymbol(index) }}</text><text>{{ item.label }}</text>
            </view>
          </view>
        </view>
      </view>
      <view class="jy-two-actions">
        <view class="jy-button jy-button-primary" @tap="editGestures">✎ 编辑手势</view>
        <view class="jy-button" @tap="toggleTimeline">{{ config.timeline.enabled ? '⊘ 暂停手势区' : '▶ 启用手势区' }}</view>
      </view>

      <view class="jy-card jy-settings-card">
        <view class="jy-setting-row" @tap="editShortcut(0)">
          <view class="jy-setting-icon">⌘</view>
          <view class="jy-setting-copy"><text>快捷键方案</text><text>复用现有快捷键选择与录入</text></view><text class="jy-chevron">›</text>
        </view>
        <view class="jy-setting-row">
          <view class="jy-setting-icon">◎</view>
          <view class="jy-setting-copy"><text>作用于当前窗口</text><text>不再绑定或强制切换剪映窗口</text></view>
        </view>
      </view>
      <view class="jy-safe"></view>
    </view>
  </scroll-view>
</view>
</template>

<script>
import { WORKBENCH_CONFIG_CHANGED_EVENT, defaultConfig, loadWorkbenchConfig, moveShortcut, normalizeWorkbenchScope, saveWorkbenchConfig, updateTimeline } from '@/utils/jianyingWorkbenchConfig.js'

function nativeStatusBarHeight() {
  let height = 24
  try {
    const windowInfo = typeof uni.getWindowInfo === 'function' ? uni.getWindowInfo() : null
    height = Math.max(height, Number(windowInfo && windowInfo.statusBarHeight) || 0, Number(windowInfo && windowInfo.safeArea && windowInfo.safeArea.top) || 0)
  } catch (e) {}
  try {
    const systemInfo = uni.getSystemInfoSync()
    height = Math.max(height, Number(systemInfo && systemInfo.statusBarHeight) || 0, Number(systemInfo && systemInfo.safeArea && systemInfo.safeArea.top) || 0)
  } catch (e) {}
  return height
}

export default {
  data() {
    return { scope: 'default', config: defaultConfig(), dragState: null, suppressTap: false, statusBarHeight: 24, _configChangedListener: null }
  },
  onLoad(options) {
    this.statusBarHeight = nativeStatusBarHeight()
    this.scope = normalizeWorkbenchScope(options && options.scope)
    this.config = loadWorkbenchConfig(this.scope)
    this._configChangedListener = (payload) => {
      if (!payload || payload.scope !== this.scope) return
      this.config = payload.config || loadWorkbenchConfig(this.scope)
    }
    if (typeof uni.$on === 'function') uni.$on(WORKBENCH_CONFIG_CHANGED_EVENT, this._configChangedListener)
  },
  onShow() {
    this.config = loadWorkbenchConfig(this.scope)
  },
  onUnload() {
    if (this._configChangedListener && typeof uni.$off === 'function') uni.$off(WORKBENCH_CONFIG_CHANGED_EVENT, this._configChangedListener)
    this._configChangedListener = null
  },
  methods: {
    padIndex(index) { return String(index + 1).padStart(2, '0') },
    goBack() { uni.navigateBack({ delta: 1 }) },
    persist(next) {
      const saved = saveWorkbenchConfig(this.scope, next)
      if (saved) this.config = saved
      else uni.showToast({ title: '保存失败，请重试', icon: 'none' })
    },
    editShortcut(index) {
      if (this.suppressTap) { this.suppressTap = false; return }
      const url = '/pages/layout/edit-key?source=jianying&scope=' + encodeURIComponent(this.scope) + '&slot=' + index
      const self = this
      uni.navigateTo({
        url: url,
        events: {
          saved(payload) {
            if (payload && payload.scope === self.scope && payload.config) self.config = payload.config
            else self.config = loadWorkbenchConfig(self.scope)
          },
        },
      })
    },
    editGestures() {
      uni.navigateTo({ url: '/pages/jianying-gestures-edit/jianying-gestures-edit?scope=' + encodeURIComponent(this.scope) })
    },
    timelineButtonSymbol(index) { return ['←', '→', '⇤', '⇥'][index] || '·' },
    editTimelineButton(index) {
      const url = '/pages/layout/edit-key?source=jianying&area=timeline&scope=' + encodeURIComponent(this.scope) + '&slot=' + index
      const self = this
      uni.navigateTo({
        url: url,
        events: {
          saved(payload) {
            if (payload && payload.scope === self.scope && payload.config) self.config = payload.config
            else self.config = loadWorkbenchConfig(self.scope)
          },
        },
      })
    },
    toggleTimeline() {
      this.persist(updateTimeline(this.config, { enabled: !this.config.timeline.enabled }))
      try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
    },
    resetShortcuts() {
      const self = this
      uni.showModal({
        title: '重置快捷键',
        content: '将上方 8 个按键恢复为默认剪映方案，手势设置保持不变。',
        success(result) {
          if (!result.confirm) return
          const defaults = defaultConfig()
          self.persist(Object.assign({}, self.config, { shortcuts: defaults.shortcuts }))
        },
      })
    },
    onDragStart(event, index) {
      const touch = event && event.touches && event.touches[0]
      if (!touch) return
      this.dragState = { index: index, startX: touch.clientX, startY: touch.clientY, moved: false }
    },
    onDragMove(event) {
      if (!this.dragState) return
      const touch = event && event.touches && event.touches[0]
      if (!touch) return
      const dx = touch.clientX - this.dragState.startX
      const dy = touch.clientY - this.dragState.startY
      if (Math.abs(dx) < 34 && Math.abs(dy) < 34) return
      const colStep = Math.round(dx / 82)
      const rowStep = Math.round(dy / 72)
      const from = this.dragState.index
      const row = Math.floor(from / 4)
      const col = from % 4
      const nextRow = Math.max(0, Math.min(1, row + rowStep))
      const nextCol = Math.max(0, Math.min(3, col + colStep))
      const to = nextRow * 4 + nextCol
      if (to === from) return
      this.config = moveShortcut(this.config, from, to)
      this.dragState.index = to
      this.dragState.startX = touch.clientX
      this.dragState.startY = touch.clientY
      this.dragState.moved = true
      this.suppressTap = true
    },
    onDragEnd() {
      if (this.dragState && this.dragState.moved) this.persist(this.config)
      this.dragState = null
      if (this.suppressTap) setTimeout(() => { this.suppressTap = false }, 120)
    },
  },
}
</script>

<style scoped>
.jy-edit-page { height: 100vh; overflow: hidden; display: flex; flex-direction: column; background: var(--app-color-bg, #EDF4FA); color: var(--app-color-text, #172638); }
.jy-statusbar-spacer { width: 100%; flex: 0 0 auto; background: var(--app-surface-strong, #FFFFFF); }
.jy-edit-topbar { height: 92rpx; padding: 0 24rpx; flex: 0 0 auto; display: grid; grid-template-columns: 120rpx 1fr 120rpx; align-items: center; border-bottom: 1rpx solid var(--app-color-border, #DCE6EF); background: var(--app-surface-strong, #FFFFFF); }
.jy-back { color: var(--app-color-text-mid, #5D6E82); font-size: 24rpx; font-weight: 650; }.jy-topbar-title { font-size: 29rpx; font-weight: 750; text-align: center; }.jy-done { color: var(--app-color-primary, #2F78F6); font-size: 24rpx; font-weight: 700; text-align: right; }
.jy-edit-scroll { min-height: 0; flex: 1; }.jy-edit-content { padding: 28rpx 24rpx calc(40rpx + env(safe-area-inset-bottom)); }.jy-section-head { margin: 0 4rpx 14rpx; display: flex; justify-content: space-between; color: var(--app-color-text-mid, #596B80); font-size: 21rpx; font-weight: 700; }.jy-section-head text:last-child { color: var(--app-color-text-light, #909CAD); font-weight: 500; }.jy-timeline-heading { margin-top: 28rpx; }
.jy-card { overflow: hidden; border: 1rpx solid var(--app-color-border, #DCE6EF); border-radius: 14rpx; background: var(--app-surface-strong, #FFFFFF); box-shadow: 0 8rpx 24rpx rgba(44,64,87,0.06); }.jy-key-card { padding: 12rpx; }.jy-edit-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); grid-template-rows: repeat(2, 148rpx); gap: 10rpx; }
.jy-edit-key { min-width: 0; position: relative; display: flex; align-items: center; justify-content: center; flex-direction: column; border: 1rpx solid var(--app-color-border, #DCE5EE); border-radius: 13rpx; background: var(--app-surface-strong, #FFFFFF); }.jy-edit-key.selected { border: 3rpx solid var(--app-color-primary, #2F78F6); background: var(--app-color-primary-bg, #F1F7FF); box-shadow: 0 0 0 5rpx rgba(47,120,246,0.12); }.jy-key-index { position: absolute; top: 8rpx; left: 9rpx; color: #98A5B4; font-size: 14rpx; }.jy-key-drag { position: absolute; top: 7rpx; right: 9rpx; color: #9BA7B5; font-size: 17rpx; }.jy-key-label { max-width: 94%; overflow: hidden; font-size: 21rpx; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }.jy-key-sub { max-width: 92%; margin-top: 8rpx; overflow: hidden; color: var(--app-color-text-light, #8793A3); font-size: 15rpx; text-overflow: ellipsis; white-space: nowrap; }
.jy-two-actions { margin-top: 14rpx; display: grid; grid-template-columns: 1fr 1fr; gap: 12rpx; }.jy-button { height: 68rpx; display: flex; align-items: center; justify-content: center; border: 1rpx solid var(--app-color-border, #DCE6EF); border-radius: 12rpx; background: var(--app-surface-strong, #FFFFFF); color: var(--app-color-text-mid, #506278); font-size: 21rpx; font-weight: 700; }.jy-button-primary { border-color: rgba(47,120,246,0.32); background: var(--app-color-primary-bg, #EDF5FF); color: var(--app-color-primary, #2F78F6); }
.jy-timeline-card { padding: 12rpx; }.jy-timeline-preview { height: 250rpx; position: relative; overflow: hidden; border: 3rpx solid var(--app-color-primary, #2F78F6); border-radius: 12rpx; background: var(--app-surface-soft, #F8FBFE); box-shadow: 0 0 0 5rpx rgba(47,120,246,0.11); }.jy-timeline-preview.disabled { opacity: .48; filter: grayscale(.7); }.jy-timeline-head { height: 47rpx; padding: 0 13rpx; display: flex; align-items: center; border-bottom: 1rpx solid var(--app-color-border, #DFE8F0); font-size: 20rpx; font-weight: 700; }.jy-size-badge { margin-left: auto; padding: 4rpx 8rpx; border-radius: 6rpx; background: var(--app-color-primary, #2F78F6); color: #FFFFFF; font-size: 15rpx; }.jy-ruler { height: 58rpx; position: relative; border-bottom: 1rpx solid var(--app-color-border, #E2E9F0); }.jy-ruler-marks { height: 32rpx; position: absolute; top: 14rpx; right: 0; left: 0; background: repeating-linear-gradient(90deg,transparent 0 38rpx,#AAB7C5 38rpx 40rpx,transparent 40rpx 76rpx); }.jy-ruler-marks::after { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(90deg,transparent 0 152rpx,#6F8094 152rpx 156rpx,transparent 156rpx 304rpx); }.jy-playhead { width: 3rpx; position: absolute; top: 46rpx; bottom: 142rpx; left: 50%; background: var(--app-color-primary, #2F78F6); }.jy-preview-actions { height: 145rpx; padding: 12rpx; display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 8rpx; box-sizing: border-box; }.jy-preview-key { min-width:0;display:flex;align-items:center;justify-content:center;flex-direction:column;border:1rpx solid var(--app-color-border,#DCE5ED);border-radius:10rpx;background:var(--app-surface-strong,#FFF); }.jy-preview-key text:first-child { color:#38536D;font-size:27rpx;font-weight:700; }.jy-preview-key text:last-child { max-width:92%;margin-top:8rpx;overflow:hidden;color:var(--app-color-text-mid,#62758A);font-size:15rpx;font-weight:650;text-overflow:ellipsis;white-space:nowrap; }
.jy-settings-card { margin-top: 26rpx; }.jy-setting-row { min-height: 88rpx; padding: 0 18rpx; display: flex; align-items: center; border-top: 1rpx solid var(--app-color-border, #EBF0F4); }.jy-setting-row:first-child { border-top: 0; }.jy-setting-icon { width: 46rpx; height: 46rpx; display: flex; align-items: center; justify-content: center; margin-right: 14rpx; border-radius: 10rpx; background: var(--app-color-primary-bg, #EEF4FB); color: #4F75A6; font-size: 21rpx; }.jy-setting-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; }.jy-setting-copy text:first-child { font-size: 22rpx; font-weight: 700; }.jy-setting-copy text:last-child { margin-top: 5rpx; color: var(--app-color-text-light, #8B98A8); font-size: 16rpx; }.jy-chevron { color: #9BA7B4; font-size: 30rpx; }.jy-safe { height: 40rpx; }
</style>
