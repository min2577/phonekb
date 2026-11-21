// utils/net.js
// 统一连接入口。根据 mode（存储于 phonekb.mode）选择 usbclient 或 wsclient。
// 默认 mode = "usb"（走 USB ADB reverse，不依赖 WiFi）。

import USB from './usbclient.js'
import WS from './wsclient.js'
import BT from './btclient.js'

const DEFAULT_MODE = 'usb'

function pick() {
  try {
    var m = uni.getStorageSync('phonekb.mode') || DEFAULT_MODE
  } catch (e) {
    var m = DEFAULT_MODE
  }
  if (m === 'ble') return BT
  if (m === 'wifi') return WS
  return USB
}

var _client = null
var _mouseDx = 0
var _mouseDy = 0
var _mouseTimer = null
var _mouseLastSentAt = 0

function client() {
  if (!_client) _client = pick()
  return _client
}

function _mouseInterval() {
  return 8
}

function _flushMouseMove() {
  if (_mouseTimer) {
    clearTimeout(_mouseTimer)
    _mouseTimer = null
  }
  var dx = Math.round(_mouseDx)
  var dy = Math.round(_mouseDy)
  _mouseDx -= dx
  _mouseDy -= dy
  if (!dx && !dy) return true
  _mouseLastSentAt = Date.now()
  return safeCall('send', [{ action: 'mouse', op: 'move', dx: dx, dy: dy }])
}

function mouseMove(dx, dy) {
  dx = Number(dx) || 0
  dy = Number(dy) || 0
  if (!dx && !dy) return true
  var c = client()
  if (c && typeof c.canSendMouse === 'function') {
    if (!c.canSendMouse()) return false
  } else if (c && typeof c.isConnected === 'function' && !c.isConnected()) return false
  _mouseDx += dx
  _mouseDy += dy
  if (!_mouseTimer) {
    var delay = Math.max(0, _mouseInterval() - (Date.now() - _mouseLastSentAt))
    if (delay === 0) _flushMouseMove()
    else _mouseTimer = setTimeout(_flushMouseMove, delay)
  }
  return true
}

function getMode() {
  try {
    var m = uni.getStorageSync('phonekb.mode') || DEFAULT_MODE
    if (m === 'ble') return 'ble'
    if (m === 'wifi') return 'wifi'
    return DEFAULT_MODE
  } catch (e) { return DEFAULT_MODE }
}

function safeCall(name, args) {
  var c = client()
  if (c && typeof c[name] === 'function') return c[name].apply(c, args)
  return undefined
}

export default {
  connect: function(opts) { return safeCall('connect', [opts]) },
  restoreConnection: function(opts) { return safeCall('restoreConnection', [opts]) },
  send: function(obj) {
    if (obj && obj.action === 'mouse' && obj.op === 'move') return mouseMove(obj.dx, obj.dy)
    if (obj && obj.action === 'mouse') _flushMouseMove()
    return safeCall('send', [obj])
  },
  mouseMove: mouseMove,
  flushMouseMove: _flushMouseMove,
  trigger: function(name) {
    var c = client()
    if (typeof c.trigger === 'function') return c.trigger(name)
    return safeCall('send', [{ action: 'shortcut', name: name }])
  },
  triggerSlot: function(id) {
    var c = client()
    if (typeof c.triggerSlot === 'function') return c.triggerSlot(id)
    return safeCall('send', [{ action: 'trigger_slot', id: id }])
  },
  deleteLayout: function(id) {
    var c = client()
    if (typeof c.deleteLayout === 'function') return c.deleteLayout(id)
    return safeCall('send', [{ action: 'delete_layout', layout_id: id }])
  },
  close: function() {
    _flushMouseMove()
    return safeCall('close', [])
  },
  isConnected: function() {
    var c = client()
    return typeof c.isConnected === 'function' ? c.isConnected() : false
  },
  canSendKeyboard: function() {
    var c = client()
    if (getMode() === 'ble' && c && typeof c.canSendKeyboard === 'function') return c.canSendKeyboard()
    return c && typeof c.isConnected === 'function' ? c.isConnected() : false
  },
  canSendMouse: function() {
    var c = client()
    if (getMode() === 'ble' && c && typeof c.canSendMouse === 'function') return c.canSendMouse()
    return c && typeof c.isConnected === 'function' ? c.isConnected() : false
  },
  getHidStatus: function() { return safeCall('getHidStatus', []) || null },
  onHidStateChange: function(cb) { return safeCall('onHidStateChange', [cb]) },
  offHidStateChange: function(cb) { return safeCall('offHidStateChange', [cb]) },
  onStateChange: function(cb) { return safeCall('onStateChange', [cb]) },
  offStateChange: function(cb) { return safeCall('offStateChange', [cb]) },
  getHello: function() { return safeCall('getHello', []) },
  getLayouts: function() { return safeCall('getLayouts', []) },
  getActiveLayoutId: function() { return safeCall('getActiveLayoutId', []) },
  getActivePageId: function() { return safeCall('getActivePageId', []) },
  onDevices: function(cb) { return safeCall('onDevices', [cb]) },
  onTargetChanged: function(cb) { return safeCall("onTargetChanged", [cb]) },
  clearTargetChanged: function() { return safeCall("clearTargetChanged", []) },
  onHello: function(cb) { return safeCall("onHello", [cb]) },
  onLayouts: function(cb) { return safeCall("onLayouts", [cb]) },
  offLayouts: function(cb) { return safeCall("offLayouts", [cb]) },
  offDevices: function(cb) { return safeCall("offDevices", [cb]) },
  onMessage: function(cb) { return safeCall("onMessage", [cb]) },
  offMessage: function(cb) { return safeCall("offMessage", [cb]) },
  onPanelSchemes: function(cb) { return safeCall("onPanelSchemes", [cb]) },

  setMode: function(mode) {
    _flushMouseMove()
    var previous = _client
    var next = mode === 'ble' ? BT : (mode === 'wifi' ? WS : USB)
    if (previous && previous !== next && typeof previous.close === 'function') {
      try { previous.close() } catch (e) { console.warn('[net] close previous transport failed', e) }
    }
    try { uni.setStorageSync('phonekb.mode', mode) } catch (e) {}
    _client = next
    _mouseDx = 0
    _mouseDy = 0
    _mouseLastSentAt = 0
  },
  getMode: getMode,
}
