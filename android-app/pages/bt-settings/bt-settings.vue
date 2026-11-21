<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="header-card">
    <view class="header-row">
      <view class="header-copy"><text class="header-label">蓝牙开关</text><text class="header-sub">{{ btEnabled ? '已打开' : '未打开' }}</text></view>
      <switch :checked="btEnabled" :disabled="btToggling" color="#2F78F6" @change="onToggleBt" />
    </view>
    <view class="header-row">
      <text class="header-label">手机蓝牙名称</text>
      <text class="header-value">{{ btName || '加载中…' }}</text>
    </view>
  </view>

  <view v-if="lastConnected" class="section">
    <text class="section-title">上次设备</text>
    <view class="device-row" @tap="onTapBonded(lastConnected)">
      <view class="device-icon">{{ lastConnected.icon || 'PC' }}</view>
      <view class="device-copy"><text class="device-name">{{ lastConnected.name }}</text><text class="device-meta">{{ lastConnected.address }}</text></view>
      <text v-if="connectionState === 'connected'" class="status-badge status-on">使用中</text>
      <text v-else class="status-badge status-off">未连接</text>
    </view>
  </view>

  <view class="section">
    <view class="section-head"><text class="section-title">已配对设备</text><text class="section-action" @tap="_refreshAll">刷新</text></view>
    <view v-if="loadingBonded" class="empty-row">正在读取已配对列表…</view>
    <view v-else-if="bonded.length === 0" class="empty-row">还没有配对过的设备</view>
    <view v-for="d in bonded" :key="d.address" class="device-row" @tap="onTapBonded(d)">
      <view class="device-icon">{{ d.icon || 'PC' }}</view>
      <view class="device-copy"><text class="device-name">{{ d.name || '未知设备' }}</text><text class="device-meta">{{ d.address }}</text></view>
      <text v-if="d.isConnected" class="status-badge status-on">使用中</text>
      <text v-else-if="hasScanned(d.address)" class="status-badge status-near">在线 {{ getDistanceText(d.address) }}</text>
      <text v-else class="status-badge status-off">离线</text>
    </view>
  </view>

  <view class="section">
    <text class="section-title">周围的设备</text>
    <view v-if="scanning" class="empty-row">正在搜索附近设备…</view>
    <view v-else-if="scanned.length === 0" class="empty-row">暂未发现设备，请点击下方搜索。</view>
    <view v-for="d in scanned" :key="d.address" class="device-row" @tap="onTapScanned(d)">
      <view class="device-icon">{{ d.icon || '?' }}</view>
      <view class="device-copy"><text class="device-name">{{ d.name || '未知设备' }}</text><text class="device-meta">{{ d.address }} · {{ d.rssi }} dBm</text></view>
      <text v-if="d.bondState === 12" class="status-badge status-on">已配对</text>
      <text v-else class="status-badge status-near">未配对</text>
    </view>
  </view>

  <view class="action-bar">
    <button class="primary-btn" :disabled="scanning || !btEnabled" @tap="onScan">{{ scanning ? '搜索中…' : '搜索设备' }}</button>
    <button class="secondary-btn" @tap="onDiagnose">蓝牙诊断</button>
  </view>

  <view class="status-panel">
    <text class="status-title">App 蓝牙状态</text>
    <view v-for="line in statusLines" :key="line.k" class="status-row">
      <text class="status-label">{{ line.label }}</text>
      <text :class="['status-value', line.cls]">{{ line.value }}</text>
    </view>
    <text v-if="statusLoading" class="status-loading">正在读取…</text>
  </view>

  <view v-if="diagText" class="diag-block">
    <text class="diag-title">诊断结果（长按复制）</text>
    <text class="diag-body" :selectable="true" @longpress="onCopyDiag">{{ diagText }}</text>
  </view>

  <view v-if="toastMsg" :class="['toast', toastKind]"><text>{{ toastMsg }}</text></view>
  <view class="footer-safe"></view>
</view>
</template>

<script>
import BT from '@/utils/btclient.js'
import Net from '@/utils/net.js'

export default {
  data() {
    return {
      statusBarHeight: 24,
      btEnabled: false,
      btToggling: false,
      btName: '',
      btAddress: '',
      bonded: [],
      scanned: [],
      loadingBonded: true,
      scanning: false,
      lastAddr: '',
      diagText: '',
      statusLines: [],
      statusLoading: true,
      toastMsg: '',
      toastKind: 'info',
      connectionState: 'idle',
      stateListener: null,
      hidStateListener: null,
    }
  },

  computed: {
    lastConnected() {
      if (!this.lastAddr) return null
      return this.bonded.find(function (d) { return d.address === this.lastAddr }.bind(this)) || null
    },
  },

  onLoad() { try { const sys = uni.getSystemInfoSync(); if (sys && sys.statusBarHeight) this.statusBarHeight = sys.statusBarHeight } catch (e) {}
    var self = this
    self.connectionState = BT.isConnected() ? 'connected' : 'idle'
    self.stateListener = function (state) {
      self.connectionState = state
      self._refreshBonded()
      self._loadStatus()
    }
    BT.onStateChange(self.stateListener)
    self.hidStateListener = function () { self._loadStatus() }
    BT.onHidStateChange(self.hidStateListener)
    try { self.lastAddr = uni.getStorageSync('phonekb.last_bt_addr') || '' } catch (e) {}
    this._load()
    this._loadStatus()
  },

  onShow() {
    this._refreshBtInfo()
    this._refreshBonded()
  },

  onUnload() {
    if (this.stateListener) BT.offStateChange(this.stateListener)
    if (this.hidStateListener) BT.offHidStateChange(this.hidStateListener)
    this.stateListener = null
    this.hidStateListener = null
  },

  methods: {
    _setToast(msg, kind) {
      this.toastMsg = msg || ''
      this.toastKind = kind || 'info'
      if (msg) {
        var self = this
        setTimeout(function () { if (self.toastMsg === msg) self.toastMsg = '' }, 4000)
      }
    },

    async _load() {
      await this._refreshBtInfo()
      await this._refreshBonded()
    },

    async _refreshBtInfo() {
      try {
        var info = await BT.getBtInfo()
        if (info.ok) {
          this.btEnabled = !!info.enabled
          this.btName = info.name || ''
          this.btAddress = info.address || ''
        } else {
          this._setToast(info.msg, 'err')
        }
      } catch (e) {
        this._setToast('读蓝牙信息失败：' + (e.message || e), 'err')
      }
    },

    async _refreshBonded() {
      this.loadingBonded = true
      try {
        var list = await BT.listBondedDevices()
        this.bonded = list || []
      } catch (e) {
        this.bonded = []
        this._setToast('读已配对失败：' + (e.message || e), 'err')
      } finally {
        this.loadingBonded = false
      }
    },

    _refreshAll() {
      this._refreshBtInfo()
      this._refreshBonded()
      this.onScan()
    },

    async onToggleBt(e) {
      var want = e.detail.value
      this.btToggling = true
      this._setToast(want ? '正在打开蓝牙…' : '正在关闭蓝牙…', 'info')
      try {
        var r = await BT.setBtEnabled(want)
        if (r.ok) {
          setTimeout(function () { this._refreshBtInfo() }.bind(this), 1500)
        } else {
          this._setToast('切换失败：' + r.msg, 'err')
        }
      } catch (e) {
        this._setToast('切换异常：' + (e.message || e), 'err')
      } finally {
        this.btToggling = false
      }
    },

    async onScan() {
      if (this.scanning) return
      if (!this.btEnabled) { this._setToast('请先打开蓝牙开关', 'err'); return }
      this.scanning = true
      this.scanned = []
      try {
        var res = await BT.startDiscovery()
        if (!res.ok) {
          this._setToast('✗ ' + res.msg, 'err')
        } else {
          this.scanned = res.devices || []
        }
      } catch (e) {
        this._setToast('✗ ' + (e.message || e), 'err')
      } finally {
        this.scanning = false
      }
    },

    hasScanned(addr) {
      for (var i = 0; i < this.scanned.length; i++) if (this.scanned[i].address === addr) return true
      return false
    },

    getDistanceText(addr) {
      for (var i = 0; i < this.scanned.length; i++) {
        if (this.scanned[i].address === addr) {
          var d = this.scanned[i].distance
          return d ? d + 'm' : ''
        }
      }
      return ''
    },

    async onTapBonded(d) {
      if (!d || !d.device) return
      BT.close()
      this._setToast('正在连接 ' + (d.name || d.address) + '…', 'info')
      try {
        await BT.connectDevice(d)
        Net.setMode('ble')
        this.lastAddr = d.address
        try { uni.setStorageSync('phonekb.last_bt_addr', d.address) } catch (e) {}
        this._setToast('✓ 已连接 ' + (d.name || d.address) + '，', 'ok')

        var self = this
        uni.switchTab({ url: '/pages/panel/panel' })

      } catch (e) {
        if (BT.canSendMouse()) {
          Net.setMode('ble')
          this.lastAddr = d.address
          try { uni.setStorageSync('phonekb.last_bt_addr', d.address) } catch (storageError) {}
          this._setToast('标准鼠标已连接；桌面业务通道未连接', 'ok')
          uni.switchTab({ url: '/pages/panel/panel' })
        } else this._setToast('连接失败：' + (e.message || e), 'err')
      }
    },

    async onTapScanned(d) {
      if (!d || !d.device) return
      if (d.bondState === 12) { this.onTapBonded(d); return }
      this._setToast('正在配对 ' + (d.name || d.address) + '（手机/电脑都要确认）…', 'info')
      try {
        await BT.pairDevice(d)
        this._setToast('配对成功，正在连接…', 'ok')
        await this._refreshBonded()
        var target = null
        for (var i = 0; i < this.bonded.length; i++) if (this.bonded[i].address === d.address) target = this.bonded[i]
        if (target) {
          await BT.connectDevice(target)
          Net.setMode('ble')
          this.lastAddr = target.address
          try { uni.setStorageSync('phonekb.last_bt_addr', target.address) } catch (e) {}
          this._setToast('✓ 已连接 ' + target.name + '，', 'ok')

          var self = this
        uni.switchTab({ url: '/pages/panel/panel' })

        }
      } catch (e) {
        if (typeof target !== 'undefined' && target && BT.canSendMouse()) {
          Net.setMode('ble')
          this.lastAddr = target.address
          try { uni.setStorageSync('phonekb.last_bt_addr', target.address) } catch (storageError) {}
          this._setToast('标准鼠标已连接；桌面业务通道未连接', 'ok')
          uni.switchTab({ url: '/pages/panel/panel' })
        } else this._setToast('配对失败：' + (e.message || e), 'err')
      }
    },

    async onDiagnose() {
      this.diagText = '诊断中…'
      try {
        var r = await BT.diagnose()
        this.diagText = (r && r.lines) ? r.lines.join('\n') : '无返回值'
      } catch (e) {
        this.diagText = '诊断异常: ' + (e.message || e)
      }
    },

    onCopyDiag() {
      uni.setClipboardData({ data: this.diagText || '' })
      this._setToast('已复制诊断结果到剪贴板', 'ok')
    },

    async _loadStatus() {
      this.statusLoading = true
      try {
        var r = await BT.diagnose()
        var raw = (r && r.lines) ? r.lines : []
        this.diagText = raw.join('\n')
        this.statusLines = raw.map(function (line, i) {
          var ok = !/返回 null|未授|报错|失败|拒绝|不可用|未连接|error|unavailable/.test(line)
          var icon = ok ? '✅' : '❌'
          var cls = ok ? 'ok' : 'err'
          var parts = line.split(': ', 2)
          return {
            k: String(i),
            icon: icon,
            label: parts[0] || line,
            value: parts.slice(1).join(': ') || '',
            cls: cls,
          }
        })
      } catch (e) {
        this.statusLines = [{ k: 'err', icon: '❌', label: '诊断函数报错', value: String(e.message || e), cls: 'err' }]
        this.diagText = '诊断函数报错: ' + (e.message || e)
      } finally {
        this.statusLoading = false
      }
    },
  },
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
.header-card,
.section,
.status-panel,
.diag-block {
  margin: 0 8rpx 16rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 7rpx 20rpx rgba(47, 78, 113, 0.055);
}
.header-card,
.status-panel,
.diag-block {
  padding: 6rpx 20rpx;
}
.header-row,
.section-head,
.device-row,
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-row {
  min-height: 78rpx;
}
.header-row + .header-row {
  border-top: 1rpx solid #E8EEF5;
}
.header-copy,
.device-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.header-label,
.section-title {
  color: #172033;
  font-size: 25rpx;
  font-weight: 700;
}
.header-sub,
.device-meta {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 19rpx;
}
.header-value {
  color: #506177;
  font-size: 21rpx;
  font-weight: 600;
}
.section {
  padding: 17rpx 20rpx 4rpx;
}
.section-head {
  min-height: 48rpx;
}
.section-action {
  padding: 6rpx 10rpx;
  color: #2F78F6;
  font-size: 20rpx;
  font-weight: 650;
}
.device-row {
  min-height: 80rpx;
  border-top: 1rpx solid #E8EEF5;
}
.device-icon {
  width: 50rpx;
  height: 50rpx;
  margin-right: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 13rpx;
  background: #EEF5FD;
  color: #2F78F6;
  font-size: 18rpx;
  font-weight: 700;
}
.device-name {
  color: #172033;
  font-size: 23rpx;
  font-weight: 650;
}
.status-badge {
  padding: 4rpx 11rpx;
  border-radius: 999rpx;
  font-size: 17rpx;
  font-weight: 650;
}
.status-on {
  background: #EAF8EF;
  color: #159447;
}
.status-near {
  background: #EAF3FF;
  color: #2F78F6;
}
.status-off {
  background: #EDF1F6;
  color: #7C8796;
}
.empty-row {
  padding: 32rpx 0;
  border-top: 1rpx solid #E8EEF5;
  color: #8996A7;
  font-size: 20rpx;
  text-align: center;
}
.action-bar {
  margin: 0 8rpx 16rpx;
}
.primary-btn,
.secondary-btn {
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  font-size: 23rpx;
  font-weight: 700;
}
.primary-btn {
  background: #2F78F6;
  color: #FFFFFF;
  box-shadow: 0 8rpx 18rpx rgba(47, 120, 246, 0.20);
}
.secondary-btn {
  margin-top: 14rpx;
  border: 1rpx solid #DCE6F1;
  background: #FFFFFF;
  color: #506177;
}
.status-panel {
  padding-top: 18rpx;
  padding-bottom: 18rpx;
}
.status-title,
.diag-title {
  display: block;
  margin-bottom: 10rpx;
  color: #53657B;
  font-size: 23rpx;
  font-weight: 700;
}
.status-row {
  min-height: 56rpx;
  border-top: 1rpx solid #EEF2F7;
}
.status-label,
.status-value {
  font-size: 21rpx;
}
.status-label {
  color: #7E8B9E;
}
.status-value {
  color: #172033;
  font-weight: 650;
}
.status-loading {
  display: block;
  padding: 18rpx 0 4rpx;
  color: #8996A7;
  font-size: 21rpx;
}
.diag-block {
  padding-top: 20rpx;
  padding-bottom: 20rpx;
}
.diag-body {
  color: #607087;
  font-size: 20rpx;
  line-height: 1.5;
}
.toast {
  position: fixed;
  left: 50%;
  bottom: 50rpx;
  transform: translateX(-50%);
  padding: 16rpx 24rpx;
  border-radius: 14rpx;
  background: #172033;
  color: #FFFFFF;
  font-size: 22rpx;
  z-index: 30;
}
.toast.err {
  background: #C4313C;
}
.footer-safe {
  height: 24rpx;
}

.statusbar-spacer { width: 100%; }
</style>
