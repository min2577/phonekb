// utils/bleclient.js
// PhoneKB BLE Peripheral via Android 原生 BluetoothGattServer + BluetoothLeAdvertiser
// 调用栈：plus.android.importClass + plus.android.implements + plus.android.runtimeMainActivity。
//
// uni-app 的 uni.createBLEPeripheralServer 在 HBuilderX 5.14(uni-app v3 release) 未实现。
// 这里直接走 Android 系统 API，所有 BLE 5 广播功能都稳定可跑。
//
// 链路（角色反转后）：
//   phone -> Notify (a1b2c3d4-0002-...) -> desktop ble_bridge -> usb_server._process_msg
//   desktop -> Write  (a1b2c3d4-0003-...) -> phone 接收响应
//
// 协议（不变）：
//   frame = [0xAA, total, idx] + chunk(<=16 bytes)    3 字节头
//   total <= 255
//
// API（与 ws/usb client 兼容）：
//   connect(opts)      // 准备 GATT server + 开始广播
//   send(obj) / trigger() / triggerSlot(id)
//   close() / isConnected()
//   onStateChange(cb) / onMessage(cb) / onHello(cb) / onLayouts(cb)
//
// 自动免配对：desktop ble_bridge 在第一次 Notify 时把 session 注册到 _usb_sessions。

const SERVICE_UUID = 'a1b2c3d4-0001-4000-8000-00805f9b34fb'
const NOTIFY_CHAR_UUID = 'a1b2c3d4-0002-4000-8000-00805f9b34fb'  // phone -> pc (commands)
const WRITE_CHAR_UUID = 'a1b2c3d4-0003-4000-8000-00805f9b34fb'   // pc -> phone (responses)
const CCCD_UUID = '00002902-0000-1000-8000-00805f9b34fb'

const MAGIC = 0xAA
const CHUNK_DATA = 16

// ===== 模块状态 =====
let _state = 'idle'           // idle | advertising | connected
let _handlers = {}

// 原生引用（+null 检查）
let _bm = null
let _adapter = null
let _advertiser = null
let _gattServer = null
let _service = null
let _notifyChar = null
let _writeChar = null
let _pcDevice = null         // 当前连接的 PC 端 BluetoothDevice

// Rx 拼装（PC -> phone）
let _rxTotal = 0
let _rxParts = []
let _rxSeen = 0
let _rxReady = true

// 缓存（与 wsclient/usbclient 一致）
let _layouts = { layouts: [], global_pages: [] }
let _helloInfo = null

// 回调
let _stateChangeCallbacks = []
let _messageCallbacks = []
let _helloCallbacks = []
let _layoutsCallbacks = []

// ===== 字节 / 帧协议 =====

function _str2bytes(str) {
  const buf = new ArrayBuffer(str.length)
  const view = new Uint8Array(buf)
  for (let i = 0; i < str.length; i++) view[i] = str.charCodeAt(i) & 0xFF
  return view
}

function _bytes2str(view) {
  let s = ''
  for (let i = 0; i < view.length; i++) s += String.fromCharCode(view[i] & 0xFF)
  return s
}

// 从 plus.android 拿到的 java byte[] 转 Uint8Array（plus.android 会把 byte[] 暴露为 JS array，每个元素是 0-255）
function _javaBytesToUint8(byteArr) {
  const len = byteArr.length
  const out = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    let b = byteArr[i]
    if (b < 0) b += 256
    out[i] = b
  }
  return out
}

function _frameEncode(payload) {
  if (!payload || payload.length === 0) return []
  if (payload.length <= CHUNK_DATA) {
    const out = new Uint8Array(3 + payload.length)
    out[0] = MAGIC; out[1] = 1; out[2] = 0
    out.set(payload, 3)
    return [out]
  }
  const total = Math.ceil(payload.length / CHUNK_DATA)
  if (total > 255) return []
  const arr = []
  for (let i = 0; i < total; i++) {
    const seg = payload.subarray(i * CHUNK_DATA, (i + 1) * CHUNK_DATA)
    const out = new Uint8Array(3 + seg.length)
    out[0] = MAGIC; out[1] = total; out[2] = i
    out.set(seg, 3)
    arr.push(out)
  }
  return arr
}

function _feedRx(raw) {
  if (raw.length < 4 || raw[0] !== MAGIC) return null
  const total = raw[1]
  const idx = raw[2]
  const chunk = raw.subarray(3)
  if (_rxReady) {
    if (total < 1 || idx !== 0) return null
    _rxTotal = total
    _rxParts = new Array(total).fill(null)
    _rxSeen = 0
    _rxReady = false
  }
  if (total !== _rxTotal || idx >= total) {
    _rxReady = true
    return null
  }
  if (idx >= _rxParts.length || _rxParts[idx] !== null) {
    _rxReady = true
    return null
  }
  _rxParts[idx] = chunk
  _rxSeen++
  if (_rxSeen >= _rxTotal) {
    _rxReady = true
    const total2 = _rxTotal
    let totalLen = 0
    for (let i = 0; i < total2; i++) totalLen += _rxParts[i].length
    const full = new Uint8Array(totalLen)
    let off = 0
    for (let i = 0; i < total2; i++) {
      full.set(_rxParts[i], off)
      off += _rxParts[i].length
    }
    return full
  }
  return null
}

function _rxReset() {
  _rxTotal = 0
  _rxParts = []
  _rxSeen = 0
  _rxReady = true
}

// ===== 事件分发 =====

function _setState(s) {
  _state = s
  for (let i = 0; i < _stateChangeCallbacks.length; i++) {
    try { _stateChangeCallbacks[i](s) } catch (e) {}
  }
}

function _emitHello(h) {
  _helloInfo = h
  for (let i = 0; i < _helloCallbacks.length; i++) {
    try { _helloCallbacks[i](h) } catch (e) {}
  }
}

function _emitLayouts(l) {
  _layouts = l || _layouts
  try { uni.setStorageSync('phonekb.last_layouts', _layouts) } catch (e) {}
  for (let i = 0; i < _layoutsCallbacks.length; i++) {
    try { _layoutsCallbacks[i](_layouts) } catch (e) {}
  }
}

function _emitMessage(msg) {
  for (let i = 0; i < _messageCallbacks.length; i++) {
    try { _messageCallbacks[i](msg) } catch (e) {}
  }
}

function _handleInboundMessage(msg) {
  if (!msg || typeof msg !== 'object') return
  if (msg.action === 'hello') {
    _helloInfo = { server: msg.server, proto: msg.proto }
    if (msg.layouts) _emitLayouts(msg.layouts)
    try { uni.setStorageSync('phonekb.hello', _helloInfo) } catch (e) {}
    _emitHello(_helloInfo)
  } else if (msg.action === 'layouts') {
    _emitLayouts(msg.data)
  }
}

// 通用反射：plus.android.invoke 显式调 Java 方法，避开 5+ runtime 类型推断 bug
function _call(obj, method) {
  if (obj === null || obj === undefined) return null
  const args = Array.prototype.slice.call(arguments, 2)
  return plus.android.invoke.apply(null, [obj, method].concat(args))
}

function _error(msg) {
  console.error('[ble]', msg)
  if (_handlers.onError) _handlers.onError(msg)
}

// ===== 原生 BluetoothGattServer 设置 =====

function _setupGattServer() {
  const main = plus.android.runtimeMainActivity()
  const UUID = plus.android.importClass('java.util.UUID')
  const Toast = plus.android.importClass('android.widget.Toast')

  _bm = main.getSystemService(plus.android.importClass('android.content.Context').BLUETOOTH_SERVICE)
  if (!_bm) throw new Error('BluetoothManager 不可用')
  _adapter = _call(_bm, 'getAdapter')
  if (!_adapter) throw new Error('此设备无蓝牙适配器')
  if (!_call(_adapter, 'isEnabled')) {
    Toast.makeText(main, '请先在系统设置打开蓝牙', Toast.LENGTH_SHORT).show()
    throw new Error('请先在系统设置打开蓝牙')
  }

  // 1. GattServerCallback
  const callback = plus.android.implements('android.bluetooth.BluetoothGattServerCallback', {
    onConnectionStateChange: function(device, status, newState) {
      try {
        if (newState === 2) {
          _pcDevice = device
          _setState('connected')
          if (_handlers.onConnected) _handlers.onConnected()
        } else if (newState === 0) {
          _pcDevice = null
          if (_state === 'connected') {
            _setState('advertising')
            if (_handlers.onDisconnected) _handlers.onDisconnected()
          }
        }
      } catch (e) { console.error('[ble-cb] onConnectionStateChange ex', e) }
    },
    onServiceAdded: function(status, service) {
      try {
        if (status === 0) {
          console.log('[ble-cb] service added OK')
          _startAdvertising()
        } else {
          _error('添加 service 失败 code=' + status)
          _setState('idle')
        }
      } catch (e) { console.error('[ble-cb] onServiceAdded ex', e) }
    },
    onCharacteristicWriteRequest: function(device, requestId, characteristic, preparedWrite, responseNeeded, offset, value) {
      try {
        const bytes = _javaBytesToUint8(value)
        const full = _feedRx(bytes)
        if (responseNeeded) _call(_gattServer, 'sendResponse', device, requestId, 0, offset, value)
        if (full) {
          const str = _bytes2str(full)
          let msg = null
          try { msg = JSON.parse(str) } catch (e) { return }
          _handleInboundMessage(msg)
          _emitMessage(msg)
        }
      } catch (e) {
        console.error('[ble-cb] write req ex', e)
        if (responseNeeded) { try { _call(_gattServer, 'sendResponse', device, requestId, 1, offset, value) } catch (e2) {} }
      }
    },
    onDescriptorWriteRequest: function(device, requestId, descriptor, preparedWrite, responseNeeded, offset, value) {
      try { if (responseNeeded) _call(_gattServer, 'sendResponse', device, requestId, 0, offset, value) } catch (e) {}
    },
    onCharacteristicReadRequest: function(device, requestId, offset, characteristic) {
      try { _call(_gattServer, 'sendResponse', device, requestId, 0, offset, _call(characteristic, 'getValue')) } catch (e) {}
    },
    onDescriptorReadRequest: function(device, requestId, offset, descriptor) {
      try { _call(_gattServer, 'sendResponse', device, requestId, 0, offset, _call(descriptor, 'getValue')) } catch (e) {}
    },
    onNotificationSent: function() {},
    onExecuteWrite: function() {},
    onMtuChanged: function() {}
  })

  _gattServer = _call(_bm, 'openGattServer', main, callback)
  if (!_gattServer) throw new Error('openGattServer 返回 null')

  const svcUuid = _call(UUID, 'fromString', SERVICE_UUID)
  const notifyUuid = _call(UUID, 'fromString', NOTIFY_CHAR_UUID)
  const writeUuid = _call(UUID, 'fromString', WRITE_CHAR_UUID)
  const cccdUuid = _call(UUID, 'fromString', CCCD_UUID)

  _service = plus.android.new('android.bluetooth.BluetoothGattService', svcUuid, 0)
  // PROPERTY_NOTIFY=0x10, PERMISSION_READ=0x01
  _notifyChar = plus.android.new('android.bluetooth.BluetoothGattCharacteristic', notifyUuid, 16, 1)
  // CCCD PERMISSION_READ|PERMISSION_WRITE = 0x01|0x02 = 3
  const cccd = plus.android.new('android.bluetooth.BluetoothGattDescriptor', cccdUuid, 3)
  _call(cccd, 'setValue', [0x01, 0x00])
  _call(_notifyChar, 'addDescriptor', cccd)
  // PROPERTY_WRITE|PROPERTY_WRITE_NO_RESPONSE = 0x08|0x04 = 0x0C, PERMISSION_WRITE=0x08
  _writeChar = plus.android.new('android.bluetooth.BluetoothGattCharacteristic', writeUuid, 12, 8)

  _call(_service, 'addCharacteristic', _notifyChar)
  _call(_service, 'addCharacteristic', _writeChar)
  _call(_gattServer, 'addService', _service)
}
function _startAdvertising() {
  try {
    const AdvertiseSettings = plus.android.importClass('android.bluetooth.le.AdvertiseSettings')
    const ParcelUuid = plus.android.importClass('android.os.ParcelUuid')

    _advertiser = _call(_adapter, 'getBluetoothLeAdvertiser')
    if (!_advertiser) {
      _error('此设备不支持 BLE 广播')
      _setState('idle')
      return
    }

    const settingsBuilder = plus.android.new('android.bluetooth.le.AdvertiseSettings$Builder')
    _call(settingsBuilder, 'setAdvertiseMode', _call(AdvertiseSettings, 'ADVERTISE_MODE_LOW_LATENCY'))
    _call(settingsBuilder, 'setConnectable', true)
    _call(settingsBuilder, 'setTimeout', 0)
    _call(settingsBuilder, 'setTxPowerLevel', _call(AdvertiseSettings, 'ADVERTISE_TX_POWER_HIGH'))
    const settings = _call(settingsBuilder, 'build')

    const dataBuilder = plus.android.new('android.bluetooth.le.AdvertiseData$Builder')
    _call(dataBuilder, 'setIncludeDeviceName', true)
    _call(dataBuilder, 'setIncludeTxPowerLevel', false)
    _call(dataBuilder, 'addServiceUuid', _call(ParcelUuid, 'fromString', SERVICE_UUID))
    const data = _call(dataBuilder, 'build')

    const advCallback = plus.android.implements('android.bluetooth.le.AdvertiseCallback', {
      onStartSuccess: function() {
        console.log('[ble] advertising started OK')
        _setState('advertising')
      },
      onStartFailure: function(errorCode) {
        _error('广播失败 code=' + errorCode)
        _setState('idle')
      }
    })

    _call(_advertiser, 'startAdvertising', settings, data, advCallback)
  } catch (e) {
    console.error('[ble] advertise ex', e)
    _error('启动广播异常：' + (e.message || e))
    _setState('idle')
  }
}
function _shutdown() {
  try { _advertiser && _call(_advertiser, 'stopAdvertising', null) } catch (e) {}
  try { if (_pcDevice && _gattServer) _call(_gattServer, 'cancelConnection', _pcDevice) } catch (e) {}
  try { _gattServer && _call(_gattServer, 'clearServices') } catch (e) {}
  try { _gattServer && _call(_gattServer, 'close') } catch (e) {}
  _pcDevice = null
  _gattServer = null
  _advertiser = null
  _adapter = null
  _bm = null
  _service = null
  _notifyChar = null
  _writeChar = null
  _rxReset()
}
function _sendFrames(frames, idx) {
  if (idx >= frames.length) return
  if (!_pcDevice || !_notifyChar || !_gattServer) return
  const f = frames[idx]
  const arr = []
  for (let i = 0; i < f.length; i++) arr.push(f[i])
  try {
    _call(_notifyChar, 'setValue', arr)
    _call(_gattServer, 'notifyCharacteristicChanged', _pcDevice, _notifyChar, false)
  } catch (e) {
    console.error('[ble] notify ex', e)
    return
  }
  setTimeout(function() { _sendFrames(frames, idx + 1) }, 30)
}
function _ensurePermissions() {
  return new Promise(function(resolve) {
    if (typeof plus === "undefined" || !plus.android || !plus.android.requestPermissions) { resolve(true); return }
    try {
      plus.android.requestPermissions([
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_ADVERTISE"
      ], function() { resolve(true) }, function() { resolve(true) })
    } catch (e) {
      console.warn("[ble] perm request ex", e)
      resolve(true)
    }
  })
}

// ===== 公共 API =====

function connect(opts) {
  opts = opts || {}
  _handlers = {
    onConnected: opts.onConnected,
    onDisconnected: opts.onDisconnected,
    onError: opts.onError,
  }
  _setState("connecting")
  _ensurePermissions().then(function(ok) {
    if (!ok) {
      _setState("idle")
      if (_handlers.onError) _handlers.onError("蓝牙权限被拒绝")
      return
    }
    try {
      _setupGattServer()
    } catch (e) {
      _setState("idle")
      if (_handlers.onError) _handlers.onError(e.message || "蓝牙启动失败")
    }
  })
}

function send(obj) {
  if (_state !== 'connected' || !_pcDevice || !_gattServer) return false
  let payload
  try { payload = _str2bytes(JSON.stringify(obj)) } catch (e) { return false }
  const frames = _frameEncode(payload)
  if (frames.length === 0) return false
  _sendFrames(frames, 0)
  return true
}

function trigger() { return send({ action: 'trigger' }) }
function triggerSlot(id) { return send({ action: 'trigger_slot', id: id }) }

function close() {
  _shutdown()
  _setState('idle')
}

function isConnected() { return _state === 'connected' }

function reloadLayouts() { return send({ action: 'reload_layouts' }) }

function getLayouts() { return _layouts }
function getActiveLayoutId() { return (_layouts && _layouts.active_layout_id) || 'default' }
function getActivePageId() { return (_layouts && _layouts.active_page_id) || null }

function onStateChange(cb) { _stateChangeCallbacks.push(cb) }
function onMessage(cb) { _messageCallbacks.push(cb) }
function offMessage(cb) { _messageCallbacks = _messageCallbacks.filter(function(item) { return item !== cb }) }
function onHello(cb) { _helloCallbacks.push(cb) }
function onLayouts(cb) { if (typeof cb === 'function' && _layoutsCallbacks.indexOf(cb) < 0) _layoutsCallbacks.push(cb) }
function offLayouts(cb) { _layoutsCallbacks = _layoutsCallbacks.filter(function(item) { return item !== cb }) }
function onDevices() { /* Peripheral 模式不维护 devices */ }
function onTargetChanged() {}
function clearTargetChanged() {}

export default {
  SERVICE_UUID: SERVICE_UUID,
  NOTIFY_CHAR_UUID: NOTIFY_CHAR_UUID,
  WRITE_CHAR_UUID: WRITE_CHAR_UUID,
  connect: connect,
  connectDevice: function() { return Promise.resolve() },
  send: send,
  trigger: trigger,
  triggerSlot: triggerSlot,
  close: close,
  isConnected: isConnected,
  onStateChange: onStateChange,
  onMessage: onMessage,
  offMessage: offMessage,
  onHello: onHello,
  onLayouts: onLayouts,
  offLayouts: offLayouts,
  reloadLayouts: reloadLayouts,
  getLayouts: getLayouts,
  getActiveLayoutId: getActiveLayoutId,
  getActivePageId: getActivePageId,
  onDevices: onDevices,
  onTargetChanged: onTargetChanged,
  clearTargetChanged: clearTargetChanged,
}
