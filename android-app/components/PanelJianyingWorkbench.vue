<template>
  <view class="jy-console">
    <view class="jy-shortcut-grid">
      <view
        v-for="(item, index) in config.shortcuts"
        :key="item.id || index"
        class="jy-key"
        :class="{ primary: index === 0, offline: !keyboardAvailable }"
        hover-class="jy-key-hover"
        @tap="triggerShortcut(item)"
      >
        <text class="jy-key-label">{{ item.label }}</text>
        <text class="jy-key-sub">{{ item.sub }}</text>
      </view>
    </view>

    <view
      class="jy-timeline-pad"
      :class="{ active: gestureActive, disabled: !config.timeline.enabled, offline: timelineHasActions && !timelineAvailable }"
      @touchstart.stop.prevent="onTouchStart"
      @touchmove.stop.prevent="onTouchMove"
      @touchend.stop.prevent="onTouchEnd"
      @touchcancel.stop.prevent="onTouchCancel"
    >
      <view class="jy-pad-head">
        <view class="jy-pad-copy">
          <text class="jy-pad-title">时间轴手势区</text>
          <text class="jy-pad-state">{{ padStateLabel }}</text>
        </view>
        <text class="jy-speed-value">移动 {{ swipeRateLabel }}</text>
        <text class="jy-zoom-value">{{ zoomPercent }}%</text>
      </view>
      <view class="jy-ruler">
        <view class="jy-ruler-marks" :style="rulerStyle"></view>
      </view>
      <view class="jy-playhead"><view class="jy-playhead-cap"></view></view>
      <view class="jy-gesture-cue"><text>单指滚动</text><text>双指缩放</text></view>
      <view class="jy-quick-actions">
        <view class="jy-action-group">
          <view class="jy-action-key editable" :class="{ offline: !keyboardAvailable }" hover-class="jy-action-key-hover" @touchstart.stop @touchmove.stop.prevent @touchend.stop @touchcancel.stop @tap.stop="triggerShortcut(config.timelineButtons[0])">
            <text class="jy-action-symbol">←</text><text class="jy-action-label">{{ config.timelineButtons[0].label }}</text>
          </view>
          <view class="jy-action-key editable" :class="{ offline: !keyboardAvailable }" hover-class="jy-action-key-hover" @touchstart.stop @touchmove.stop.prevent @touchend.stop @touchcancel.stop @tap.stop="triggerShortcut(config.timelineButtons[1])">
            <text class="jy-action-symbol">→</text><text class="jy-action-label">{{ config.timelineButtons[1].label }}</text>
          </view>
        </view>
        <view class="jy-action-group">
          <view class="jy-action-key editable" :class="{ offline: !keyboardAvailable }" hover-class="jy-action-key-hover" @touchstart.stop @touchmove.stop.prevent @touchend.stop @touchcancel.stop @tap.stop="triggerShortcut(config.timelineButtons[2])">
            <text class="jy-action-symbol">⇤</text><text class="jy-action-label">{{ config.timelineButtons[2].label }}</text>
          </view>
          <view class="jy-action-key editable" :class="{ offline: !keyboardAvailable }" hover-class="jy-action-key-hover" @touchstart.stop @touchmove.stop.prevent @touchend.stop @touchcancel.stop @tap.stop="triggerShortcut(config.timelineButtons[3])">
            <text class="jy-action-symbol">⇥</text><text class="jy-action-label">{{ config.timelineButtons[3].label }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { markRaw } from 'vue'
import Net from '@/utils/net.js'
import { WORKBENCH_CONFIG_CHANGED_EVENT, getGestureAction, loadWorkbenchConfig } from '@/utils/jianyingWorkbenchConfig.js'
import { consumeGestureSteps, messageForGestureAction, scaleForPinch, thresholdFor, touchCoordinate, touchDistance } from '@/utils/jianyingGesture.js'

function firstTouch(event) {
  return event && event.touches && event.touches[0]
}

export default {
  name: 'PanelJianyingWorkbench',
  props: {
    storageScope: { type: String, default: 'default' },
    configRevision: { type: Number, default: 0 },
    preview: { type: Boolean, default: false },
  },
  data() {
    return {
      config: loadWorkbenchConfig(this.storageScope),
      keyboardAvailable: Net.canSendKeyboard(),
      mouseAvailable: Net.canSendMouse(),
      rulerOffset: 0,
      rulerScale: 1,
      activeGestureMode: '',
      gesture: markRaw({
        mode: '',
        lastX: 0,
        lastDistance: 0,
        swipeRemainder: 0,
        pinchRemainder: 0,
        lastHapticAt: 0,
      }),
    }
  },
  computed: {
    gestureActive() { return !!this.activeGestureMode },
    zoomPercent() { return Math.round(this.rulerScale * 100) },
    swipeRate() { return Number(this.config.timeline.swipeMultiplier) || 1 },
    swipeRateLabel() { return this.swipeRate.toFixed(1) + '×' },
    timelineAvailable() {
      return this.gestureActionAvailable(this.config.timeline.swipeLeft)
        || this.gestureActionAvailable(this.config.timeline.swipeRight)
        || this.gestureActionAvailable(this.config.timeline.pinchOut)
        || this.gestureActionAvailable(this.config.timeline.pinchIn)
    },
    timelineHasActions() {
      const timeline = this.config.timeline
      return [timeline.swipeLeft, timeline.swipeRight, timeline.pinchOut, timeline.pinchIn]
        .some((id) => getGestureAction(id).type !== 'none')
    },
    padStateLabel() {
      if (!this.config.timeline.enabled) return '已暂停'
      if (!this.timelineHasActions) return '未配置手势'
      if (!this.timelineAvailable) return '电脑未连接'
      if (this.activeGestureMode === 'pinch') return '正在缩放'
      if (this.activeGestureMode === 'swipe') return '正在移动'
      return '单指滚动 · 双指缩放'
    },
    rulerStyle() {
      return { transform: 'translateX(' + this.rulerOffset + 'rpx) scaleX(' + this.rulerScale.toFixed(3) + ')' }
    },
  },
  watch: {
    storageScope() { this.reloadConfig() },
    configRevision() { this.reloadConfig() },
  },
  mounted() {
    this._onWorkbenchConfigChanged = (payload) => {
      if (!payload || payload.scope !== this.storageScope) return
      this.config = payload.config || loadWorkbenchConfig(this.storageScope)
      this.resetGesture()
    }
    if (typeof uni.$on === 'function') uni.$on(WORKBENCH_CONFIG_CHANGED_EVENT, this._onWorkbenchConfigChanged)
    this._onNetState = () => { this.refreshInputAvailability() }
    this._onHidState = () => { this.refreshInputAvailability() }
    try { Net.onStateChange(this._onNetState) } catch (e) {}
    try { Net.onHidStateChange(this._onHidState) } catch (e) {}
    this.refreshInputAvailability()
  },
  beforeUnmount() {
    if (this._onWorkbenchConfigChanged && typeof uni.$off === 'function') uni.$off(WORKBENCH_CONFIG_CHANGED_EVENT, this._onWorkbenchConfigChanged)
    try { Net.offStateChange(this._onNetState) } catch (e) {}
    try { Net.offHidStateChange(this._onHidState) } catch (e) {}
  },
  methods: {
    setGestureMode(mode) {
      this.gesture.mode = mode
      this.activeGestureMode = mode
    },
    refreshInputAvailability() {
      this.keyboardAvailable = Net.canSendKeyboard()
      this.mouseAvailable = Net.canSendMouse()
    },
    reloadConfig() {
      this.config = loadWorkbenchConfig(this.storageScope)
      this.resetGesture()
    },
    gestureActionAvailable(actionId) {
      const action = getGestureAction(actionId)
      if (action.type === 'none') return false
      if (action.type === 'mouse_zoom' || action.type === 'mouse_wheel') return this.mouseAvailable
      if (action.type === 'shortcut') return this.keyboardAvailable
      return false
    },
    updateRulerScale(previousDistance, nextDistance) {
      if (previousDistance <= 0 || nextDistance <= 0 || previousDistance === nextDistance) return
      this.rulerScale = scaleForPinch(
        this.rulerScale,
        previousDistance,
        nextDistance,
        0.42,
        3.2,
        this.config.timeline.pinchMultiplier
      )
    },
    triggerShortcut(item) {
      if (this.preview) return
      if (!this.keyboardAvailable) {
        uni.showToast({ title: '请先连接电脑端', icon: 'none' })
        return
      }
      const shortcut = item && item.shortcut
      if (!shortcut) return
      const sent = Net.send({
        action: 'simulate_key',
        modifiers: Array.isArray(shortcut.modifiers) ? shortcut.modifiers : [],
        key: String(shortcut.key || ''),
      })
      if (sent) {
        const feedback = item.feedback || {}
        if (feedback.vibrate !== false) try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
        if (feedback.toast) uni.showToast({ title: item.label || '已发送', icon: 'none', duration: 500 })
      }
    },
    onTouchStart(event) {
      if (this.preview || !this.config.timeline.enabled) return
      const touches = event.touches || []
      const mode = touches.length >= 2 ? 'pinch' : 'swipe'
      if (mode === 'pinch') {
        this.setGestureMode('pinch')
        this.gesture.lastDistance = touchDistance(touches)
        this.gesture.pinchRemainder = 0
      } else {
        const touch = firstTouch(event)
        if (!touch) return
        this.setGestureMode('swipe')
        this.gesture.lastX = touchCoordinate(touch, 'x')
        this.gesture.swipeRemainder = 0
      }
    },
    onTouchMove(event) {
      if (this.preview || !this.config.timeline.enabled || !this.gesture.mode) return
      const touches = event.touches || []
      if (touches.length >= 2) {
        const distance = touchDistance(touches)
        if (this.gesture.mode !== 'pinch') {
          this.setGestureMode('pinch')
          this.gesture.lastDistance = distance
          this.gesture.pinchRemainder = 0
          return
        }
        this.updateRulerScale(this.gesture.lastDistance, distance)
        this.gesture.pinchRemainder += (distance - this.gesture.lastDistance) * this.config.timeline.pinchMultiplier
        this.gesture.lastDistance = distance
        const consumed = consumeGestureSteps(this.gesture.pinchRemainder, thresholdFor(this.config.timeline.sensitivity, 'pinch'), 8)
        this.gesture.pinchRemainder = consumed.remaining
        if (consumed.steps) this.sendDirectionalActions(consumed.steps, this.config.timeline.pinchOut, this.config.timeline.pinchIn)
        return
      }
      const touch = firstTouch(event)
      if (!touch) return
      const x = touchCoordinate(touch, 'x')
      if (this.gesture.mode !== 'swipe') {
        this.setGestureMode('swipe')
        this.gesture.lastX = x
        this.gesture.swipeRemainder = 0
        return
      }
      const dx = x - this.gesture.lastX
      this.gesture.lastX = x
      const adjustedDx = dx * this.swipeRate
      this.gesture.swipeRemainder += adjustedDx
      this.rulerOffset = ((this.rulerOffset + adjustedDx * 0.7 + 36) % 72) - 36
      const consumed = consumeGestureSteps(this.gesture.swipeRemainder, thresholdFor(this.config.timeline.sensitivity, 'swipe'), 8)
      this.gesture.swipeRemainder = consumed.remaining
      if (consumed.steps) this.sendDirectionalActions(consumed.steps, this.config.timeline.swipeRight, this.config.timeline.swipeLeft)
    },
    onTouchEnd(event) {
      const touches = event && event.touches ? event.touches : []
      if (touches.length >= 2) {
        this.setGestureMode('pinch')
        this.gesture.lastDistance = touchDistance(touches)
        return
      }
      if (touches.length === 1) {
        this.setGestureMode('swipe')
        this.gesture.lastX = touchCoordinate(touches[0], 'x')
        this.gesture.swipeRemainder = 0
        return
      }
      this.resetGesture()
    },
    onTouchCancel() {
      this.resetGesture()
    },
    sendGestureAction(actionId, count) {
      const action = getGestureAction(actionId)
      if (!this.gestureActionAvailable(actionId)) return false
      const total = Math.min(8, Math.max(1, Math.abs(Number(count) || 1)))
      let sent = false
      for (let index = 0; index < total; index++) {
        const message = messageForGestureAction(action)
        if (message && Net.send(message)) sent = true
      }
      const now = Date.now()
      if (sent && now - this.gesture.lastHapticAt >= 70) {
        this.gesture.lastHapticAt = now
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      }
      return sent
    },
    sendDirectionalActions(steps, positiveActionId, negativeActionId) {
      const actionId = steps > 0 ? positiveActionId : negativeActionId
      const count = Math.min(8, Math.abs(steps))
      this.sendGestureAction(actionId, count)
    },
    resetGesture() {
      this.setGestureMode('')
      this.gesture.lastX = 0
      this.gesture.lastDistance = 0
      this.gesture.swipeRemainder = 0
      this.gesture.pinchRemainder = 0
      this.rulerOffset = 0
    },
  },
}
</script>

<style>
.jy-console { width: 100%; }
.jy-shortcut-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-template-rows: repeat(2, 142rpx); gap: 10rpx; }
.jy-key { min-width: 0; min-height: 142rpx; padding: 12rpx 7rpx; display: flex; align-items: center; justify-content: center; flex-direction: column; border: 1rpx solid var(--app-color-border, #DFE6EF); border-radius: 14rpx; background: var(--app-surface-strong, #FFFFFF); color: var(--app-color-text, #1E2B3C); box-shadow: 0 3rpx 8rpx rgba(43,72,106,0.07); text-align: center; }
.jy-key.primary { border-color: rgba(47,120,246,0.38); background: var(--app-color-primary-bg, #EEF6FF); color: var(--app-color-primary, #2F78F6); }
.jy-key-hover { transform: scale(0.975); border-color: rgba(47,120,246,0.46); background: var(--app-color-primary-bg, #EEF6FF); }
.jy-key.offline { opacity: 0.72; }
.jy-key-label { width: 100%; overflow: hidden; font-size: 26rpx; font-weight: 650; line-height: 1.15; text-overflow: ellipsis; white-space: nowrap; }
.jy-key-sub { max-width: 100%; margin-top: 9rpx; overflow: hidden; color: var(--app-color-text-light, #8793A3); font-size: 18rpx; line-height: 1.15; text-overflow: ellipsis; white-space: nowrap; }
.jy-timeline-pad { height: 292rpx; margin-top: 14rpx; position: relative; overflow: hidden; border: 1rpx solid var(--app-color-border, #D7E1EA); border-radius: 12rpx; background: var(--app-surface-strong, #FFFFFF); touch-action: none; user-select: none; transition: border-color 120ms ease, box-shadow 120ms ease; }
.jy-timeline-pad.active { border-color: var(--app-color-primary, #2F78F6); box-shadow: 0 0 0 3rpx rgba(47,120,246,0.12); }
.jy-timeline-pad.disabled { opacity: 0.58; }
.jy-timeline-pad.offline { opacity: 0.72; }
.jy-pad-head { height: 48rpx; padding: 0 12rpx; display: flex; align-items: center; border-bottom: 1rpx solid var(--app-color-border, #E7EDF2); }
.jy-pad-copy { min-width: 0; flex: 1; display: flex; align-items: baseline; }
.jy-pad-title { color: var(--app-color-text, #1E2B3C); font-size: 21rpx; font-weight: 700; }
.jy-pad-state { margin-left: 9rpx; overflow: hidden; color: var(--app-color-text-light, #8793A3); font-size: 14rpx; text-overflow: ellipsis; white-space: nowrap; }
.jy-speed-value,
.jy-zoom-value { min-width: 62rpx; margin-left: 10rpx; padding: 4rpx 7rpx; border-radius: 7rpx; background: var(--app-color-primary-bg, #EEF6FF); color: var(--app-color-primary, #2F78F6); font-size: 15rpx; font-weight: 700; text-align: center; }
.jy-speed-value { min-width: 88rpx; background: var(--app-surface-soft, #F3F7FA); color: var(--app-color-text-mid, #526A82); }
.jy-ruler { height: 59rpx; position: relative; overflow: hidden; border-bottom: 1rpx solid var(--app-color-border, #E7EDF2); background: var(--app-surface-soft, #F8FBFE); }
.jy-ruler-marks { width: calc(100% + 72rpx); height: 32rpx; position: absolute; top: 15rpx; left: -36rpx; background: repeating-linear-gradient(90deg, transparent 0 22rpx, #AAB7C5 22rpx 24rpx, transparent 24rpx 44rpx); transform-origin: 50% 50%; will-change: transform; }
.jy-ruler-marks::after { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(90deg, transparent 0 88rpx, #6F8094 88rpx 92rpx, transparent 92rpx 176rpx); }
.jy-playhead { width: 3rpx; position: absolute; top: 47rpx; bottom: 138rpx; left: 50%; z-index: 2; background: var(--app-color-primary, #2F78F6); }
.jy-playhead-cap { width: 18rpx; height: 18rpx; position: absolute; top: 10rpx; left: -8rpx; border-radius: 5rpx 5rpx 9rpx 9rpx; background: var(--app-color-primary, #2F78F6); }
.jy-gesture-cue { height: 45rpx; display: flex; align-items: center; justify-content: center; gap: 38rpx; border-bottom: 1rpx solid var(--app-color-border, #E7EDF2); color: var(--app-color-text-light, #7F8D9D); font-size: 16rpx; }
.jy-quick-actions { height: 138rpx; padding: 12rpx; position: relative; z-index: 3; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12rpx; background: var(--app-surface-soft, #F7FAFC); box-sizing: border-box; }
.jy-action-group { min-width: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8rpx; }
.jy-action-key { min-width: 0; height: 112rpx; display: flex; align-items: center; justify-content: center; flex-direction: column; border: 1rpx solid var(--app-color-border, #DCE5ED); border-radius: 10rpx; background: var(--app-surface-strong, #FFFFFF); box-shadow: 0 3rpx 8rpx rgba(43,72,106,.06); }
.jy-action-key-hover { transform: scale(.97); border-color: rgba(47,120,246,.45); background: var(--app-color-primary-bg, #EEF6FF); }
.jy-action-key.offline { opacity: .62; }
.jy-action-symbol { color: var(--app-color-text-mid, #48657F); font-size: 30rpx; font-weight: 750; line-height: 1; }
.jy-action-label { max-width: 92%; margin-top: 9rpx; overflow: hidden; color: var(--app-color-text, #30465B); font-size: 17rpx; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
</style>
