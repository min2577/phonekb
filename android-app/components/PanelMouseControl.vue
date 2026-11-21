<template>
  <view class="section section-trackpad-launcher">
    <view class="tp-card">
      <view class="tp-body">
        <view class="tp-pad"
              @touchstart.stop.prevent="onTPStart"
              @touchmove.stop.prevent="onTPMove"
              @touchend.stop.prevent="onTPEnd"
              @touchcancel.stop.prevent="onTPCancel">
          <text class="tp-hint">触控板</text>
        </view>
        <view class="tp-row">
          <view class="tp-btn" @tap="onTPLeft">左键</view>
          <view class="tp-btn" @tap="onTPRight">右键</view>
          <view :class="['tp-btn', 'tp-btn-wheel', wheelMotion.longPressed ? 'is-scrolling' : '']"
                @touchstart.stop.prevent="onWheelStart"
                @touchmove.stop.prevent="onWheelMove"
                @touchend.stop.prevent="onWheelEnd"
                @touchcancel.stop.prevent="onWheelCancel">滚轮</view>
          <view class="tp-btn tp-btn-icon" @tap="onShowSensModal">⚙</view>
        </view>
      </view>
    </view>
  </view>

  <view v-if="showSensModal" class="modal-mask" @tap="onCloseSensModal">
    <view class="modal sens-modal" @tap="noop">
      <view class="modal-head"><text class="modal-title">⚙ 鼠标灵敏度</text></view>
      <view class="modal-body">
        <view class="sens-modal-value">{{tpSensitivity.toFixed(2)}}x</view>
        <slider class="sens-modal-slider"
                :min="0.1" :max="5.0" :step="0.05"
                :value="tpSensitivity"
                activeColor="#3B82F6"
                backgroundColor="#E5E7EB"
                block-size="26"
                @change="onSensSlider" />
        <view class="sens-modal-presets">
          <view v-for="(p, i) in sensPresets" :key="i"
                :class="['sens-preset', Math.abs(tpSensitivity - p) < 0.025 ? 'on' : '']"
                :data-val="p"
                @tap="onSensPreset">{{p.toFixed(2)}}x</view>
        </view>
        <view class="sens-modal-input-row">
          <input size="1" class="sens-modal-input" type="digit" placeholder="0.10 ~ 5.00"
                 placeholder-class="sens-modal-input-ph"
                 :value="sensInputValue"
                 @input="onSensInputChange"
                 confirm-type="done" />
          <view class="sens-modal-input-btn" @tap="onSensInputConfirm">设置</view>
        </view>
      </view>
      <view class="modal-foot">
        <view class="btn-cancel" @tap="onSensReset">复位 1.00x</view>
        <view class="btn-save" @tap="onCloseSensModal">完成</view>
      </view>
    </view>
  </view>

  <view v-if="showTrackpad" class="trackpad-modal">
    <view class="trackpad-modal-head">
      <text class="trackpad-modal-title">🖱 鼠标控制</text>
      <view class="trackpad-modal-close" @tap="onCloseTrackpad" hover-class="trackpad-modal-close-hover">×</view>
    </view>
    <view class="trackpad-modal-pad"
          @touchstart.stop.prevent="onTPStart"
          @touchmove.stop.prevent="onTPMove"
          @touchend.stop.prevent="onTPEnd"
          @touchcancel.stop.prevent="onTPCancel">
      <text class="tp-hint">触控板</text>
    </view>
    <view class="trackpad-modal-row">
      <view class="tp-btn" @tap="onTPRight">右键</view>
      <view class="tp-btn" @tap="onTPDouble">双击</view>
      <view class="tp-btn" @tap="onTPWheelUp">滚轮↑</view>
      <view class="tp-btn" @tap="onTPWheelDown">滚轮↓</view>
      <view class="tp-btn tp-btn-primary" @tap="onTPDrag">拖动</view>
    </view>
  </view>
</template>

<script>
import { markRaw } from "vue"
import Net from "@/utils/net.js"
import {
  WHEEL_LONG_PRESS_MS,
  WHEEL_MOVE_SLOP_PX,
  consumeWheelMovement,
} from "@/utils/mouseGesture.js"
import { createTouchpadController } from "@/utils/touchpadController.js"
import { loadSettings } from "@/utils/appSettings.js"

export default {
  name: "PanelMouseControl",
  emits: ["tp-expand-change"],
  props: {
    forceExpand: { type: Boolean, default: false },
    preview: { type: Boolean, default: false },
  },
  data() {
    return {
      dragging: false,
      tpExpanded: true,
      tpSensitivity: 1.5,
      showSensModal: false,
      sensInputValue: "",
      sensPresets: [0.5, 1.0, 1.5, 2.0, 3.0],
      showTrackpad: false,
      touchpadController: null,
      wheelMotion: {
        startY: null, lastY: null, startAt: 0,
        accumulatedY: 0, timer: null,
        longPressed: false, moved: false,
      },
    }
  },
  mounted() {
    try {
      const sv = parseFloat(uni.getStorageSync("phonekb.tp_sens"))
      if (sv && sv > 0 && sv <= 10) this.tpSensitivity = Math.round(sv * 100) / 100
    } catch (e) {}
    this._createTouchpadController()
    // 监听全局「全屏触摸板」事件
    if (!this.preview) {
      this._onTrackpadReq = () => this.onShowTrackpad()
      try { uni.$on('phonekb:showTrackpad', this._onTrackpadReq) } catch (e) {}
    }
  },
  beforeUnmount() {
    if (this.touchpadController) this.touchpadController.cancel()
    this._resetWheelGesture()
    if (this._onTrackpadReq) {
      try { uni.$off('phonekb:showTrackpad', this._onTrackpadReq) } catch (e) {}
    }
  },
  deactivated() {
    if (this.touchpadController) this.touchpadController.cancel()
    this._resetWheelGesture()
    this.dragging = false
  },
  methods: {
    noop() {},
    onTpExpandChange(expanded) { this.$emit('tp-expand-change', expanded) },
    onShowSensModal() {
      if (this.preview) return
      this.sensInputValue = this.tpSensitivity.toFixed(2)
      this.showSensModal = true
    },
    onCloseSensModal() { this.showSensModal = false },
    onSensPreset(e) {
      const v = Number(e.currentTarget.dataset.val)
      if (!isNaN(v) && v > 0) {
        this.tpSensitivity = Math.max(0.1, Math.min(5.0, v))
        this._syncTouchpadOptions()
        try { uni.setStorageSync("phonekb.tp_sens", this.tpSensitivity) } catch (e) {}
        try { uni.vibrateShort({ type: "light" }) } catch (e) {}
      }
    },
    onSensInputChange(e) {
      this.sensInputValue = String(e.detail.value || "")
    },
    onSensInputConfirm() {
      const v = parseFloat(this.sensInputValue)
      if (!isNaN(v) && v >= 0.1 && v <= 5.0) {
        this.tpSensitivity = v
        this._syncTouchpadOptions()
        try { uni.setStorageSync("phonekb.tp_sens", this.tpSensitivity) } catch (e) {}
        try { uni.vibrateShort({ type: "light" }) } catch (e) {}
        this.sensInputValue = v.toFixed(2)
      } else {
        uni.showToast({ title: "请输入 0.10 ~ 5.00", icon: "none" })
      }
    },
    onSensSlider(e) {
      const v = parseFloat(e.detail.value)
      if (!isNaN(v)) {
        this.tpSensitivity = Math.round(v * 100) / 100
        this._syncTouchpadOptions()
        try { uni.setStorageSync("phonekb.tp_sens", this.tpSensitivity) } catch (e) {}
      }
    },
    onSensReset() {
      this.tpSensitivity = 1.5
      this._syncTouchpadOptions()
      try { uni.setStorageSync("phonekb.tp_sens", 1.5) } catch (e) {}
      try { uni.vibrateShort({ type: "light" }) } catch (e) {}
    },
    onShowTrackpad() { if (!this.preview) this.showTrackpad = true },
    onCloseTrackpad() {
      if (this.touchpadController) this.touchpadController.cancel()
      this.dragging = false
      this.showTrackpad = false
    },
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
    _syncTouchpadOptions() {
      if (this.touchpadController) this.touchpadController.updateOptions(this._touchpadOptions())
    },
    _dispatchTouchpadAction(action) {
      if (this.preview || !action) return
      if (action.action === 'mouse' && action.op === 'move') Net.mouseMove(action.dx, action.dy)
      else Net.send(action)
      if (action.action === 'mouse' && action.op === 'down' && action.button === 'left') this.dragging = true
      if (action.action === 'mouse' && action.op === 'up' && action.button === 'left') this.dragging = false
    },
    onTPStart(e) {
      if (!this.preview && this.touchpadController) this.touchpadController.start(e.touches)
    },
    onTPMove(e) {
      if (!this.preview && this.touchpadController) this.touchpadController.move(e.touches)
    },
    onTPEnd(e) {
      if (!this.preview && this.touchpadController) this.touchpadController.end(e.touches)
      Net.flushMouseMove()
    },
    onTPCancel() {
      if (this.touchpadController) this.touchpadController.cancel()
      this.dragging = false
    },
    onTPRight() { if (!this.preview) Net.send({ action: "mouse", op: "click", button: "right" }) },
    onTPLeft() { if (!this.preview) Net.send({ action: "mouse", op: "click", button: "left" }) },
    onTPWheel() { if (!this.preview) Net.send({ action: "mouse", op: "wheel", delta: 120 }) },
    _wheelTouch(e) {
      return (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
    },
    _clearWheelTimer() {
      const wheel = this.wheelMotion
      if (wheel.timer == null) return
      clearTimeout(wheel.timer)
      wheel.timer = null
    },
    _resetWheelGesture() {
      this._clearWheelTimer()
      const wheel = this.wheelMotion
      wheel.startY = null; wheel.lastY = null; wheel.startAt = 0
      wheel.accumulatedY = 0; wheel.longPressed = false; wheel.moved = false
    },
    onWheelStart(e) {
      if (this.preview) return
      const t = this._wheelTouch(e)
      if (!t) return
      this._resetWheelGesture()
      const wheel = this.wheelMotion
      wheel.startY = t.clientY
      wheel.lastY = t.clientY
      wheel.startAt = Date.now()
      wheel.timer = setTimeout(() => {
        wheel.timer = null
        wheel.longPressed = true
        try { uni.vibrateShort({ type: "light" }) } catch (err) {}
      }, WHEEL_LONG_PRESS_MS)
    },
    onWheelMove(e) {
      if (this.preview) return
      const t = this._wheelTouch(e)
      const wheel = this.wheelMotion
      if (!t || wheel.lastY == null) return
      const currentY = t.clientY
      if (!wheel.longPressed) {
        if (Math.abs(currentY - wheel.startY) > WHEEL_MOVE_SLOP_PX) {
          wheel.moved = true
          this._clearWheelTimer()
        }
        wheel.lastY = currentY
        return
      }
      wheel.moved = true
      wheel.accumulatedY += currentY - wheel.lastY
      wheel.lastY = currentY
      const result = consumeWheelMovement(wheel.accumulatedY)
      wheel.accumulatedY = result.remainingY
      const notch = result.delta < 0 ? -120 : 120
      for (let remaining = Math.abs(result.delta); remaining > 0; remaining -= 120) {
        Net.send({ action: "mouse", op: "wheel", delta: notch })
      }
    },
    onWheelEnd() {
      if (this.preview) return
      const wheel = this.wheelMotion
      const isTap = !wheel.longPressed && !wheel.moved &&
        wheel.startAt > 0 && Date.now() - wheel.startAt < WHEEL_LONG_PRESS_MS
      this._resetWheelGesture()
      if (isTap) this.onTPWheel()
    },
    onWheelCancel() {
      if (!this.preview) this._resetWheelGesture()
    },
    onTPDrag() {
      if (this.preview) return
      if (this.touchpadController) this.touchpadController.armExternalDrag()
      uni.showToast({ title: "拖动中：滑动后抬手结束", icon: "none", duration: 1500 })
    },
    onTPDouble() { if (!this.preview) Net.send({ action: "mouse", op: "click", button: "left", count: 2 }) },
    onTPWheelUp() { if (!this.preview) Net.send({ action: "mouse", op: "wheel", delta: 120 }) },
    onTPWheelDown() { if (!this.preview) Net.send({ action: "mouse", op: "wheel", delta: -120 }) },
  },
}
</script>

<style>
/* ==========================================================================
 * PanelMouseControl 全局样式 (非 scoped)
 *
 * 历史原因: 原本这些样式写在 pages/panel/panel.vue 的 .panel-page 前缀下,
 * 但因为 panel.vue 用 <style scoped>, 子组件内部的节点不会带 panel 的 data-v
 * hash, 导致 .panel-page .trackpad-modal 等选择器选不中这里的节点,
 * 实际渲染时全屏触摸板 / 灵敏度弹窗没有 position: fixed / z-index, 透到
 * 下面 widget-slot 之上看起来"乱七八糟"。
 *
 * 修复: 在本组件内提供同名类的全局基础样式, z-index 提到 1500 盖过所有
 * panel 内部元素 (widget-slot 240 / trackpad-modal 260 / MoreMenu 300)。
 * panel.vue 的同名 .panel-page 前缀样式保留不动, 只在 panel 自己模板内的
 * trackpad-modal 节点生效 (那里有 preview 等其他用途)。
 * ========================================================================== */

/* === 全屏触摸板 modal === */
.trackpad-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 1500;
  display: flex;
  flex-direction: column;
  /* Keep the title below the Android status/navigation area even when the
   * native safe-area inset is reported as zero by the custom navigation bar. */
  padding: calc(64rpx + env(safe-area-inset-top)) 28rpx calc(28rpx + env(safe-area-inset-bottom));
  background: #F5F8FC;
}
.trackpad-modal-head { display: flex; align-items: center; min-height: 72rpx; gap: 12rpx; }
.trackpad-modal-title { flex: 1; color: #1E2B3C; font-size: 30rpx; font-weight: 650; }
.trackpad-modal-close {
  width: 58rpx; height: 58rpx;
  display: flex; align-items: center; justify-content: center;
  color: #526175; background: #FFFFFF;
  border: 1rpx solid #E0E6EE; border-radius: 16rpx; font-size: 34rpx;
}
.trackpad-modal-pad {
  flex: 1; margin: 20rpx 0;
  display: flex; align-items: center; justify-content: center;
  touch-action: none; user-select: none;
  background: linear-gradient(145deg, #FFFFFF 0%, #EEF3F8 100%);
  border: 1rpx solid #DCE4ED; border-radius: 26rpx;
}
.trackpad-modal-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10rpx; }
.trackpad-modal-row .tp-btn { height: 72rpx; }

/* === Panel 内小触摸板 launcher (非全屏) === */
.section-trackpad-launcher { margin: 0; padding: 0; background: transparent; border: 0; box-shadow: none; }
.tp-card { background: transparent; }
.tp-body { display: flex; flex-direction: column; gap: 12rpx; padding: 0; background: transparent; border: 0; box-shadow: none; }
.tp-pad {
  width: 100%; height: 188rpx;
  touch-action: none; user-select: none;
  background: linear-gradient(145deg, #FFFFFF 0%, #F1F5FA 100%);
  border: 1rpx solid #DFE6EF; border-radius: 18rpx;
  display: flex; align-items: center; justify-content: center;
}
.tp-pad::before { display: none; }
.tp-hint { color: #8D99A9; font-size: 21rpx; font-weight: 400; }
.tp-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12rpx; }
.tp-btn {
  min-width: 0; height: 58rpx; padding: 0 8rpx;
  display: flex; align-items: center; justify-content: center;
  color: #465468; background: #FFFFFF;
  border: 1rpx solid #E1E7EF; border-radius: 12rpx;
  font-size: 21rpx; font-weight: 550;
}
.tp-btn-icon { color: #7C899A; background: #F9FAFC; font-size: 25rpx; }
.tp-btn-wheel { touch-action: none; user-select: none; }
.tp-btn-wheel.is-scrolling { color: #2F78F6; background: #E8F2FF; border-color: #83B4FF; }
.tp-btn-primary { background: linear-gradient(145deg, #2F78F6 0%, #5C9BFF 100%); color: #FFFFFF; border-color: transparent; }
.tp-btn:active { background: #EEF6FF; transform: scale(0.97); }

/* === 灵敏度弹窗 (基础) === */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(31,48,70,0.28);
  backdrop-filter: blur(12rpx);
  -webkit-backdrop-filter: blur(12rpx);
  z-index: 1500;
  display: flex; align-items: center; justify-content: center;
  padding: 48rpx;
}
.modal {
  width: 100%; max-width: 650rpx; max-height: 80vh;
  background: rgba(255,255,255,0.96);
  border: 1rpx solid rgba(122,145,169,0.18);
  border-radius: 26rpx;
  box-shadow: 0 24rpx 64rpx rgba(40,65,94,0.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-head { padding: 26rpx 28rpx 20rpx; }
.modal-title { color: #1E2B3C; font-size: 29rpx; font-weight: 600; }
.modal-body { padding: 8rpx 28rpx 20rpx; max-height: 70vh; }
.modal-foot { display: flex; gap: 12rpx; padding: 16rpx 28rpx 22rpx; }
.btn-cancel, .btn-save {
  min-width: 144rpx; padding: 17rpx 24rpx;
  border-radius: 12rpx; text-align: center;
  font-size: 24rpx; font-weight: 550;
}
.btn-cancel { color: #566579; background: #F2F5F8; flex: 1; }
.btn-save { color: #FFFFFF; background: linear-gradient(145deg, #2F78F6 0%, #5C9BFF 100%); flex: 1; }

/* sens-modal specific */
.sens-modal { width: 560rpx; }
.sens-modal-value { text-align: center; font-size: 56rpx; font-weight: 700; color: #2F78F6; padding: 16rpx 0; font-family: Consolas, monospace; }
.sens-modal-slider { width: 100%; }
.sens-modal-presets { display: flex; gap: 12rpx; padding: 18rpx 0 8rpx; }
.sens-preset { flex: 1; padding: 14rpx 0; text-align: center; background: #F6F9FC; border: 1rpx solid #E1E7EF; border-radius: 12rpx; color: #566579; font-size: 22rpx; }
.sens-preset.on { background: linear-gradient(145deg, #2F78F6 0%, #5C9BFF 100%); color: #FFFFFF; border-color: transparent; }
.sens-modal-input-row { display: flex; gap: 12rpx; padding: 22rpx 24rpx 10rpx; }
.sens-modal-input { flex: 1; height: 66rpx; padding: 0 18rpx; background: #F7F9FC; border: 1rpx solid #E1E7EF; border-radius: 12rpx; font-size: 23rpx; }
.sens-modal-input-ph { color: #A8B1BE; }
.sens-modal-input-btn { min-width: 112rpx; height: 66rpx; display: flex; align-items: center; justify-content: center; color: #FFFFFF; background: linear-gradient(145deg, #2F78F6 0%, #5C9BFF 100%); border-radius: 12rpx; font-size: 23rpx; }

.app-appearance-active .trackpad-modal {
  background: var(--app-color-bg-alt);
}
.app-appearance-active .trackpad-modal-title,
.app-appearance-active .sens-modal .modal-title {
  color: var(--app-color-text);
}
.app-appearance-active .tp-hint,
.app-appearance-active .sens-preset,
.app-appearance-active .sens-modal-input {
  color: var(--app-color-text-mid);
}
.app-appearance-active .trackpad-modal-close,
.app-appearance-active .trackpad-modal-pad,
.app-appearance-active .tp-pad,
.app-appearance-active .tp-btn,
.app-appearance-active .sens-preset,
.app-appearance-active .sens-modal-input,
.app-appearance-active .sens-modal .btn-cancel {
  background: var(--app-surface-strong);
  background-image: none;
  border-color: var(--app-color-border);
}
.app-appearance-active .tp-btn {
  color: var(--app-color-text-mid);
}
.app-appearance-active .tp-btn-icon {
  background: var(--app-color-bg-alt);
}
.app-appearance-active .tp-btn:active {
  background: var(--app-color-primary-bg);
}
.app-appearance-active .tp-btn-primary,
.app-appearance-active .sens-preset.on {
  background: var(--app-color-primary);
  color: #FFFFFF;
  border-color: transparent;
}
.app-appearance-active .sens-modal {
  background: var(--app-surface-strong);
  border-color: var(--app-color-border);
}
</style>
