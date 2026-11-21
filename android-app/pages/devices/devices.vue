<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="connection-card">
    <view class="card-heading">
      <view class="heading-icon">链</view>
      <text class="heading-title">当前连接</text>
    </view>

    <view class="connection-state">
      <view class="state-copy">
        <view :class="['state-dot', connected ? 'state-dot-on' : 'state-dot-off']"></view>
        <view class="state-texts">
          <text class="state-title">{{ connected ? '已连接' : '未连接' }}</text>
          <text class="state-sub">{{ connected ? '连接稳定' : '等待连接电脑' }}</text>
        </view>
      </view>
      <text :class="['status-badge', connected ? 'status-badge-on' : 'status-badge-off']">
        {{ connected ? '在线' : '离线' }}
      </text>
    </view>

    <view v-if="lastHello" class="connection-details">
      <view class="detail-row">
        <text class="detail-label">服务器</text>
        <text class="detail-value">{{ lastHello.server }}</text>
      </view>
      <view class="detail-row">
        <text class="detail-label">协议版本</text>
        <text class="detail-value">{{ lastHello.proto }}</text>
      </view>
    </view>
  </view>

  <view class="device-section">
    <view class="section-heading">
      <view class="section-heading-left">
        <view class="heading-icon">设</view>
        <text class="heading-title">在线设备</text>
        <text class="count-badge">{{ devices.length }}</text>
      </view>
      <view class="refresh-btn" hover-class="refresh-btn-hover" @tap="onRefresh">刷新</view>
    </view>

    <view v-if="devices.length === 0" class="empty-state">
      <view class="empty-icon">PC</view>
      <text class="empty-title">暂无在线设备</text>
      <text class="empty-sub">请确认手机与电脑处于同一网络</text>
    </view>

    <view v-for="(item, idx) in devices" :key="idx" class="device-row" hover-class="device-row-hover">
      <view class="device-icon">{{ idx === 0 ? 'PC' : 'NB' }}</view>
      <view class="device-copy">
        <text class="device-name">设备 #{{ item.index + 1 }}</text>
        <text class="device-meta">{{ item.ip }}<text v-if="item.last_pong"> · {{ fmtTime(item.last_pong) }}</text></text>
      </view>
      <text class="device-online">在线</text>
    </view>
  </view>

  <view class="info-strip">
    <text class="info-text">如果设备没有出现，请确认手机和电脑位于同一网络，或返回连接页重新连接。</text>
  </view>

  <view class="footer-safe"></view>
  <CustomTabBar />
</view>
</template>

<script>
import CustomTabBar from '@/components/CustomTabBar.vue'
let app = null
try { app = getApp({ allowDefault: true }) } catch (e) {}
import WS from '@/utils/net.js'

export default {
  components: { CustomTabBar },
  data() { return {
      statusBarHeight: 24,
    devices: [],
    lastHello: null,
    connected: false,
    pullTimer: null,
  } },

  onShow() {
    this.lastHello = WS.getHello() || (() => { try { return uni.getStorageSync("phonekb.hello") } catch (e) { return null } })(); this.connected = WS.isConnected()
    this._pull()
    const self = this
    if (!this._devicesListener) {
      this._devicesListener = function(devs) { self.devices = devs }
      WS.onDevices(this._devicesListener)
    }
    if (!this.pullTimer) {
      this.pullTimer = setInterval(function() { self._pull() }, 5000)
    }
  },

  onHide() {
    if (this.pullTimer) { clearInterval(this.pullTimer); this.pullTimer = null }
  },

  onUnload() {
    if (this.pullTimer) { clearInterval(this.pullTimer); this.pullTimer = null }
    if (this._devicesListener) {
      WS.offDevices(this._devicesListener)
      this._devicesListener = null
    }
  },

    onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {} },
    methods: {
_pull() {
    WS.send({ action: "list_devices" })
  },

  onRefresh() {
    this._pull()
    uni.showToast({ title: "已刷新", icon: "success", duration: 600 })
  },

  fmtTime(ts) {
    if (!ts) return "—"
    const d = new Date(ts)
    if (ts > 1e12) {
      // ms
      const dt = new Date(ts)
      const pad = (n) => (n < 10 ? "0" : "") + n
      return pad(dt.getMonth() + 1) + "-" + pad(dt.getDate()) + " " + pad(dt.getHours()) + ":" + pad(dt.getMinutes())
    }
    return d.toLocaleString()
  }
  }
}
</script>
<style scoped>
.page {
  min-height: 100vh;
  padding: 20rpx 24rpx calc(132rpx + env(safe-area-inset-bottom));
  background: #F4F8FD;
  color: #172033;
  box-sizing: border-box;
}
.connection-card,
.device-section {
  margin: 0 8rpx 16rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(47, 78, 113, 0.06);
  overflow: hidden;
}
.connection-card {
  padding: 20rpx 22rpx;
}
.card-heading,
.section-heading,
.section-heading-left,
.connection-state,
.state-copy,
.detail-row,
.device-row {
  display: flex;
  align-items: center;
}
.card-heading {
  margin-bottom: 18rpx;
}
.heading-icon {
  width: 46rpx;
  height: 46rpx;
  margin-right: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 700;
}
.heading-title {
  color: #172033;
  font-size: 27rpx;
  font-weight: 700;
}
.connection-state {
  justify-content: space-between;
  padding: 6rpx 0 16rpx;
}
.state-copy {
  flex: 1;
  min-width: 0;
}
.state-dot {
  width: 16rpx;
  height: 16rpx;
  margin: 0 18rpx 0 4rpx;
  border-radius: 50%;
}
.state-dot-on {
  background: #22B85A;
  box-shadow: 0 0 0 7rpx rgba(34, 184, 90, 0.12);
}
.state-dot-off {
  background: #AEB8C6;
  box-shadow: 0 0 0 7rpx rgba(174, 184, 198, 0.12);
}
.state-texts,
.device-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.state-title,
.device-name {
  color: #172033;
  font-size: 25rpx;
  font-weight: 650;
}
.state-sub,
.device-meta {
  margin-top: 5rpx;
  color: #7E8B9E;
  font-size: 19rpx;
}
.status-badge,
.device-online {
  padding: 5rpx 13rpx;
  border-radius: 999rpx;
  font-size: 18rpx;
  font-weight: 650;
}
.status-badge-on,
.device-online {
  background: #EAF8EF;
  color: #159447;
}
.status-badge-off {
  background: #EDF1F6;
  color: #7C8796;
}
.connection-details {
  padding-top: 10rpx;
  border-top: 1rpx solid #E8EEF5;
}
.detail-row {
  min-height: 60rpx;
  justify-content: space-between;
}
.detail-row + .detail-row {
  border-top: 1rpx solid #EDF2F7;
}
.detail-label {
  color: #6F7D91;
  font-size: 21rpx;
}
.detail-value {
  max-width: 64%;
  color: #172033;
  font-size: 22rpx;
  font-weight: 600;
  text-align: right;
}
.section-heading {
  min-height: 78rpx;
  padding: 0 20rpx;
  justify-content: space-between;
  border-bottom: 1rpx solid #E8EEF5;
}
.count-badge {
  margin-left: 12rpx;
  padding: 3rpx 12rpx;
  border-radius: 999rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 700;
}
.refresh-btn {
  padding: 9rpx 14rpx;
  border-radius: 12rpx;
  color: #2F78F6;
  font-size: 21rpx;
  font-weight: 650;
}
.refresh-btn-hover {
  background: #EAF3FF;
}
.device-row {
  min-height: 88rpx;
  margin: 0 20rpx;
  padding: 12rpx 2rpx;
}
.device-row + .device-row {
  border-top: 1rpx solid #E8EEF5;
}
.device-row-hover {
  background: #F7FAFE;
}
.device-icon,
.empty-icon {
  width: 54rpx;
  height: 54rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: #EEF5FD;
  color: #2F78F6;
  font-size: 21rpx;
  font-weight: 650;
}
.device-icon {
  margin-right: 14rpx;
}
.empty-state {
  padding: 42rpx 24rpx 46rpx;
  display: flex;
  align-items: center;
  flex-direction: column;
}
.empty-title {
  margin-top: 18rpx;
  color: #172033;
  font-size: 25rpx;
  font-weight: 650;
}
.empty-sub {
  margin-top: 8rpx;
  color: #8B97A8;
  font-size: 20rpx;
  text-align: center;
}
.info-strip {
  margin: 0 8rpx;
  padding: 15rpx 18rpx;
  border-radius: 14rpx;
  background: #EAF3FF;
}
.info-text {
  color: #55708F;
  font-size: 20rpx;
  line-height: 1.5;
}
.footer-safe {
  height: 36rpx;
}

.statusbar-spacer { width: 100%; }
</style>
