<template>
  <view class="section section-text">
    <textarea
      class="text-input"
      placeholder="在这里输入内容，发送到电脑..."
      placeholder-class="text-input-ph"
      :value="typeText"
      :disabled="preview"
      @input="onTypeInput"
      @confirm="onTypeSend"
      maxlength="-1"
      hold-keyboard="true"
    />
    <view class="text-actions">
      <view :class="['btn-secondary', 'text-clear-btn', !typeText ? 'is-disabled' : '']" @tap="onTypeClear">清空</view>
      <view :class="['btn-primary', 'text-send-btn', !typeText ? 'is-disabled' : '']" @tap="onTypeSend">发送</view>
    </view>
  </view>
</template>

<script>
import Net from "@/utils/net.js"

export default {
  name: "PanelTextInput",
  props: {
    preview: { type: Boolean, default: false },
  },
  emits: ["send", "clear"],
  data() {
    return { typeText: "" }
  },
  methods: {
    onTypeInput(e) {
      if (this.preview) return
      this.typeText = String((e && e.detail && e.detail.value) || "")
    },
    onTypeSend() {
      if (this.preview) return
      const text = this.typeText
      if (!text) return
      if (!Net.isConnected()) {
        uni.showToast({ title: "未连接，点顶部状态条重连", icon: "none", duration: 1800 })
        return
      }
      const sent = Net.send({ action: "type", text: text })
      if (sent) {
        try { uni.vibrateShort({ type: "light" }) } catch (e) {}
        this.typeText = ""
        this.$emit("send", text)
      } else {
        uni.showToast({ title: "发送失败，请重连", icon: "none", duration: 1500 })
      }
    },
    onTypeClear() {
      if (this.preview) return
      this.typeText = ""
      this.$emit("clear")
    },
  },
}
</script>

<style>
/* 文字输入：清空按钮 - 与 快捷键 按钮风格一致（白底深字、淡边框、3D 立体感） */
.text-clear-btn,
.panel-page .text-clear-btn,
.custom-app-preview .text-clear-btn {
  background-color: #FFFFFF !important;
  background-image: linear-gradient(180deg, #FFFFFF 0%, #F6F9FD 100%) !important;
  color: #5B6776 !important;
  border: 1rpx solid #DDE4ED !important;
  font-weight: 600 !important;
  box-shadow:
    0 4rpx 10rpx rgba(47,78,113,0.10),
    0 1rpx 2rpx rgba(47,78,113,0.06),
    inset 0 1rpx 1rpx rgba(255,255,255,0.92),
    inset 0 -1rpx 1rpx rgba(47,78,113,0.06) !important;
}
.text-clear-btn.is-disabled,
.panel-page .text-clear-btn.is-disabled,
.custom-app-preview .text-clear-btn.is-disabled {
  opacity: 1 !important;
  background-color: #F8FAFD !important;
  background-image: linear-gradient(180deg, #F8FAFD 0%, #F4F7FB 100%) !important;
  color: #B7C0CC !important;
  border-color: #E6ECF3 !important;
  box-shadow: inset 0 1rpx 1rpx rgba(255,255,255,0.6) !important;
}

/* 文字输入：发送按钮 - 同 快捷键 风格，但用蓝色字和边框以区分主操作 */
.text-send-btn,
.panel-page .text-send-btn,
.custom-app-preview .text-send-btn {
  background-color: #FFFFFF !important;
  background-image: linear-gradient(180deg, #FFFFFF 0%, #F0F6FE 100%) !important;
  color: #2F78F6 !important;
  border: 1rpx solid #BCD5F8 !important;
  font-weight: 700 !important;
  box-shadow:
    0 4rpx 10rpx rgba(47,120,246,0.14),
    0 1rpx 2rpx rgba(47,120,246,0.08),
    inset 0 1rpx 1rpx rgba(255,255,255,0.92),
    inset 0 -1rpx 1rpx rgba(47,120,246,0.06) !important;
}
.text-send-btn.is-disabled,
.panel-page .text-send-btn.is-disabled,
.custom-app-preview .text-send-btn.is-disabled {
  opacity: 1 !important;
  background-color: #F8FAFD !important;
  background-image: linear-gradient(180deg, #F8FAFD 0%, #F4F7FB 100%) !important;
  color: #B7C0CC !important;
  border-color: #E6ECF3 !important;
  box-shadow: inset 0 1rpx 1rpx rgba(255,255,255,0.6) !important;
}

.panel-page.app-appearance-active .text-clear-btn,
.panel-page.app-appearance-active .text-send-btn {
  background-color: var(--app-surface-strong) !important;
  background-image: none !important;
  border-color: var(--app-color-border) !important;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.10) !important;
}
.panel-page.app-appearance-active .text-clear-btn {
  color: var(--app-color-text-mid) !important;
}
.panel-page.app-appearance-active .text-send-btn {
  color: var(--app-color-primary) !important;
}
.panel-page.app-appearance-active .text-clear-btn.is-disabled,
.panel-page.app-appearance-active .text-send-btn.is-disabled {
  background-color: var(--app-surface) !important;
  color: var(--app-color-disabled) !important;
  border-color: var(--app-color-divider) !important;
  box-shadow: none !important;
}
</style>
