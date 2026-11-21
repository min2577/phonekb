// PhoneKB Classic Bluetooth RFCOMM client.
// Blocking Android calls run on Java threads; the JS/UI thread only receives events.

import { utf8Decode, SPP_MAGIC_INT, SPP_MAX_PAYLOAD } from './sppProtocol.js'
import { reconnectSettings } from './appSettings.js'
import {
  connect as nativeConnect,
  send as nativeSend,
  hidStart as nativeHidStart,
  hidMouseMove as nativeHidMouseMove,
  hidMouseButton as nativeHidMouseButton,
  hidMouseWheel as nativeHidMouseWheel,
  hidKeyboardKey as nativeHidKeyboardKey,
  hidKeyboardShortcut as nativeHidKeyboardShortcut,
  hidConsumerKey as nativeHidConsumerKey,
  hidClose as nativeHidClose,
  close as nativeClose,
} from '@/uni_modules/phonekb-spp'

const SPP_UUID = '00001101-0000-1000-8000-00805F9B34FB'
const CONNECT_TIMEOUT_MS = 12000
const HANDSHAKE_TIMEOUT_MS = 7000
const HEARTBEAT_INTERVAL_MS = 10000
const HEARTBEAT_TIMEOUT_MS = 35000

let _state = 'idle' // idle | listing | scanning | pairing | connecting | handshaking | connected | reconnecting
let _handlers = {}
let _socket = null
let _inputStream = null
let _outputStream = null
let _dataInput = null
let _readThread = null
let _writeExecutor = null
let _generation = 0

let _manualClose = false
let _lastDevice = null
let _reconnectTimer = null
let _reconnectAttempt = 0
let _heartbeatTimer = null
let _handshakeTimer = null
let _connectTimer = null
let _lastPong = 0
let _pendingConnect = null
let _lastError = ''
let _reconnectEligible = false
let _hidAvailable = null
let _hidState = 'idle' // idle | registering | connecting | connected | unavailable | error
let _hidAddress = ''
let _hidLastError = ''
let _hidButtonTimers = []
let _hidStateChangeCallbacks = []
let _hidReconnectTimer = null
let _hidReconnectAttempt = 0

let _layouts = { layouts: [], global_pages: [] }
let _helloInfo = null
let _stateChangeCallbacks = []
let _messageCallbacks = []
let _helloCallbacks = []
let _layoutsCallbacks = []

function _call(obj, method) {
  if (obj === null || obj === undefined) return null
  const args = Array.prototype.slice.call(arguments, 2)
  return plus.android.invoke.apply(null, [obj, method].concat(args))
}

function _postToUi(fn) {
  try {
    const activity = plus.android.runtimeMainActivity()
    const runnable = plus.android.implements('java.lang.Runnable', { run: fn })
    _call(activity, 'runOnUiThread', runnable)
  } catch (e) {
    setTimeout(fn, 0)
  }
}

function _startJavaThread(name, fn) {
  const runnable = plus.android.implements('java.lang.Runnable', { run: fn })
  let thread
  try {
    thread = plus.android.newObject('java.lang.Thread', runnable, name)
  } catch (primaryError) {
    try {
      thread = plus.android.newObject('java.lang.Thread', runnable)
      _call(thread, 'setName', name)
    } catch (fallbackError) {
      throw new Error('创建原生线程失败: ' + ((fallbackError && fallbackError.message) || fallbackError || primaryError))
    }
  }
  try { _call(thread, 'setName', name) } catch (e) {}
  _call(thread, 'start')
  return thread
}

function _newJavaByteArray(length) {
  const ReflectArray = plus.android.importClass('java.lang.reflect.Array')
  const Byte = plus.android.importClass('java.lang.Byte')
  return ReflectArray.newInstance(Byte.TYPE, length)
}

function _phoneLabel() {
  try {
    const Build = plus.android.importClass('android.os.Build')
    const manufacturer = String(Build.MANUFACTURER || '').trim()
    const model = String(Build.MODEL || '').trim()
    return (manufacturer + ' ' + model).trim() || 'Android'
  } catch (e) { return 'Android' }
}

function _javaBytesToUint8(value) {
  const output = new Uint8Array(value.length)
  for (let i = 0; i < value.length; i++) {
    let byte = value[i]
    if (byte < 0) byte += 256
    output[i] = byte
  }
  return output
}

function _setState(next) {
  if (_state === next) return
  _state = next
  for (let i = 0; i < _stateChangeCallbacks.length; i++) {
    try { _stateChangeCallbacks[i](next) } catch (e) {}
  }
}

function _getHidStatus() {
  return {
    state: _hidState,
    address: _hidAddress,
    error: _hidLastError,
    available: _hidAvailable,
    connected: _hidState === 'connected',
    mouseChannel: _hidState === 'connected' ? 'hid' : (_state === 'connected' ? 'spp' : 'none'),
    businessConnected: _state === 'connected',
  }
}

function _setHidState(next, message) {
  const previousState = _hidState
  const previousError = _hidLastError
  _hidState = next
  if (message !== undefined) _hidLastError = message || ''
  if (previousState === _hidState && previousError === _hidLastError) return
  const status = _getHidStatus()
  for (let i = 0; i < _hidStateChangeCallbacks.length; i++) {
    try { _hidStateChangeCallbacks[i](status) } catch (e) {}
  }
}

function _emitMessage(message) {
  for (let i = 0; i < _messageCallbacks.length; i++) {
    try { _messageCallbacks[i](message) } catch (e) {}
  }
}

function _emitLayouts(layouts) {
  _layouts = layouts || _layouts
  try { uni.setStorageSync('phonekb.last_layouts', _layouts) } catch (e) {}
  for (let i = 0; i < _layoutsCallbacks.length; i++) {
    try { _layoutsCallbacks[i](_layouts) } catch (e) {}
  }
}

function _emitHello(info) {
  _helloInfo = info || {}
  try { uni.setStorageSync('phonekb.hello', _helloInfo) } catch (e) {}
  for (let i = 0; i < _helloCallbacks.length; i++) {
    try { _helloCallbacks[i](_helloInfo) } catch (e) {}
  }
}

function _handleInboundMessage(message) {
  if (!message || typeof message !== 'object') return
  if (message.action === 'pong') {
    _lastPong = Date.now()
    if (_state === 'handshaking') _finishHandshake()
  } else if (message.action === 'layouts') {
    _emitLayouts(message.data)
  } else if (message.action === 'hello') {
    if (message.layouts) _emitLayouts(message.layouts)
    _emitHello(message.hello || { server: message.server, proto: message.proto })
  } else if (message.action === 'trigger_ack' && !message.ok && message.msg) {
    try { uni.showToast({ title: message.msg, icon: 'none' }) } catch (e) {}
  }
  _emitMessage(message)
}

function _mergeHandlers(opts) {
  opts = opts || {}
  _handlers = {
    onConnected: opts.onConnected || _handlers.onConnected,
    onDisconnected: opts.onDisconnected || _handlers.onDisconnected,
    onError: opts.onError || _handlers.onError,
    onDeviceNeeded: opts.onDeviceNeeded || _handlers.onDeviceNeeded,
  }
}

function _clearTimer(name) {
  if (name === 'connect' && _connectTimer) { clearTimeout(_connectTimer); _connectTimer = null }
  if (name === 'handshake' && _handshakeTimer) { clearTimeout(_handshakeTimer); _handshakeTimer = null }
  if (name === 'reconnect' && _reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
}

function _stopHeartbeat() {
  if (_heartbeatTimer) { clearInterval(_heartbeatTimer); _heartbeatTimer = null }
}

function _closeResources() {
  _generation++
  _clearTimer('connect')
  _clearTimer('handshake')
  _stopHeartbeat()
  try { nativeClose() } catch (e) {}
  try { _socket && _call(_socket, 'close') } catch (e) {}
  try { _dataInput && _call(_dataInput, 'close') } catch (e) {}
  try { _writeExecutor && _call(_writeExecutor, 'shutdownNow') } catch (e) {}
  _socket = null
  _inputStream = null
  _outputStream = null
  _dataInput = null
  _readThread = null
  _writeExecutor = null
}

function _rejectPending(error) {
  if (!_pendingConnect) return
  const pending = _pendingConnect
  _pendingConnect = null
  try { pending.reject(error instanceof Error ? error : new Error(String(error))) } catch (e) {}
}

function _resolvePending(value) {
  if (!_pendingConnect) return
  const pending = _pendingConnect
  _pendingConnect = null
  try { pending.resolve(value) } catch (e) {}
}

function _transportFailed(message) {
  if (_state === 'idle' || _state === 'reconnecting') return
  _lastError = message || '蓝牙连接已断开'
  const wasConnected = _state === 'connected'
  console.error('[bt] transport failed: ' + _lastError)
  _closeResources()
  _rejectPending(new Error(message || '蓝牙连接已断开'))
  if (wasConnected && _handlers.onDisconnected) {
    try { _handlers.onDisconnected() } catch (e) {}
  } else if (!wasConnected && _handlers.onError) {
    try { _handlers.onError(message || '蓝牙连接失败') } catch (e) {}
  }
  _scheduleReconnect()
}

function _scheduleReconnect() {
  const settings = reconnectSettings()
  if (_manualClose || !_lastDevice || !_reconnectEligible || _reconnectTimer) {
    if (_manualClose) _setState('idle')
    return
  }
  if (!settings.enabled || _reconnectAttempt >= settings.maxAttempts) {
    _setState('idle')
    return
  }
  _setState('reconnecting')
  const delays = [1000, 2000, 5000, 10000, 15000]
  const delay = delays[Math.min(_reconnectAttempt, delays.length - 1)]
  _reconnectAttempt++
  console.log('[bt] reconnect in ' + delay + 'ms, attempt=' + _reconnectAttempt)
  _reconnectTimer = setTimeout(function() {
    _reconnectTimer = null
    if (_manualClose || !_lastDevice) return
    connectDevice(_lastDevice, Object.assign({}, _handlers, { autoReconnect: true, reconnectAttempt: true })).catch(function() {})
  }, delay)
}

function _startHeartbeat() {
  _stopHeartbeat()
  const settings = reconnectSettings()
  const timeout = Math.max(15000, settings.heartbeatMs * 2 + 5000)
  _lastPong = Date.now()
  _heartbeatTimer = setInterval(function() {
    if (_state !== 'connected') return
    if (Date.now() - _lastPong > timeout) {
      _transportFailed('蓝牙心跳超时')
      return
    }
    _sendRaw({ action: 'ping' })
  }, settings.heartbeatMs)
}

function _finishHandshake() {
  if (_state !== 'handshaking') return
  _clearTimer('handshake')
  _reconnectAttempt = 0
  _reconnectEligible = true
  _lastError = ''
  _setState('connected')
  try {
    if (_lastDevice && _lastDevice.address) uni.setStorageSync('phonekb.last_bt_addr', _lastDevice.address)
  } catch (e) {}
  _resolvePending(true)
  _startHeartbeat()
  if (_handlers.onConnected) {
    try { _handlers.onConnected() } catch (e) {}
  }
  setTimeout(function() { send({ action: 'reload_layouts' }) }, 100)
}

function _clearHidButtonTimers() {
  for (let i = 0; i < _hidButtonTimers.length; i++) clearTimeout(_hidButtonTimers[i])
  _hidButtonTimers = []
}

function _clearHidReconnect(resetAttempt) {
  if (_hidReconnectTimer) clearTimeout(_hidReconnectTimer)
  _hidReconnectTimer = null
  if (resetAttempt) _hidReconnectAttempt = 0
}

function _scheduleHidReconnect() {
  if (_manualClose || _hidAvailable === false || !_hidAddress || _hidReconnectTimer) return
  const address = _hidAddress
  const delays = [1000, 3000, 5000, 10000]
  const delay = delays[Math.min(_hidReconnectAttempt, delays.length - 1)]
  _hidReconnectAttempt++
  _hidReconnectTimer = setTimeout(function() {
    _hidReconnectTimer = null
    if (_manualClose || address !== _hidAddress) return
    _startHidInput(address)
  }, delay)
}

function _stopHidInput() {
  _clearHidButtonTimers()
  _clearHidReconnect(true)
  if (_hidAvailable !== false) {
    try { nativeHidClose() } catch (e) {}
  }
  _hidAddress = ''
  _setHidState('idle', '')
}

function _startHidInput(address) {
  address = String(address || '')
  if (!address || _hidAvailable === false) return
  if (_hidAddress === address && (_hidState === 'registering' || _hidState === 'connecting' || _hidState === 'connected')) return
  if (_sdkInt() < 28) {
    _hidAvailable = false
    _setHidState('unavailable', 'Android 版本低于 9，不支持 Bluetooth HID Device')
    return
  }
  _hidAddress = address
  _setHidState('registering', '')
  try {
    nativeHidStart({
      address: address,
      callback: function(event) {
        if (!event) return
        if (event.type === 'hid_connected') {
          _hidAvailable = true
          _clearHidReconnect(true)
          _setHidState('connected', '')
          try { if (_hidAddress) uni.setStorageSync('phonekb.last_bt_addr', _hidAddress) } catch (e) {}
          console.log('[bt-hid] Windows 已连接为标准鼠标和键盘输入设备')
        } else if (event.type === 'hid_registered' || event.type === 'hid_connecting') {
          _setHidState(event.type === 'hid_registered' ? 'registering' : 'connecting', '')
        } else if (event.type === 'hid_unsupported') {
          _hidAvailable = false
          _setHidState('unavailable', event.message || '手机不支持 HID Device Profile')
          console.warn('[bt-hid] ' + _hidLastError)
        } else if (event.type === 'hid_error' || event.type === 'hid_disconnected') {
          const message = event.message || 'HID 输入通道已断开'
          _setHidState(event.type === 'hid_error' ? 'error' : 'idle', message)
          console.warn('[bt-hid] ' + _hidLastError + '，鼠标继续使用 SPP 背压通道')
          if (/拒绝注册 HID 输入设备|HID 输入设备注册失败|注册 HID 输入设备失败/.test(message)) {
            _clearHidReconnect(true)
            return
          }
          _scheduleHidReconnect()
        }
      }
    })
  } catch (error) {
    const message = String((error && error.message) || error || '')
    if (/method not found/i.test(message) && /hidStart/i.test(message)) {
      _hidAvailable = false
      _setHidState('unavailable', '当前原生基座不含 Bluetooth HID 模块')
      console.warn('[bt-hid] ' + _hidLastError + '，鼠标继续使用 SPP 背压通道')
      return
    }
    _setHidState('error', message)
    console.warn('[bt-hid] 启动失败: ' + message)
    _scheduleHidReconnect()
  }
}

function _markHidSendFailed(message) {
  _clearHidButtonTimers()
  try { nativeHidClose() } catch (e) {}
  _setHidState('error', message)
  console.warn('[bt-hid] ' + message + '，当前消息回退 SPP')
  _scheduleHidReconnect()
}

function _scheduleHidButton(button, down, delay) {
  const timer = setTimeout(function() {
    _hidButtonTimers = _hidButtonTimers.filter(function(item) { return item !== timer })
    if (_hidState !== 'connected') return
    try {
      if (nativeHidMouseButton(button, down) !== true) _markHidSendFailed('HID按键报告被系统拒绝')
    } catch (error) {
      _markHidSendFailed('HID按键发送失败: ' + String((error && error.message) || error || ''))
    }
  }, delay)
  _hidButtonTimers.push(timer)
}

function _scheduleHidKeyboardRelease(modifiers, key, delay) {
  const timer = setTimeout(function() {
    _hidButtonTimers = _hidButtonTimers.filter(function(item) { return item !== timer })
    if (_hidState !== 'connected') return
    try {
      const ok = modifiers.length
        ? nativeHidKeyboardShortcut(modifiers, key, false)
        : nativeHidKeyboardKey(key, false)
      if (ok !== true) _markHidSendFailed('HID键盘抬起报告被系统拒绝')
    } catch (error) {
      _markHidSendFailed('HID键盘抬起失败: ' + String((error && error.message) || error || ''))
    }
  }, delay)
  _hidButtonTimers.push(timer)
}

function _isHidKeyboardObject(object) {
  if (!object) return false
  if (object.action === 'simulate_key' || object.action === 'keyboard_key' || object.action === 'keyboard_shortcut' || object.action === 'consumer_key') return true
  return !!(object.action === 'hold_slot' && object.slot && object.slot.key && object.slot.key.type === 'shortcut' && object.slot.key.shortcut)
}

function _trySendHidKeyboard(object) {
  if (!_isHidKeyboardObject(object) || _hidState !== 'connected') return false
  try {
    if (object.action === 'consumer_key') {
      if (nativeHidConsumerKey(String(object.key || ''), object.down === true) === true) return true
    } else if (object.action === 'keyboard_key') {
      if (nativeHidKeyboardKey(String(object.key || ''), object.down === true) === true) return true
    } else {
      const shortcut = object.action === 'hold_slot' ? object.slot.key.shortcut : object
      const key = String(shortcut.key || '')
      const modifiers = Array.isArray(shortcut.modifiers)
        ? shortcut.modifiers.map(function(item) { return String(item || '') })
        : []
      const down = object.action === 'simulate_key' ? true : object.down === true
      const ok = modifiers.length
        ? nativeHidKeyboardShortcut(modifiers, key, down)
        : nativeHidKeyboardKey(key, down)
      if (ok === true) {
        if (object.action === 'simulate_key') _scheduleHidKeyboardRelease(modifiers, key, 24)
        return true
      }
    }
    _markHidSendFailed('HID键盘报告被系统拒绝或键位不受支持')
  } catch (error) {
    _markHidSendFailed('HID键盘发送失败: ' + String((error && error.message) || error || ''))
  }
  return false
}

function _sendKeyboardSppFallback(object) {
  if (_state !== 'connected') return false
  if (object.action === 'hold_slot' || object.action === 'simulate_key') return _sendRaw(object)
  if (object.down !== true) return true
  if (object.action === 'keyboard_key') {
    return _sendRaw({ action: 'simulate_key', modifiers: [], key: String(object.key || '') })
  }
  if (object.action === 'keyboard_shortcut') {
    if (object.name) return _sendRaw({ action: 'shortcut', name: String(object.name) })
    return _sendRaw({
      action: 'simulate_key',
      modifiers: Array.isArray(object.modifiers) ? object.modifiers : [],
      key: String(object.key || '')
    })
  }
  if (object.action === 'consumer_key') {
    return _sendRaw({ action: 'shortcut', name: String(object.name || object.key || '') })
  }
  return false
}

function _trySendHidMouse(object) {
  if (!object || (object.action !== 'mouse' && object.action !== 'hold_mouse')) return false
  if (_hidState !== 'connected') return false
  const op = object.action === 'hold_mouse' ? (object.down === true ? 'down' : 'up') : String(object.op || '')
  try {
    if (op === 'move') {
      if (nativeHidMouseMove(Number(object.dx) || 0, Number(object.dy) || 0) === true) return true
      _markHidSendFailed('HID移动报告被系统拒绝')
      return false
    }
    if (op === 'down' || op === 'up') {
      if (nativeHidMouseButton(String(object.button || 'left'), op === 'down') === true) return true
      _markHidSendFailed('HID按键报告被系统拒绝')
      return false
    }
    if (op === 'click') {
      const button = String(object.button || 'left')
      const count = Math.max(1, Math.min(2, Number(object.count) || 1))
      if (nativeHidMouseButton(button, true) !== true) {
        _markHidSendFailed('HID点击报告被系统拒绝')
        return false
      }
      _scheduleHidButton(button, false, 16)
      if (count > 1) {
        _scheduleHidButton(button, true, 72)
        _scheduleHidButton(button, false, 88)
      }
      return true
    }
    if (op === 'wheel') {
      const raw = Number(object.delta) || 0
      const notch = raw === 0 ? 0 : (raw > 0 ? 1 : -1)
      if (nativeHidMouseWheel(notch) === true) return true
      _markHidSendFailed('HID滚轮报告被系统拒绝')
      return false
    }
    if (op === 'hwheel' || op === 'zoom') {
      const raw = Number(object.delta) || 0
      const notch = raw === 0 ? 0 : (raw > 0 ? 1 : -1)
      const modifier = op === 'zoom' ? 'ctrl' : 'shift'
      if (nativeHidKeyboardKey(modifier, true) !== true) {
        _markHidSendFailed('HID手势修饰键被系统拒绝')
        return false
      }
      const wheelOk = nativeHidMouseWheel(notch) === true
      const releaseOk = nativeHidKeyboardKey(modifier, false) === true
      if (wheelOk && releaseOk) return true
      _markHidSendFailed('HID手势报告被系统拒绝')
      return false
    }
  } catch (error) {
    _markHidSendFailed('HID发送失败: ' + String((error && error.message) || error || ''))
  }
  return false
}

function _startReader(generation) {
  _readThread = _startJavaThread('phonekb-spp-reader', function() {
    try {
      while (generation === _generation && _dataInput) {
        const rawMagic = _dataInput.readInt()
        const magic = parseInt(rawMagic, 10)
        if (magic !== SPP_MAGIC_INT) throw new Error('电脑端协议版本不匹配（magic=' + String(rawMagic) + '）')
        const length = parseInt(_dataInput.readInt(), 10)
        if (length <= 0 || length > SPP_MAX_PAYLOAD) throw new Error('收到非法蓝牙消息长度: ' + length)
        const byteArray = _newJavaByteArray(length)
        _dataInput.readFully(byteArray)
        const bytes = _javaBytesToUint8(byteArray)
        const text = utf8Decode(bytes)
        _postToUi(function() {
          if (generation !== _generation) return
          try { _handleInboundMessage(JSON.parse(text)) }
          catch (e) { console.warn('[bt] JSON parse failed', e) }
        })
      }
    } catch (error) {
      const message = (error && error.message) || String(error)
      _postToUi(function() {
        if (generation === _generation && !_manualClose) _transportFailed(message)
      })
    }
  })
}

function _sendRaw(object) {
  let payload
  try { payload = JSON.stringify(object) }
  catch (error) {
    console.error('[bt] encode failed', error)
    return false
  }
  try {
    return nativeSend(payload) === true
  } catch (error) {
    _transportFailed('蓝牙写入失败: ' + ((error && error.message) || error))
    return false
  }
}

function _beginSocketConnection(deviceInfo) {
  return new Promise(function(resolve, reject) {
    _pendingConnect = { resolve: resolve, reject: reject }
    const generation = ++_generation
    const address = String((deviceInfo && deviceInfo.address) || '')
    if (!address) { _pendingConnect = null; reject(new Error('未指定电脑设备')); return }

    _connectTimer = setTimeout(function() {
      if (generation !== _generation) return
      try { nativeClose() } catch (e) {}
      _transportFailed('连接超时，请确认 Windows 入站蓝牙串口已启用')
    }, CONNECT_TIMEOUT_MS)

    try {
      nativeConnect({
        address: address,
        callback: function(event) {
          if (generation !== _generation || !event) return
          if (event.type === 'connected') {
          _clearTimer('connect')
            _setState('handshaking')
            if (!_sendRaw({ action: 'ping', protocol: 2, device: _phoneLabel() })) {
              _transportFailed('初始化蓝牙数据通道失败: 无法发送握手消息')
              return
            }
            _handshakeTimer = setTimeout(function() {
              if (generation === _generation && _state === 'handshaking') _transportFailed('电脑端握手超时，请确认 PhoneKB 正在运行并监听入站串口')
            }, HANDSHAKE_TIMEOUT_MS)
          } else if (event.type === 'message') {
            try { _handleInboundMessage(JSON.parse(event.payload || '')) }
            catch (error) { _transportFailed('蓝牙消息解析失败: ' + ((error && error.message) || error)) }
          } else if (event.type === 'error' || event.type === 'disconnected') {
            _transportFailed(event.message || '蓝牙连接已断开')
          }
        }
      })
    } catch (error) {
      _clearTimer('connect')
      _transportFailed('启动原生蓝牙连接失败: ' + ((error && error.message) || error))
    }
  })
}

function connectDevice(device, opts) {
  opts = opts || {}
  _mergeHandlers(opts)
  _manualClose = false
  _clearTimer('reconnect')
  if (!opts.reconnectAttempt) _reconnectAttempt = 0
  if (!opts.reconnectAttempt) _reconnectEligible = opts.autoReconnect !== false
  _rejectPending(new Error('连接已被新的请求替换'))
  const nextAddress = String((device && device.address) || '')
  if (_hidAddress && _hidAddress !== nextAddress) _stopHidInput()
  _closeResources()
  _lastDevice = {
    name: String((device && device.name) || 'Windows PC'),
    address: String((device && device.address) || ''),
    device: device && device.device,
    icon: (device && device.icon) || 'PC',
  }
  _setState('connecting')
  return _ensurePermissions(false).then(function() {
    // HID input does not depend on the desktop SPP service. Start it as soon
    // as the user selects a paired computer so basic mouse input can stand alone.
    _startHidInput(nextAddress)
    return _beginSocketConnection(_lastDevice)
  }).catch(function(error) {
    const message = (error && error.message) || String(error)
    _lastError = message
    console.error('[bt] connect request failed: ' + message)
    if (_state !== 'reconnecting') {
      _closeResources()
      _rejectPending(error)
      if (_handlers.onError) { try { _handlers.onError(message) } catch (e) {} }
      if (opts.reconnectAttempt && /蓝牙未打开/.test(message)) _scheduleReconnect()
      else if (/权限|蓝牙未打开|无蓝牙适配器|未指定电脑/.test(message)) _setState('idle')
      else _scheduleReconnect()
    }
    throw error
  })
}

function connect(opts) {
  opts = opts || {}
  _mergeHandlers(opts)
  _manualClose = false
  _setState('listing')
  return listBondedDevices().then(function(devices) {
    if (!devices.length) throw new Error('没有已配对设备，请先在蓝牙设置中与电脑配对')
    let lastAddress = ''
    try { lastAddress = uni.getStorageSync('phonekb.last_bt_addr') || '' } catch (e) {}
    let selected = devices.find(function(item) { return item.address === lastAddress })
    if (!selected && devices.length === 1) selected = devices[0]
    if (selected) return connectDevice(selected, opts)
    _setState('listing')
    if (_handlers.onDeviceNeeded) { _handlers.onDeviceNeeded(devices); return false }
    throw new Error('已配对多个设备，请选择要连接的电脑')
  }).catch(function(error) {
    if (_state === 'listing') _setState('idle')
    if (_handlers.onError) { try { _handlers.onError(error.message || String(error)) } catch (e) {} }
    throw error
  })
}

function restoreConnection(opts) {
  let address = ''
  try { address = uni.getStorageSync('phonekb.last_bt_addr') || '' } catch (e) {}
  if (!address) return Promise.reject(new Error('没有上次连接的蓝牙设备'))
  return connectDevice(
    { name: 'Windows PC', address: address },
    Object.assign({}, opts || {}, { autoReconnect: true })
  )
}

function send(object) {
  if (object && (object.action === 'mouse' || object.action === 'hold_mouse')) {
    if (_trySendHidMouse(object)) return true
    if (_state === 'connected') return _sendRaw(object)
    return false
  }
  if (_isHidKeyboardObject(object)) {
    if (_trySendHidKeyboard(object)) return true
    return _sendKeyboardSppFallback(object)
  }
  if (_state !== 'connected') return false
  return _sendRaw(object)
}

function canSendMouse() { return _hidState === 'connected' || _state === 'connected' }
function canSendKeyboard() { return _hidState === 'connected' || _state === 'connected' }

function close() {
  _manualClose = true
  _reconnectEligible = false
  _clearTimer('reconnect')
  _stopHidInput()
  const wasConnected = _state === 'connected'
  _closeResources()
  _rejectPending(new Error('连接已取消'))
  _setState('idle')
  if (wasConnected && _handlers.onDisconnected) {
    try { _handlers.onDisconnected() } catch (e) {}
  }
}

function _sdkInt() {
  try {
    const BuildVersion = plus.android.importClass('android.os.Build$VERSION')
    return parseInt(BuildVersion.SDK_INT, 10) || 0
  } catch (e) { return 0 }
}

function _ensurePermissions(needsDiscovery) {
  return new Promise(function(resolve, reject) {
    if (typeof plus === 'undefined' || !plus.android || !plus.android.requestPermissions) { resolve(true); return }
    const sdk = _sdkInt()
    if (sdk < 23) { resolve(true); return }
    const permissions = sdk >= 31
      ? ['android.permission.BLUETOOTH_CONNECT'].concat(needsDiscovery ? ['android.permission.BLUETOOTH_SCAN'] : [])
      : (needsDiscovery ? ['android.permission.ACCESS_FINE_LOCATION'] : [])
    if (!permissions.length) { resolve(true); return }
    try {
      plus.android.requestPermissions(permissions, function(result) {
        const denied = []
        try {
          const present = result.deniedPresent || []
          const always = result.deniedAlways || []
          for (let i = 0; i < present.length; i++) denied.push(present[i])
          for (let i = 0; i < always.length; i++) denied.push(always[i])
        } catch (e) {}
        if (denied.length) reject(new Error('蓝牙权限被拒绝，请到系统设置允许“附近的设备”' + (sdk < 31 ? '和定位权限' : '')))
        else resolve(true)
      }, function(error) {
        reject(new Error('请求蓝牙权限失败: ' + ((error && error.message) || JSON.stringify(error || {}))))
      })
    } catch (error) {
      reject(new Error('请求蓝牙权限异常: ' + ((error && error.message) || error)))
    }
  })
}

function _getAdapter() {
  try {
    const activity = plus.android.runtimeMainActivity()
    const Context = plus.android.importClass('android.content.Context')
    const manager = _call(activity, 'getSystemService', Context.BLUETOOTH_SERVICE)
    const adapter = manager && _call(manager, 'getAdapter')
    if (adapter) return adapter
  } catch (e) {}
  try {
    const BluetoothAdapter = plus.android.importClass('android.bluetooth.BluetoothAdapter')
    return _call(BluetoothAdapter, 'getDefaultAdapter')
  } catch (e) { return null }
}

function _isEnabled(adapter) {
  try { return !!(adapter && _call(adapter, 'isEnabled')) } catch (e) { return false }
}

function getBtInfo() {
  return _ensurePermissions(false).then(function() {
    const adapter = _getAdapter()
    if (!adapter) return { ok: false, msg: '此设备无蓝牙适配器' }
    let name = ''
    try { name = String(_call(adapter, 'getName') || '') } catch (e) {}
    return { ok: true, enabled: _isEnabled(adapter), name: name, address: '', state: _call(adapter, 'getState'), sdk: _sdkInt() }
  })
}

function setBtEnabled(enabled) {
  return _ensurePermissions(false).then(function() {
    const adapter = _getAdapter()
    if (!adapter) return { ok: false, msg: '此设备无蓝牙适配器' }
    if (_isEnabled(adapter) === !!enabled) return { ok: true, enabled: !!enabled, msg: '状态未变' }
    const activity = plus.android.runtimeMainActivity()
    const Settings = plus.android.importClass('android.provider.Settings')
    const BluetoothAdapter = plus.android.importClass('android.bluetooth.BluetoothAdapter')
    const action = enabled ? BluetoothAdapter.ACTION_REQUEST_ENABLE : Settings.ACTION_BLUETOOTH_SETTINGS
    const intent = plus.android.newObject('android.content.Intent', action)
    _call(activity, 'startActivity', intent)
    return { ok: true, pending: true, enabled: _isEnabled(adapter), msg: '请在系统界面确认蓝牙状态' }
  })
}

function _classToIcon(majorClass) {
  if (majorClass === 0x100) return '💻'
  if (majorClass === 0x200) return '📞'
  if (majorClass === 0x400) return '🔊'
  if (majorClass === 0x500) return '⌨️'
  return '📱'
}

function _deviceInfo(device, rssi) {
  let majorClass = -1
  try {
    const btClass = _call(device, 'getBluetoothClass')
    if (btClass) majorClass = parseInt(_call(btClass, 'getMajorDeviceClass'), 10)
  } catch (e) {}
  let bondState = -1
  try { bondState = parseInt(_call(device, 'getBondState'), 10) } catch (e) {}
  const address = String(_call(device, 'getAddress') || '')
  return {
    name: String(_call(device, 'getName') || '未命名设备'),
    address: address,
    device: device,
    rssi: typeof rssi === 'number' ? rssi : -999,
    distance: null,
    icon: _classToIcon(majorClass),
    majorClass: majorClass,
    bondState: bondState,
    isConnected: _state === 'connected' && !!_lastDevice && _lastDevice.address === address,
  }
}

function _listBonded(adapter) {
  const result = []
  const set = _call(adapter, 'getBondedDevices')
  const iterator = set && _call(set, 'iterator')
  while (iterator && _call(iterator, 'hasNext')) {
    const device = _call(iterator, 'next')
    if (device) result.push(_deviceInfo(device))
  }
  return result
}

function listBondedDevices() {
  return _ensurePermissions(false).then(function() {
    const adapter = _getAdapter()
    if (!adapter) return []
    return _listBonded(adapter)
  })
}

function startDiscovery() {
  return _ensurePermissions(true).then(function() {
    return new Promise(function(resolve) {
      const adapter = _getAdapter()
      if (!adapter) { resolve({ ok: false, msg: '此设备无蓝牙适配器', devices: [] }); return }
      if (!_isEnabled(adapter)) { resolve({ ok: false, msg: '请先打开蓝牙', devices: [] }); return }
      const BluetoothDevice = plus.android.importClass('android.bluetooth.BluetoothDevice')
      const BluetoothAdapter = plus.android.importClass('android.bluetooth.BluetoothAdapter')
      const IntentFilter = plus.android.importClass('android.content.IntentFilter')
      const Context = plus.android.importClass('android.content.Context')
      const activity = plus.android.runtimeMainActivity()
      const actionFound = BluetoothDevice.ACTION_FOUND
      const actionFinished = BluetoothAdapter.ACTION_DISCOVERY_FINISHED
      const found = []
      const seen = {}
      let done = false
      let timeout = null
      const finish = function(result) {
        if (done) return
        done = true
        if (timeout) clearTimeout(timeout)
        try { _call(adapter, 'cancelDiscovery') } catch (e) {}
        try { _call(activity, 'unregisterReceiver', receiver) } catch (e) {}
        _setState('idle')
        resolve(result || { ok: true, msg: '扫描完成', devices: found })
      }
      const receiver = plus.android.implements('android.content.BroadcastReceiver', {
        onReceive: function(context, intent) {
          try {
            const action = String(_call(intent, 'getAction') || '')
            if (action === actionFinished) { finish(); return }
            if (action !== actionFound) return
            const device = _call(intent, 'getParcelableExtra', BluetoothDevice.EXTRA_DEVICE)
            if (!device) return
            const address = String(_call(device, 'getAddress') || '')
            if (!address || seen[address]) return
            seen[address] = true
            let rssi = -999
            try { rssi = parseInt(_call(intent, 'getShortExtra', BluetoothDevice.EXTRA_RSSI, -999), 10) } catch (e) {}
            found.push(_deviceInfo(device, rssi))
          } catch (e) { console.warn('[bt] discovery callback failed', e) }
        }
      })
      const filter = new IntentFilter()
      _call(filter, 'addAction', actionFound)
      _call(filter, 'addAction', actionFinished)
      try {
        if (_sdkInt() >= 33) _call(activity, 'registerReceiver', receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        else _call(activity, 'registerReceiver', receiver, filter)
        _setState('scanning')
        if (!_call(adapter, 'startDiscovery')) { finish({ ok: false, msg: '系统未能启动蓝牙扫描', devices: [] }); return }
        timeout = setTimeout(function() { finish() }, 12000)
      } catch (error) {
        finish({ ok: false, msg: '启动蓝牙扫描失败: ' + (error.message || error), devices: [] })
      }
    })
  })
}

function pairDevice(deviceInfo) {
  return _ensurePermissions(false).then(function() {
    return new Promise(function(resolve, reject) {
      if (!deviceInfo || !deviceInfo.device) { reject(new Error('设备无效')); return }
      const device = deviceInfo.device
      _setState('pairing')
      let started = false
      try { started = !!_call(device, 'createBond') } catch (error) { reject(new Error('发起配对失败: ' + (error.message || error))); return }
      if (!started) { reject(new Error('系统拒绝发起配对')); return }
      let waited = 0
      const timer = setInterval(function() {
        waited += 500
        try {
          const state = parseInt(_call(device, 'getBondState'), 10)
          if (state === 12) { clearInterval(timer); _setState('idle'); resolve(true) }
          else if (state === 10 && waited > 1000) { clearInterval(timer); _setState('idle'); reject(new Error('配对被取消或失败')) }
          else if (waited >= 30000) { clearInterval(timer); _setState('idle'); reject(new Error('配对超时')) }
        } catch (error) { clearInterval(timer); _setState('idle'); reject(error) }
      }, 500)
    })
  })
}

function diagnose() {
  return _ensurePermissions(false).then(function() {
    const businessChannel = _state === 'connected' ? 'RFCOMM/SPP v2（已连接）' : 'RFCOMM/SPP v2（未连接）'
    const mouseChannel = _hidState === 'connected'
      ? 'Bluetooth HID（标准鼠标）'
      : (_state === 'connected' ? 'SPP ACK 背压回退' : '不可用')
    const lines = ['=== 蓝牙诊断 ===', '手机: ' + _phoneLabel(), 'Android API: ' + _sdkInt(), '业务通道: ' + businessChannel, '鼠标通道: ' + mouseChannel, 'HID 状态: ' + _hidState]
    if (_hidLastError) lines.push('HID 说明: ' + _hidLastError)
    lines.push('HID 重连次数: ' + _hidReconnectAttempt)
    const adapter = _getAdapter()
    lines.push('蓝牙适配器: ' + (adapter ? '可用' : '不可用'))
    if (adapter) {
      lines.push('蓝牙开关: ' + (_isEnabled(adapter) ? '已打开' : '未打开'))
      try { lines.push('本机名称: ' + String(_call(adapter, 'getName') || '')) } catch (e) {}
      try { lines.push('已配对设备数: ' + _listBonded(adapter).length) } catch (e) { lines.push('读取配对设备失败: ' + (e.message || e)) }
    }
    lines.push('连接状态: ' + _state)
    lines.push('上次电脑: ' + ((_lastDevice && (_lastDevice.name + ' ' + _lastDevice.address)) || '无'))
    lines.push('重连次数: ' + _reconnectAttempt)
    lines.push('最后错误: ' + (_lastError || '无'))
    return { ok: true, lines: lines }
  })
}

function init() {}
function trigger(name) { return name ? send({ action: 'shortcut', name: name }) : send({ action: 'trigger' }) }
function triggerSlot(idOrSlot) {
  const payload = { action: 'trigger_slot' }
  if (idOrSlot && typeof idOrSlot === 'object' && idOrSlot.key) {
    payload.slot = idOrSlot
    payload.id = idOrSlot.key.id ? String(idOrSlot.key.id) : ''
  } else payload.id = String(idOrSlot || '')
  return send(payload)
}
function isConnected() { return _state === 'connected' }
function getHidStatus() { return _getHidStatus() }
function onHidStateChange(cb) { if (typeof cb === 'function' && _hidStateChangeCallbacks.indexOf(cb) < 0) _hidStateChangeCallbacks.push(cb) }
function offHidStateChange(cb) { _hidStateChangeCallbacks = _hidStateChangeCallbacks.filter(function(item) { return item !== cb }) }
function reloadLayouts() { return send({ action: 'reload_layouts' }) }
function getHello() { return _helloInfo }
function getLayouts() { return _layouts }
function getActiveLayoutId() { return (_layouts && _layouts.active_layout_id) || 'default' }
function getActivePageId() { return (_layouts && _layouts.active_page_id) || null }
function onStateChange(cb) { if (typeof cb === 'function' && _stateChangeCallbacks.indexOf(cb) < 0) _stateChangeCallbacks.push(cb) }
function offStateChange(cb) { _stateChangeCallbacks = _stateChangeCallbacks.filter(function(item) { return item !== cb }) }
function onMessage(cb) { if (typeof cb === 'function' && _messageCallbacks.indexOf(cb) < 0) _messageCallbacks.push(cb) }
function offMessage(cb) { _messageCallbacks = _messageCallbacks.filter(function(item) { return item !== cb }) }
function onHello(cb) { if (typeof cb === 'function' && _helloCallbacks.indexOf(cb) < 0) _helloCallbacks.push(cb) }
function onLayouts(cb) { if (typeof cb === 'function' && _layoutsCallbacks.indexOf(cb) < 0) _layoutsCallbacks.push(cb) }
function offLayouts(cb) { _layoutsCallbacks = _layoutsCallbacks.filter(function(item) { return item !== cb }) }
function onDevices() {}
function onTargetChanged() {}
function clearTargetChanged() {}

export default {
  init: init,
  SPP_UUID: SPP_UUID,
  diagnose: diagnose,
  getBtInfo: getBtInfo,
  setBtEnabled: setBtEnabled,
  startDiscovery: startDiscovery,
  pairDevice: pairDevice,
  listBondedDevices: listBondedDevices,
  connect: connect,
  connectDevice: connectDevice,
  restoreConnection: restoreConnection,
  send: send,
  trigger: trigger,
  triggerSlot: triggerSlot,
  close: close,
  isConnected: isConnected,
  canSendMouse: canSendMouse,
  canSendKeyboard: canSendKeyboard,
  getHidStatus: getHidStatus,
  onHidStateChange: onHidStateChange,
  offHidStateChange: offHidStateChange,
  reloadLayouts: reloadLayouts,
  getHello: getHello,
  getLayouts: getLayouts,
  getActiveLayoutId: getActiveLayoutId,
  getActivePageId: getActivePageId,
  onStateChange: onStateChange,
  offStateChange: offStateChange,
  onMessage: onMessage,
  offMessage: offMessage,
  onHello: onHello,
  onLayouts: onLayouts,
  offLayouts: offLayouts,
  onDevices: onDevices,
  onTargetChanged: onTargetChanged,
  clearTargetChanged: clearTargetChanged,
}
