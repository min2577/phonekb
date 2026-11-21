<template>
<view :class="['page', appAppearanceClasses]" :style="appAppearanceStyle">
  <view class="statusbar-spacer" :style="{ height: statusBarHeight + 'px' }"></view>
  <view class="hero-card">
    <view class="hero-icon">⌨</view>
    <text class="hero-title">手机键盘</text>
    <text class="hero-sub">连接电脑并开始控制</text>
  </view>

  <view class="section-card mode-section">
    <text class="section-title">连接模式</text>
    <view class="mode-grid">
      <view :class="['mode-item', mode === 'usb' ? 'mode-item-active' : '']" @tap="onSetMode('usb')">
        <text class="mode-icon">⌁</text>
        <text class="mode-name">USB</text>
      </view>
      <view :class="['mode-item', mode === 'wifi' ? 'mode-item-active' : '']" @tap="onSetMode('wifi')">
        <text class="mode-icon">◉</text>
        <text class="mode-name">WiFi</text>
      </view>
      <view :class="['mode-item', mode === 'ble' ? 'mode-item-active' : '']" @tap="onSetMode('ble')">
        <text class="mode-icon">ᛒ</text>
        <text class="mode-name">蓝牙</text>
      </view>
    </view>
    <text v-if="mode === 'usb'" class="mode-note">USB 模式：电脑端开启 ADB 反向端口后直接连接。</text>
    <text v-else-if="mode === 'wifi'" class="mode-note">WiFi 模式：手机与电脑需要连接同一局域网。</text>
    <text v-else class="mode-note">蓝牙模式：先完成系统配对，再从设备列表选择电脑。</text>
  </view>

  <view v-if="devtoolsTip" class="tip-strip"><text class="tip-text">{{ devtoolsTip }}</text></view>

  <block v-if="mode === 'wifi'">
    <view class="section-card action-section">
      <button class="primary-btn" @tap="onScan">扫码连接</button>
    </view>
    <view class="manual-title"><text>手动连接</text></view>
    <view class="section-card form-card">
      <view class="field">
        <text class="field-label">电脑 IP 地址</text>
        <view class="field-control">
          <input class="field-input" placeholder="192.168.1.4" placeholder-style="font-size:24rpx;color:#9AA6B6" :value="host" @input="onHostInput" />
          <view class="paste-btn" @tap="onPasteHost">粘贴</view>
        </view>
      </view>
      <view class="field">
        <text class="field-label">6 位配对码</text>
        <view class="field-control">
          <input class="field-input code-input" placeholder="ABCDEF" placeholder-style="font-size:24rpx;color:#9AA6B6" :value="code" @input="onCodeInput" maxlength="6" />
          <view class="paste-btn" @tap="onPasteCode">粘贴</view>
        </view>
      </view>
      <button :class="['primary-btn', !canConnect ? 'primary-btn-disabled' : '']" :disabled="!canConnect" @tap="onManualConnect">连接</button>
      <text class="form-hint">手机和电脑需处于同一局域网</text>
    </view>
  </block>

  <view v-else-if="mode === 'usb'" class="section-card form-card">
    <view class="connection-illustration">USB</view>
    <text class="connection-copy">数据线连接完成后，点击下方按钮建立控制通道。</text>
    <button class="primary-btn" @tap="onManualConnect">连接</button>
  </view>

  <view v-else class="section-card bluetooth-card">
    <view class="section-head"><text class="section-title">蓝牙设备</text><text class="section-action" @tap="_startBluetooth(false)">刷新</text></view>
    <text class="bluetooth-status">{{ bleStatus }}</text>
    <scroll-view v-if="bondedDevices.length > 0" scroll-y class="device-list">
      <view v-for="d in bondedDevices" :key="d.address" class="device-row" @tap="onBtPick(d)">
        <view class="device-icon">PC</view>
        <view class="device-copy"><text class="device-name">{{ d.name || d.address }}</text><text class="device-meta">{{ d.address }}</text></view>
        <text class="device-action">连接</text>
      </view>
    </scroll-view>
    <scroll-view v-if="scanDevices.length > 0" scroll-y class="device-list scanned-list">
      <view v-for="d in scanDevices" :key="d.address" class="device-row" @tap="onBtScanPick(d)">
        <view class="device-icon">?</view>
        <view class="device-copy"><text class="device-name">{{ d.name || d.address }}</text><text class="device-meta">{{ d.address }}</text></view>
        <text class="device-action">配对</text>
      </view>
    </scroll-view>
    <button class="primary-btn" @tap="_startScanDevices">{{ scanning ? '搜索中…' : '搜索附近电脑' }}</button>
    <view class="advanced-link" @tap="onOpenBluetoothSettings"><text>高级蓝牙设置与诊断 ›</text></view>
  </view>

  <view v-if="status" :class="['status-strip', statusClass]"><text>{{ status }}</text></view>
  <view class="footer-safe"></view>
</view>
</template>
<script>
import Net from '@/utils/net.js'
import BT from '@/utils/btclient.js'

export default {
  data() {
    return {
      statusBarHeight: 24,
      mode: 'usb',
      host: '', code: '',
      status: '',
      statusClass: 'info',
      canConnect: false,
      devtoolsTip: '',
      bleModalOpen: false,
      bleStatus: '正在启动广播...',
      bleDevices: [],
      bondedDevices: [],
      scanDevices: [],
      scanning: false
    }
  },
  onLoad() {
    try {
      const app = getApp({ allowDefault: true })
      if (app && app.globalData) {
        if (app.globalData.host) this.host = app.globalData.host
        if (app.globalData.code) this.code = app.globalData.code
      }
    } catch (e) {}
    try {
      const sys = uni.getSystemInfoSync()
      if (sys.platform === 'devtools') {
        this.devtoolsTip = '模拟器模式：请把 IP 改成电脑的局域网 IP（电脑弹窗里有显示，如 192.168.1.4），不是 127.0.0.1'
      }
    } catch (e) {}
    try { this.mode = Net.getMode() } catch (e) {}
    this._updateCanConnect()
  },
  onShow() {
    if (this.mode === 'ble') this._startBluetooth(true)
  },
  onUnload() {
    if (this._btStateCb) {
      try { BT.offStateChange(this._btStateCb) } catch (e) {}
      this._btStateCb = null
    }
    if (this._btHidStateCb) {
      try { BT.offHidStateChange(this._btHidStateCb) } catch (e) {}
      this._btHidStateCb = null
    }
  },
  methods: {
    onHostInput(e) { this.host = e.detail.value; this._updateCanConnect() },
    onCodeInput(e) { this.code = (e.detail.value || '').toUpperCase(); this._updateCanConnect() },
    _updateCanConnect() {
      const code = (this.code || '').trim()
      const codeOk = /^[A-Z0-9]{6}$/.test(code)
      if (this.mode === 'usb') {
        // USB å¨ææºä¸æçº¿，ç©çæ¥å¥æ¬èº«å°±æ¯ä¿¡ä»»è¾¹ç，ä¸åè¦æ± 6 ä½éå¯¹ç 
        this.canConnect = true
        return
      }
      if (this.mode === 'ble') {
        this.canConnect = false
        return
      }
      const host = (this.host || '').trim()
      const hostOk = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(host)
      this.canConnect = hostOk && codeOk
    },
    onScan() {
      const self = this
      uni.scanCode({
        scanType: ['qrCode'],
        onlyFromCamera: false,
        success(res) {
          const url = res.result
          let m = url.match(/^wss?:\/\/([^:\/]+):(\d+)\/?\?t=([^&]+)(?:&code=([A-Z0-9]{6}))?$/)
          if (m) {
            const host = m[1], port = parseInt(m[2], 10), token = m[3]
            const code = m[4] || token.slice(0, 6).toUpperCase()
            try {
              const app = getApp({ allowDefault: true })
              if (app && app.globalData) { app.globalData.host = host; app.globalData.port = port; app.globalData.code = code; app.globalData.token = token }
            } catch (e) {}
            self.host = host; self.code = code; self._updateCanConnect(); self._connect()
            return
          }
          m = url.match(/^wss?:\/\/([^:\/]+):(\d+)\/?\?secret=(\S+)$/)
          if (!m) { uni.showToast({ title: '二维码格式不对', icon: 'none' }); return }
          const host = m[1], port = parseInt(m[2], 10), secret = m[3]
          const code = secret.slice(0, 6).toUpperCase()
          try {
            const app = getApp({ allowDefault: true })
            if (app && app.globalData) { app.globalData.host = host; app.globalData.port = port; app.globalData.code = code; app.globalData.token = null }
          } catch (e) {}
          self.host = host; self.code = code; self._updateCanConnect(); self._connect()
        },
        fail(error) {
          const detail = String((error && (error.errMsg || error.message)) || '')
          if (/cancel/i.test(detail)) return
          let title = '扫码失败，请检查相机权限后重试'
          if (/barcode|模块/i.test(detail)) title = '当前运行环境缺少扫码模块'
          else if (/permission|camera|权限/i.test(detail)) title = '请允许相机权限后重试'
          uni.showToast({ title: title, icon: 'none', duration: 2500 })
        }
      })
    },
    onPasteHost() { this._paste('host') },
    onPasteCode() { this._paste('code') },
    _paste(field) {
      const self = this
      uni.getClipboardData({
        success(res) {
          let val = (res.data || '').trim()
          if (field === 'code') val = val.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6)
          else { const m = val.match(/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/); val = m ? m[0] : val }
          if (field === 'host') self.host = val
          else self.code = val
          self._updateCanConnect()
          uni.showToast({ title: '已粘贴: ' + val, icon: 'none', duration: 1200 })
        },
        fail() { uni.showToast({ title: '剪贴板为空', icon: 'none' }) }
      })
    },
    onManualConnect() {
      if (!this.canConnect) {
        var tip = this.mode === 'usb' ? '无法连接，请检查 adb reverse 和 PC 托盘' : '请填正确的 IP 和 6 位配对码'
        uni.showToast({ title: tip, icon: 'none' })
        return
      }
      try {
        const app = getApp({ allowDefault: true })
        if (app && app.globalData) { app.globalData.host = this.host.trim(); app.globalData.code = this.code.trim() }
      } catch (e) {}
      this._connect()
    },
    _connect() {
      const self = this
      this.status = '连接中…'; this.statusClass = 'info'
      let code = this.code
      try {
        const app = getApp({ allowDefault: true })
        if (app && app.globalData && app.globalData.code) code = app.globalData.code
      } catch (e) {}
      if (this.mode === 'usb') {
        var usbCode = code || 'USB_LOCAL_TRUST'
        Net.connect({
          host: '127.0.0.1', port: 9877, code: usbCode,
          onConnected() {
            self.status = '✓ 已连接（USB），跳转中…'; self.statusClass = 'ok'
            setTimeout(function() { uni.switchTab({ url: '/pages/panel/panel' }) }, 400)
          },
          onError(msg) { self.status = '✗ ' + msg + '（请确认电脑端已打开、USB 调试已开启并授权此电脑）'; self.statusClass = 'err' },
          onDisconnected() { self.status = 'USB 已断开（请检查数据线）'; self.statusClass = 'err' }
        })
      } else {
        let host = this.host, port = 9876, token = null
        try {
          const app = getApp({ allowDefault: true })
          if (app && app.globalData) {
            if (app.globalData.host) host = app.globalData.host
            if (app.globalData.port) port = app.globalData.port
            if (app.globalData.token) token = app.globalData.token
          }
        } catch (e) {}
        Net.connect({
          host: host, port: port, code: code, token: token,
          onConnected() {
            self.status = '✓ 已连接（WiFi），跳转中…'; self.statusClass = 'ok'
            setTimeout(function() { uni.switchTab({ url: '/pages/panel/panel' }) }, 400)
          },
          onError(msg) { self.status = '✗ ' + msg; self.statusClass = 'err' },
          onDisconnected() { self.status = '已断开'; self.statusClass = 'err' }
        })
      }
    },
    onSetMode(mode) {
      Net.setMode(mode)
      this.mode = mode
      this._updateCanConnect()
      const tipMap = {
        usb: '已切换到 USB 模式',
        wifi: '已切换到 WiFi 模式',
        ble: '已切换到蓝牙模式'
      }
      uni.showToast({ title: tipMap[mode] || ('已切换: ' + mode), icon: 'none', duration: 1200 })
      if (mode === 'ble') {
        this._startBluetooth(true)
        return
      }
    },
    _startBluetooth(autoConnect) {
      const self = this
      self.bleModalOpen = true
      self.scanDevices = []
      self.scanning = false
      self.bleStatus = '正在查找已配对的电脑…'
      if (!self._btStateCb) {
        self._btStateCb = function(s) {
          if (s === 'connected') self.bleStatus = '完整蓝牙已连接'
          else if (s === 'connecting' || s === 'handshaking' || s === 'reconnecting') self.bleStatus = '正在连接电脑…'
        }
        try { BT.onStateChange(self._btStateCb) } catch (e) {}
      }
      if (!self._btHidStateCb) {
        self._btHidStateCb = function(hid) {
          if (hid && hid.connected) {
            self.bleStatus = Net.isConnected()
              ? '完整蓝牙已连接'
              : '基础蓝牙已连接：快捷键、键盘、鼠标可用'
          }
        }
        try { BT.onHidStateChange(self._btHidStateCb) } catch (e) {}
      }
      // 先刷新已配对列表
      BT.listBondedDevices().then(function(devices) {
        self.bondedDevices = devices
        if (devices.length === 0) {
          self.bleStatus = '没有已配对的电脑，点下面的"搜索电脑"找到后一键配对'
        } else {
          self.bleStatus = '已找到 ' + devices.length + ' 台电脑，点一台直接连'
          if (autoConnect && !self._btConnectingAddress && !BT.canSendKeyboard()) {
            var lastAddress = ''
            try { lastAddress = uni.getStorageSync('phonekb.last_bt_addr') || '' } catch (e) {}
            var target = devices.find(function(item) { return item.address === lastAddress })
            if (!target && devices.length === 1) target = devices[0]
            if (target) self.onBtPick(target)
          } else if (BT.canSendKeyboard()) {
            var hid = BT.getHidStatus()
            self.bleStatus = Net.isConnected() || (hid && hid.businessConnected)
              ? '完整蓝牙已连接'
              : '基础蓝牙已连接：快捷键、键盘、鼠标可用'
          }
        }
      }).catch(function(err) {
        self.bleStatus = '✗ ' + (err || '启动失败')
      })
    },
    _startScanDevices() {
      const self = this
      if (self.scanning) return
      self.scanning = true
      self.scanDevices = []
      self.bleStatus = '扫描中（电脑要打开"可被发现"）…'
      BT.startDiscovery().then(function(res) {
        self.scanning = false
        if (!res.ok) {
          self.bleStatus = '✗ 扫描失败: ' + res.msg
          return
        }
        self.scanDevices = res.devices
        self.bleStatus = '扫到 ' + res.devices.length + ' 个设备，点一个配对'
      }).catch(function(err) {
        self.scanning = false
        var m = (err && err.message) ? err.message : (err || '')
        self.bleStatus = '✗ ' + m + '  点“重新扫描”可重试'
      })
    },
    onBtScanPick(d) {
      const self = this
      self.bleStatus = '正在配对 ' + (d.name || d.address) + '…（手机上会弹"配对"框，要点"配对"）'
      BT.pairDevice(d).then(function() {
        self.bleStatus = '✓ 配对成功，正在连…'
        // 重新刷新列表
        return BT.listBondedDevices()
      }).then(function(devs) {
        self.bondedDevices = devs
        // 找刚配的那个，自动 connect
        const target = devs.find(function(x) { return x.address === d.address })
        if (target) {
          self.onBtPick(target)
          return true
        }
        throw new Error('配对成功，但没有在已配对列表中找到该电脑')
      }).catch(function(err) {
        self.bleStatus = '✗ 配对失败: ' + (err && err.message ? err.message : err)
      })
    },
    onBtPick(d) {
      const self = this
      if (!d || !d.address || self._btConnectingAddress) return
      self._btConnectingAddress = d.address
      self.bleStatus = '正在连接 ' + (d.name || d.address) + '...'
      try { BT.close() } catch (e) {}
      BT.connectDevice(d).then(function() {
        self._btConnectingAddress = ''
        self.bleModalOpen = false
        self.status = '已连接（蓝牙完整模式），跳转中…'
        self.statusClass = 'ok'
        setTimeout(function() { uni.switchTab({ url: '/pages/panel/panel' }) }, 400)
      }).catch(function(err) {
        self._waitForBasicBluetooth(3500).then(function(basicConnected) {
          self._btConnectingAddress = ''
          if (basicConnected) {
            try { uni.setStorageSync('phonekb.last_bt_addr', d.address) } catch (e) {}
            self.bleStatus = '基础蓝牙已连接：快捷键、键盘、鼠标可用'
            self.status = '已连接（蓝牙基础模式），跳转中…'
            self.statusClass = 'ok'
            setTimeout(function() { uni.switchTab({ url: '/pages/panel/panel' }) }, 400)
          } else {
            self.bleStatus = '连接失败: ' + (err.message || err)
          }
        })
      })
    },
    _waitForBasicBluetooth(timeoutMs) {
      return new Promise(function(resolve) {
        var startedAt = Date.now()
        var check = function() {
          if (BT.canSendKeyboard() || BT.canSendMouse()) { resolve(true); return }
          if (Date.now() - startedAt >= timeoutMs) { resolve(false); return }
          setTimeout(check, 150)
        }
        check()
      })
    },
    onOpenBluetoothSettings() {
      uni.navigateTo({ url: '/pages/bt-settings/bt-settings' })
    },
    onBlePick() { /* Peripheral 模式不需要选设备 */ },
    onBleRescan() { this._startBluetooth() },
    onBleModalClose() {
      this.bleModalOpen = false
      try { BT.close() } catch (e) {}
    },
  }
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
.hero-card,
.section-card {
  margin: 0 8rpx 16rpx;
  background: #FFFFFF;
  border: 1rpx solid #DCE6F1;
  border-radius: 22rpx;
  box-shadow: 0 8rpx 22rpx rgba(47, 78, 113, 0.06);
}
.hero-card {
  padding: 24rpx 22rpx;
  display: flex;
  align-items: center;
  flex-direction: column;
}
.hero-icon {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 19rpx;
  background: #DCEBFF;
  color: #172033;
  font-size: 34rpx;
  font-weight: 700;
}
.hero-title {
  margin-top: 14rpx;
  color: #172033;
  font-size: 31rpx;
  font-weight: 750;
}
.hero-sub {
  margin-top: 6rpx;
  color: #728197;
  font-size: 21rpx;
}
.section-card {
  padding: 18rpx 20rpx;
}
.section-title {
  color: #172033;
  font-size: 26rpx;
  font-weight: 700;
}
.mode-grid {
  margin-top: 16rpx;
  display: flex;
  justify-content: space-between;
}
.mode-item {
  width: 31%;
  min-height: 104rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border: 1rpx solid #DCE6F1;
  border-radius: 16rpx;
  background: #F7FAFE;
  color: #586A80;
}
.mode-item-active {
  border-color: #99C0FF;
  background: #EAF3FF;
  color: #2F78F6;
}
.mode-icon {
  font-size: 30rpx;
  font-weight: 700;
}
.mode-name {
  margin-top: 9rpx;
  font-size: 21rpx;
  font-weight: 650;
}
.mode-note {
  display: block;
  margin-top: 16rpx;
  color: #718196;
  font-size: 19rpx;
  line-height: 1.45;
}
.primary-btn {
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14rpx;
  background: #2F78F6;
  color: #FFFFFF;
  font-size: 24rpx;
  font-weight: 700;
  box-shadow: 0 8rpx 18rpx rgba(47, 120, 246, 0.20);
}
.primary-btn:active {
  background: #2469DC;
  transform: scale(0.99);
}
.primary-btn-disabled {
  background: #BFCBDD;
  box-shadow: none;
}
.manual-title {
  margin: -2rpx 18rpx 12rpx;
  color: #64758B;
  font-size: 21rpx;
  font-weight: 650;
}
.field + .field {
  margin-top: 16rpx;
}
.field-label {
  display: block;
  margin-bottom: 10rpx;
  color: #53657B;
  font-size: 21rpx;
  font-weight: 600;
}
.field-control {
  display: flex;
  align-items: center;
}
.field-input {
  min-width: 0;
  flex: 1;
  height: 66rpx;
  padding: 0 18rpx;
  border: 1rpx solid #DCE6F1;
  border-radius: 13rpx;
  background: #F7FAFE;
  color: #172033;
  font-size: 24rpx;
}
.paste-btn {
  height: 66rpx;
  margin-left: 10rpx;
  padding: 0 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid #DCE6F1;
  border-radius: 13rpx;
  background: #FFFFFF;
  color: #2F78F6;
  font-size: 21rpx;
  font-weight: 650;
}
.form-card .primary-btn {
  margin-top: 20rpx;
}
.form-hint,
.connection-copy,
.bluetooth-status {
  display: block;
  margin-top: 14rpx;
  color: #7C899B;
  font-size: 19rpx;
  line-height: 1.45;
  text-align: center;
}
.connection-illustration {
  width: 84rpx;
  height: 64rpx;
  margin: 4rpx auto 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16rpx;
  background: #EAF3FF;
  color: #2F78F6;
  font-size: 22rpx;
  font-weight: 750;
}
.section-head,
.device-row {
  display: flex;
  align-items: center;
}
.section-head {
  justify-content: space-between;
}
.section-action,
.device-action {
  color: #2F78F6;
  font-size: 23rpx;
  font-weight: 650;
}
.device-list {
  max-height: 280rpx;
  margin-top: 16rpx;
}
.scanned-list {
  border-top: 1rpx solid #E8EEF5;
}
.device-row {
  min-height: 82rpx;
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
  font-size: 19rpx;
  font-weight: 700;
}
.device-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}
.device-name {
  color: #172033;
  font-size: 23rpx;
  font-weight: 650;
}
.device-meta {
  margin-top: 4rpx;
  color: #7E8B9E;
  font-size: 18rpx;
}
.bluetooth-card .primary-btn {
  margin-top: 22rpx;
}
.advanced-link {
  padding: 20rpx 0 4rpx;
  color: #65768A;
  font-size: 20rpx;
  text-align: center;
}
.tip-strip,
.status-strip {
  margin: 0 8rpx 14rpx;
  padding: 14rpx 18rpx;
  border-radius: 13rpx;
  background: #EAF3FF;
  color: #55708F;
  font-size: 20rpx;
  text-align: center;
}
.status-strip {
  background: #EEF4FA;
  color: #506177;
}
.status-strip.success,
.status-strip.ok {
  background: #EAF8EF;
  color: #159447;
}
.status-strip.error,
.status-strip.err {
  background: #FDECEE;
  color: #C4313C;
}
.footer-safe {
  height: 24rpx;
}

.statusbar-spacer { width: 100%; }
</style>
