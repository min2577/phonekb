// utils/usbclient.js
// USB 模式客户端：通过 adb reverse 后连接 127.0.0.1:9877（WebSocket）。
// 与 wsclient.js API 兼容，业务页面只需把 import 改成这份即可。

import { reconnectSettings } from './appSettings.js'

let socketTask = null
let handlers = {}
let connected = false
let _lastPong = 0
let _pingTimer = null
let _stateChangeCallbacks = []
let _lastConnInfo = null
let _reconnectTimer = null
let _manualClose = false
let _layoutsCallbacks = []
let _helloCallbacks = []
let _layouts = { layouts: [], global_pages: [] }
let _helloInfo = null
let _messageCallbacks = []


function connect(opts) {
  _manualClose = false
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  if (socketTask && !connected) {
    try { socketTask.close({ code: 1000, reason: "reconnect" }) } catch (e) {}
    socketTask = null
  }
  _stopHeartbeat()
  connected = false

  const host = opts.host || "127.0.0.1"
  const port = opts.port || 9877
  const code = opts.code
  const url = "ws://" + host + ":" + port + "/"
  console.log("[usb] connecting", url)
  _lastConnInfo = { host: host, port: port, code: code }
  handlers = {
    onConnected: opts.onConnected || function() {},
    onError: opts.onError || function() {},
    onDisconnected: opts.onDisconnected || function() {},
  }

  setTimeout(function() { _doConnect(url, code) }, 200)
}

function _doConnect(url, code) {
  socketTask = uni.connectSocket({
    url: url,
    success() { console.log("[usb] socketTask created") },
    fail(err) {
      console.error("[usb] connect fail", err)
      handlers.onError(err.errMsg || "USB 连接失败")
      setTimeout(function() {
        if (connected) return
        try { socketTask && socketTask.close() } catch (e) {}
        socketTask = null
        _scheduleReconnect()
      }, 0)
    },
  })

  socketTask.onOpen(function() {
    console.log("[usb] open, sending pair")
    _sendRaw({ action: "pair", secret: code, ua: "app-usb/0.3" })
    if (connect._timeoutId) clearTimeout(connect._timeoutId)
    connect._timeoutId = setTimeout(function() {
      console.error("[usb] pair timeout")
      handlers.onError("配对超时（5秒）")
      try { socketTask.close() } catch (e) {}
    }, 5000)
  })

  socketTask.onMessage(function(res) {
    let msg
    try { msg = JSON.parse(res.data) } catch (e) { return }
    if (msg.action === "pong") { _lastPong = Date.now(); return }
    if (msg.action === "paired") {
      if (connect._timeoutId) { clearTimeout(connect._timeoutId); connect._timeoutId = null }
      if (msg.ok) {
        connected = true
        _reconnectAttempts = 0
        _lastPong = Date.now()
        _startHeartbeat()
        _emitStateChange("connected")
        handlers.onConnected()
        // 配对成功立刻拉一次布局，避免第一次进入页面拿到空缓存
        setTimeout(function() { try { send({ action: "reload_layouts" }) } catch (e) {} }, 100)
      } else {
        connected = false
        _emitStateChange("disconnected")
        handlers.onError("配对码错误")
        try { socketTask.close() } catch (e) {}
      }
    } else if (msg.action === "error") {
      handlers.onError(msg.msg || "协议错误")
    } else if (msg.action === "trigger_ack") {
      if (!msg.ok && msg.msg) uni.showToast({ title: msg.msg, icon: "none" })
    } else if (msg.action === "layouts") {
      _layouts = msg.data || _layouts
      try { uni.setStorageSync("phonekb.last_layouts", _layouts) } catch (e) {}
      for (let i = 0; i < _layoutsCallbacks.length; i++) {
        try { _layoutsCallbacks[i](_layouts) } catch (e) {}
      }
    } else if (msg.action === "hello") {
      if (msg.layouts) _layouts = msg.layouts
      if (msg.hello) _helloInfo = msg.hello
      try { uni.setStorageSync("phonekb.last_layouts", _layouts) } catch (e) {}
      for (let i = 0; _helloCallbacks.length && i < _helloCallbacks.length; i++) {
        try { _helloCallbacks[i](_helloInfo || {}) } catch (e) {}
      }
    }
    _emitMessage(msg)
  })

  socketTask.onError(function(err) {
    console.error("[usb] onError", err)
    handlers.onError(err.errMsg || "连接错误")
    _scheduleReconnect()
  })

  socketTask.onClose(function() {
    console.log("[usb] closed")
    connected = false
    _stopHeartbeat()
    _emitStateChange("disconnected")
    handlers.onDisconnected()
    socketTask = null
    _scheduleReconnect()
  })
}

let _reconnectAttempts = 0

function _scheduleReconnect() {
  if (_manualClose || !_lastConnInfo || _reconnectTimer) return
  const settings = reconnectSettings()
  if (!settings.enabled || _reconnectAttempts >= settings.maxAttempts) return
  _reconnectAttempts++
  const delay = Math.min(1000 * Math.pow(1.7, _reconnectAttempts - 1), 10000)
  _reconnectTimer = setTimeout(function() {
    _reconnectTimer = null
    if (_manualClose || !_lastConnInfo || socketTask) return
    const url = "ws://" + _lastConnInfo.host + ":" + _lastConnInfo.port + "/"
    console.log("[usb] reconnecting", url)
    _doConnect(url, _lastConnInfo.code)
  }, delay)
}

function _startHeartbeat() {
  _stopHeartbeat()
  const settings = reconnectSettings()
  const timeout = Math.max(15000, settings.heartbeatMs * 2 + 5000)
  _lastPong = Date.now()
  _pingTimer = setInterval(function() {
    if (!connected) return
    if (Date.now() - _lastPong > timeout) {
      console.warn("[usb] pong timeout, force close")
      try { socketTask.close() } catch (e) {}
      return
    }
    send({ action: "ping" })
  }, settings.heartbeatMs)
}

function _stopHeartbeat() {
  if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null }
}

function _emitStateChange(state) {
  for (let i = 0; i < _stateChangeCallbacks.length; i++) {
    try { _stateChangeCallbacks[i](state) } catch (e) {}
  }
}

function _sendRaw(obj) {
  if (!socketTask) return false
  try {
    socketTask.send({ data: JSON.stringify(obj) })
    return true
  } catch (e) {
    console.error("[usb] send fail", e)
    return false
  }
}

function triggerSlot(id) {
  const ok = send({ action: "trigger_slot", id: id })
  if (ok) try { uni.vibrateShort({ type: "light" }) } catch (e) {}
  return ok
}

function close() {
  _manualClose = true
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  if (connect._timeoutId) { clearTimeout(connect._timeoutId); connect._timeoutId = null }
  if (socketTask) {
    try { socketTask.close({ code: 1000, reason: "client close" }) } catch (e) {}
    socketTask = null
  }
  connected = false
  _stopHeartbeat()
}

function isConnected() { return connected }
function onStateChange(cb) { if (typeof cb === 'function' && _stateChangeCallbacks.indexOf(cb) < 0) _stateChangeCallbacks.push(cb) }
function offStateChange(cb) { _stateChangeCallbacks = _stateChangeCallbacks.filter(function(item) { return item !== cb }) }
function onLayouts(cb) { if (typeof cb === 'function' && _layoutsCallbacks.indexOf(cb) < 0) _layoutsCallbacks.push(cb) }
function offLayouts(cb) { _layoutsCallbacks = _layoutsCallbacks.filter(function(item) { return item !== cb }) }
function onHello(cb) { _helloCallbacks.push(cb) }
function onMessage(cb) { if (typeof cb === 'function' && _messageCallbacks.indexOf(cb) < 0) _messageCallbacks.push(cb) }
function offMessage(cb) { _messageCallbacks = _messageCallbacks.filter(function(item) { return item !== cb }) }
function _emitMessage(msg) {
  for (let i = 0; i < _messageCallbacks.length; i++) {
    try { _messageCallbacks[i](msg) } catch (e) {}
  }
}

function send(obj) {
  if (!connected) return false
  return _sendRaw(obj)
}
function getLayouts() { return _layouts }
function getHello() { return _helloInfo }
function reloadLayouts() { return send({ action: "reload_layouts" }) }
function deleteLayout(layoutId) { return send({ action: "delete_layout", layout_id: layoutId }) }

export default {
  connect: connect,
  send: send,
  triggerSlot: triggerSlot,
  close: close,
  isConnected: isConnected,
  onStateChange: onStateChange, offStateChange: offStateChange,
  onLayouts: onLayouts, offLayouts: offLayouts, onHello: onHello, onMessage: onMessage, offMessage: offMessage,
  getLayouts: getLayouts, getHello: getHello,
  reloadLayouts: reloadLayouts,
  deleteLayout: deleteLayout,
}
