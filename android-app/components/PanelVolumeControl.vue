<template>
<view class="section">
  <view class="vol-display">
    <text class="vol-display-icon">{{ muted ? '🔇' : '🔊' }}</text>
    <view class="vol-display-info">
      <text class="vol-display-label">{{ muted ? '已静音' : '音量' }}</text>
      <text class="vol-display-value">{{ muted ? '—' : Math.round(volume * 100) + '%' }}</text>
    </view>
  </view>
  <view class="vol-row">
    <view class="vol-btn vol-btn-side" hover-class="vol-btn-hover" @tap="onVolDown">
      <text class="vol-btn-text">−</text>
    </view>
    <view class="vol-btn vol-btn-toggle" :class="{ 'is-muted': muted }"
          hover-class="vol-btn-toggle-hover" @tap="onToggleMute">
      <text class="vol-btn-text">{{ muted ? '取消静音' : '静音' }}</text>
    </view>
    <view class="vol-btn vol-btn-side" hover-class="vol-btn-hover" @tap="onVolUp">
      <text class="vol-btn-text">＋</text>
    </view>
  </view>
</view>
</template>

<script>
import Net from '@/utils/net.js'

export default {
  name: 'PanelVolumeControl',
  props: {
    preview: { type: Boolean, default: false },
  },
  data() {
    return {
      volume: 0.5,
      muted: false,
    }
  },
  methods: {
    sendAction(action) {
      if (this.preview) return
      if (!Net.isConnected()) {
        uni.showToast({ title: '未连接,点顶部状态条重连', icon: 'none', duration: 1500 })
        return
      }
      const sent = Net.send({ action: action })
      if (sent) {
        try { uni.vibrateShort({ type: 'light' }) } catch (e) {}
      } else {
        uni.showToast({ title: '发送失败', icon: 'none', duration: 1200 })
      }
    },
    onVolDown() {
      if (this.preview) return
      this.volume = Math.max(0, this.volume - 0.05)
      this.sendAction('volume_down')
    },
    onVolUp() {
      if (this.preview) return
      this.volume = Math.min(1, this.volume + 0.05)
      this.sendAction('volume_up')
    },
    onToggleMute() {
      if (this.preview) return
      this.muted = !this.muted
      this.sendAction(this.muted ? 'volume_mute' : 'volume_unmute')
    },
  },
}
</script>

<style>
.section { flex: 0 0 auto; }
.vol-display {
  display: flex; align-items: center; gap: 16rpx;
  padding: 16rpx 24rpx;
  background: var(--color-bg-alt);
  border-radius: 14rpx;
  margin-bottom: 16rpx;
}
.vol-display-icon { font-size: 48rpx; line-height: 1; }
.vol-display-info { flex: 1; display: flex; flex-direction: column; gap: 2rpx; }
.vol-display-label { font-size: 24rpx; color: var(--color-text-mid); }
.vol-display-value { font-size: 32rpx; font-weight: 700; color: var(--color-text); font-family: Consolas, monospace; }

.vol-row {
  display: grid; grid-template-columns: 1fr 1.4fr 1fr; gap: 12rpx;
}
.vol-btn {
  padding: 24rpx 0;
  border-radius: 14rpx;
  font-weight: 600;
  text-align: center;
  transition: background-color var(--duration-base) var(--ease-fluent), transform var(--duration-fast) var(--ease-fluent);
}
.vol-btn-hover { transform: scale(0.97); }
.vol-btn-toggle-hover { transform: scale(0.97); }

.vol-btn-side {
  background: var(--color-bg);
  color: var(--color-text);
  border: 2rpx solid var(--color-divider);
  font-size: 40rpx;
}
.vol-btn-toggle {
  background: var(--color-primary);
  color: white;
  border: 2rpx solid var(--color-primary);
  font-size: 28rpx;
}
.vol-btn-toggle.is-muted {
  background: var(--color-danger);
  border-color: var(--color-danger);
}
</style>
