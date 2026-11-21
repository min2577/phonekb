<template>
  <view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle" @touchmove.stop.prevent="noop">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
    <view class="tp-header">
      <view class="tp-back" @tap="onBack">← 返回</view>
      <view class="tp-sens-row">
        <text class="tp-sens-label">灵敏度</text>
        <slider class="tp-sens-slider"
                :min="0.1" :max="5.0" :step="0.05"
                :value="tpSensitivity"
                :show-value="false"
                activeColor="#3B82F6"
                backgroundColor="#E5E7EB"
                block-size="22"
                @change="onSensSlider" />
        <text class="tp-sens-value">{{tpSensitivity.toFixed(2)}}x</text>
        <view class="tp-sens-quick" @tap="onSensQuick">复位</view>
      </view>
    </view>
    <view class="trackpad"
          @touchstart.stop.prevent="onTPStart"
          @touchmove.stop.prevent="onTPMove"
          @touchend.stop.prevent="onTPEnd"
          @touchcancel.stop.prevent="onTPCancel">
      <text class="trackpad-hint">触控板</text>
    </view>
    <view class="trackpad-row">
      <view class="tp-btn" @tap="onTPLeft">左键</view>
      <view class="tp-btn" @tap="onTPDouble">双击</view>
      <view class="tp-btn" @tap="onTPWheelUp">滚轮↑</view>
      <view class="tp-btn" @tap="onTPWheelDown">滚轮↓</view>
      <view class="tp-btn tp-btn-primary" @tap="onTPDrag">拖动</view>
    </view>
  </view>
</template>

<script>
import { markRaw } from 'vue'
import Net from '@/utils/net.js'
import { createTouchpadController } from '@/utils/touchpadController.js'
import { loadSettings } from '@/utils/appSettings.js'

export default {
  data() {
    return {
      statusBarHeight: 24,
      tpSensitivity: 1.5,
      touchpadController: null,
      dragMode: false,
    }
  },
  onShow() {
    try {
      const sv = parseFloat(uni.getStorageSync("phonekb.tp_sens"))
      if (sv && sv > 0 && sv <= 10) this.tpSensitivity = Math.round(sv * 100) / 100
    } catch (e) {}
    if (!this.touchpadController) this._createTouchpadController()
    else this.touchpadController.updateOptions(this._touchpadOptions())
    try { uni.setStorageSync("phonekb.touchpad_open_count", (parseInt(uni.getStorageSync("phonekb.touchpad_open_count") || 0) + 1)) } catch (e) {}
  },
  onUnload() {
    if (this.touchpadController) this.touchpadController.cancel()
  },
  onHide() {
    if (this.touchpadController) this.touchpadController.cancel()
    this.dragMode = false
  },
  onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
  methods: {
    onBack() {
      if (this.touchpadController) this.touchpadController.cancel()
      uni.navigateBack({ delta: 1 })
    },
    noop() {},
    _touchpadOptions() {
      const settings = loadSettings()
      return {
        sensitivity: this.tpSensitivity,
        scrollSensitivity: settings.touchpadScrollSensitivity,
        tapToClick: settings.touchpadTapToClick,
        tapDrag: settings.touchpadTapDrag,
        naturalScroll: settings.touchpadNaturalScroll,
        inertia: settings.touchpadInertia,
      }
    },
    _createTouchpadController() {
      this.touchpadController = markRaw(createTouchpadController({
        options: this._touchpadOptions(),
        emit: (action) => this._dispatchTouchpadAction(action),
      }))
    },
    _dispatchTouchpadAction(action) {
      if (!action) return
      if (action.action === 'mouse' && action.op === 'move') Net.mouseMove(action.dx, action.dy)
      else Net.send(action)
      if (action.action === 'mouse' && action.op === 'down' && action.button === 'left') this.dragMode = true
      if (action.action === 'mouse' && action.op === 'up' && action.button === 'left') this.dragMode = false
    },
    onSensSlider(e) {
      const v = parseFloat(e.detail.value)
      if (!isNaN(v)) {
        this.tpSensitivity = Math.round(v * 100) / 100
        if (this.touchpadController) this.touchpadController.updateOptions(this._touchpadOptions())
        try { uni.setStorageSync("phonekb.tp_sens", this.tpSensitivity) } catch (e) {}
        try { uni.vibrateShort({ type: "light" }) } catch (e) {}
      }
    },
    onSensQuick() {
      this.tpSensitivity = 1.5
      if (this.touchpadController) this.touchpadController.updateOptions(this._touchpadOptions())
      try { uni.setStorageSync("phonekb.tp_sens", 1.5) } catch (e) {}
      try { uni.showToast({ title: "已复位到 1.5x", icon: "none", duration: 1000 }) } catch (e) {}
    },
    onTPStart(e) {
      if (this.touchpadController) this.touchpadController.start(e.touches)
    },
    onTPMove(e) {
      if (this.touchpadController) this.touchpadController.move(e.touches)
    },
    onTPEnd(e) {
      if (this.touchpadController) this.touchpadController.end(e.touches)
      Net.flushMouseMove()
    },
    onTPCancel() {
      if (this.touchpadController) this.touchpadController.cancel()
      this.dragMode = false
    },
    onTPLeft() {
      Net.send({ action: "mouse", op: "click", button: "left" })
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
    },
    onTPRight() {
      Net.send({ action: "mouse", op: "click", button: "right" })
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
    },
    onTPDouble() {
      Net.send({ action: "mouse", op: "click", button: "left", count: 2 })
      try { uni.vibrateShort({ type: "medium" }) } catch (e) {}
    },
    onTPWheelUp() {
      Net.send({ action: "mouse", op: "wheel", delta: 120 })
    },
    onTPWheelDown() {
      Net.send({ action: "mouse", op: "wheel", delta: -120 })
    },
    onTPDrag() {
      if (this.touchpadController) this.touchpadController.armExternalDrag()
      try {
        uni.showToast({ title: "拖动中：滑动后抬手结束", icon: "none", duration: 1200 })
      } catch (e) {}
    },
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
}
.tp-header {
  padding: 18rpx 24rpx 22rpx;
  background: rgba(255,255,255,0.94);
  border-bottom: 1rpx solid #DCE6F1;
}
.tp-back {
  min-height: 58rpx;
  display: flex;
  align-items: center;
  color: #506177;
  font-size: 24rpx;
  font-weight: 650;
}
.tp-sens-row {
  margin-top: 8rpx;
  padding: 16rpx 18rpx;
  display: flex;
  align-items: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 18rpx;
  background: #F7FAFE;
}
.tp-sens-label {
  color: #53657B;
  font-size: 22rpx;
  font-weight: 650;
}
.tp-sens-slider {
  min-width: 0;
  flex: 1;
  margin: 0 12rpx;
}
.tp-sens-value {
  min-width: 72rpx;
  color: #2F78F6;
  font-size: 21rpx;
  font-weight: 700;
  text-align: center;
}
.tp-sens-quick {
  padding: 8rpx 12rpx;
  border-radius: 11rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 19rpx;
  font-weight: 650;
}
.trackpad {
  height: 760rpx;
  margin: 24rpx;
  touch-action: none;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #D5E1EE;
  border-radius: 32rpx;
  background: #FFFFFF;
  box-shadow: 0 14rpx 34rpx rgba(47,78,113,0.09);
}
.trackpad-hint {
  max-width: 70%;
  color: #8996A7;
  font-size: 22rpx;
  line-height: 1.5;
  text-align: center;
}
.trackpad-row {
  margin: 0 24rpx;
  display: flex;
  gap: 10rpx;
}
.tp-btn {
  min-width: 0;
  flex: 1;
  height: 70rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 15rpx;
  background: #FFFFFF;
  color: #506177;
  font-size: 20rpx;
  font-weight: 650;
}
.tp-btn-primary {
  border-color: #2F78F6;
  background: #2F78F6;
  color: #FFFFFF;
}

.statusbar-spacer { width: 100%; }
</style>
