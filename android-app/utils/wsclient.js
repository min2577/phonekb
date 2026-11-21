// utils/wsclient.js
// WebSocket 客户端 + 配对 + V2 协议（layouts / pages / slots）
// 从微信小程序迁移到 uni-app：把 wx. 替换为 uni.

// utils/wsclient.js
// WebSocket 客户端 + 配对 + V2 协议（layouts / pages / slots）

import { reconnectSettings } from './appSettings.js'
import { pendingLayouts, clearPendingLayouts } from './gamepadEditorStore.js'

let socketTask = null
let handlers = {}
let connected = false
let _targetChangedCallbacks = []
let _stateChangeCallbacks = []
let _layoutsCallbacks = []
let _helloCallbacks = []
let _customKeysCallbacks = []
let _lastCustomKeys = []
let _gamepadLayoutsCallbacks = []
let _gamepadLayouts = null
let _messageCallbacks = []

let _devicesCallbacks = []
let _lastConnInfo = null
let _reconnectTimer = null
let _reconnectAttempts = 0
let _connecting = false
let _pendingConn = null
let _manualClose = false
let _connectDelayTimer = null
let _helloInfo = null   // {server, proto}
let _layouts = { layouts: [], global_pages: [] }

function connect(opts) {
  if (_connecting) {
    if (_pendingConn) return _pendingConn
    return
  }
  _connecting = true
  _manualClose = false
  _pendingConn = new Promise(function(resolve) {
    setTimeout(function() { _connecting = false; _pendingConn = null; resolve() }, 2000)
  })

  if (socketTask) {
    try { socketTask.close({ code: 1000, reason: "reconnect" }) } catch (e) {}
    socketTask = null
  }
  try { uni.closeSocket({ code: 1000 }) } catch (e) {}
  _stopHeartbeat()
  if (_connectDelayTimer) { clearTimeout(_connectDelayTimer); _connectDelayTimer = null }
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  connected = false

  const host = opts.host
  const port = opts.port || 9876
  const code = opts.code
  const token = opts.token || null
  const url = "ws://" + host + ":" + port + "/"
  console.log("[ws] connecting", url)
  _lastConnInfo = { host: host, port: port, code: code, token: token }
  handlers = {
    onConnected: opts.onConnected || function() {},
    onError: opts.onError || function() {},
    onDisconnected: opts.onDisconnected || function() {},
  }

  _connectDelayTimer = setTimeout(function() {
    _connectDelayTimer = null
    if (!_manualClose) _doConnect(url, code, token)
  }, 300)
}

function _doConnect(url, code, token) {
  if (_manualClose) return
  const task = uni.connectSocket({
    url: url,
    success() { console.log("[ws] socketTask created") },
    fail(err) {
      console.error("[ws] connect fail", err)
      handlers.onError(err.errMsg || "连接失败")
    },
  })
  socketTask = task

  task.onOpen(function() {
    if (_manualClose || socketTask !== task) return
    console.log("[ws] open, sending pair")
    // 优先用 v2 token（QR 码扫码），否则用 6 位配对码（手输）
    const pairValue = token || code
    const app = typeof getApp === 'function' ? getApp({ allowDefault: true }) : null
    send({ action: "pair", secret: pairValue, ua: "wxapp/" + (app && app.globalData ? app.globalData.appVersion || "0.3" : "0.3") })
    if (connect._timeoutId) clearTimeout(connect._timeoutId)
    connect._timeoutId = setTimeout(function() {
      console.error("[ws] pair timeout")
      handlers.onError("配对超时（5秒），请检查 IP 和配对码")
      try { task.close() } catch (e) {}
    }, 5000)
  })

  task.onMessage(function(res) {
    if (_manualClose || socketTask !== task) return
    let msg
    try { msg = JSON.parse(res.data) } catch (e) { return }
    if (msg.action === "pong") { _lastPong = Date.now(); return }

    if (msg.action === "paired") {
      if (connect._timeoutId) { clearTimeout(connect._timeoutId); connect._timeoutId = null }
      if (msg.ok) {
        connected = true
        _reconnectAttempts = 0
        _lastPong = Date.now()
        _helloInfo = { server: msg.server, proto: msg.proto }
        _startHeartbeat()
        _emitStateChange("connected")
        const pending = pendingLayouts()
        if (pending) send({ action: "save_gamepad_layouts", data: pending })
        else send({ action: "get_gamepad_layouts" })
        handlers.onConnected()
      } else {
        connected = false
        _emitStateChange("disconnected")
        handlers.onError("配对码错误")
        try { task.close() } catch (e) {}
      }
    } else if (msg.action === "hello") {
      _helloInfo = { server: msg.server, proto: msg.proto }
      if (msg.layouts) _layouts = msg.layouts
      for (let i = 0; i < _helloCallbacks.length; i++) {
        try { _helloCallbacks[i](msg) } catch (e) {}
      }
      for (let i = 0; i < _layoutsCallbacks.length; i++) {
        try { _layoutsCallbacks[i](_layouts) } catch (e) {}
      }
      // 缓存到本地
      try {
        uni.setStorageSync("phonekb.last_layouts", _layouts)
        uni.setStorageSync("phonekb.hello", _helloInfo)
      } catch (e) {}
    } else if (msg.action === "layouts") {
      _layouts = msg.data || _layouts
      try { uni.setStorageSync("phonekb.last_layouts", _layouts) } catch (e) {}
      for (let i = 0; i < _layoutsCallbacks.length; i++) {
        try { _layoutsCallbacks[i](_layouts) } catch (e) {}
      }
    } else if (msg.action === "devices") {
      for (let i = 0; i < _devicesCallbacks.length; i++) {
        try { _devicesCallbacks[i](msg.devices || []) } catch (e) {}
      }
    } else if (msg.action === "custom_keys") {
  _lastCustomKeys = msg.keys || []
  try { uni.setStorageSync("phonekb.last_custom_keys", _lastCustomKeys) } catch (e) {}
  for (let i = 0; i < _customKeysCallbacks.length; i++) {
    try { _customKeysCallbacks[i](_lastCustomKeys) } catch (e) {}
  }
} else if (msg.action === "save_gamepad_layouts_ack") {
  if (msg.ok && msg.data) {
    clearPendingLayouts()
    _gamepadLayouts = msg.data
    try { uni.setStorageSync("phonekb.gamepad_layouts", _gamepadLayouts) } catch (e) {}
  }
} else if (msg.action === "gamepad_layouts") {
  if (!pendingLayouts()) {
    _gamepadLayouts = msg.data || _gamepadLayouts
    try { uni.setStorageSync("phonekb.gamepad_layouts", _gamepadLayouts) } catch (e) {}
    for (let i = 0; i < _gamepadLayoutsCallbacks.length; i++) {
      try { _gamepadLayoutsCallbacks[i](_gamepadLayouts) } catch (e) {}
    }
  }
} else if (msg.action === "trigger_ack") {
      if (!msg.ok && msg.msg) {
        uni.showToast({ title: msg.msg, icon: "none" })
      }
    } else if (msg.action === "shortcut_ack") {
      if (!msg.ok) {
        uni.showToast({ title: "未知快捷键: " + msg.name, icon: "none" })
      }
    } else if (msg.action === "error") {
      handlers.onError(msg.msg || "协议错误")
    } else if (msg.action === "target_changed") {
      try {
        const app = getApp({ allowDefault: true })
        if (app) { app.globalData.targetInfo = msg.title || "(无标题)" }
      } catch (e) {}
      handlers.onTargetChanged && handlers.onTargetChanged(msg.title || "(无标题)", msg.hwnd)
    }
    _emitMessage(msg)
  })

  task.onError(function(err) {
    if (_manualClose || socketTask !== task) return
    console.error("[ws] error", err)
    connected = false
    _emitStateChange("disconnected")
    handlers.onError(err.errMsg || "网络错误")
    _scheduleReconnect()
  })

  task.onClose(function(res) {
    if (_manualClose || socketTask !== task) return
    console.log("[ws] close", res && res.code, res && res.reason)
    socketTask = null
    connected = false
    _stopHeartbeat()
    _emitStateChange("disconnected")
    handlers.onDisconnected()
    _scheduleReconnect()
  })
}

function _emitStateChange(state) {
  for (let i = 0; i < _stateChangeCallbacks.length; i++) {
    try { _stateChangeCallbacks[i](state) } catch (e) {}
  }
}


function _doReconnect() {
  if (_manualClose || !_lastConnInfo) return
  if (socketTask) {
    try { socketTask.close({ code: 1000, reason: "reconnect" }) } catch (e) {}
    socketTask = null
  }
  try { uni.closeSocket({ code: 1000 }) } catch (e) {}
  _stopHeartbeat()
  connected = false
  const url = "ws://" + _lastConnInfo.host + ":" + _lastConnInfo.port + "/"
  console.log("[ws] reconnecting (handlers preserved) " + url)
  _doConnect(url, _lastConnInfo.code, _lastConnInfo.token)
}
function _scheduleReconnect() {
  if (_manualClose) return
  if (_reconnectTimer) return
  if (!_lastConnInfo) return
  const settings = reconnectSettings()
  if (!settings.enabled || _reconnectAttempts >= settings.maxAttempts) return
  _reconnectAttempts++
  const delay = Math.max(2000, Math.min(2000 * Math.pow(1.7, _reconnectAttempts - 1), 15000))
  console.log("[ws] reconnect in " + delay + "ms (attempt " + _reconnectAttempts + ")")
  _reconnectTimer = setTimeout(function() {
    _reconnectTimer = null
    if (!_manualClose && _lastConnInfo) _doReconnect()
  }, delay)
}

let _pingTimer = null
let _lastPong = 0

function _startHeartbeat() {
  if (_pingTimer) return
  const settings = reconnectSettings()
  const timeout = Math.max(15000, settings.heartbeatMs * 2 + 5000)
  _lastPong = Date.now()
  _pingTimer = setInterval(function() {
    if (!connected) return
    if (Date.now() - _lastPong > timeout) {
      console.warn("[ws] pong timeout, force close")
      try { socketTask.close() } catch (e) {}
      return
    }
    send({ action: "ping" })
  }, settings.heartbeatMs)
}

function _stopHeartbeat() {
  if (_pingTimer) { clearInterval(_pingTimer); _pingTimer = null }
}

function send(obj) {
  if (!socketTask) return false
  try {
    socketTask.send({ data: JSON.stringify(obj) })
    return true
  } catch (e) {
    console.error("[ws] send fail", e)
    return false
  }
}

function trigger(name) {
  const ok = send({ action: "shortcut", name: name })
  if (ok) try { uni.vibrateShort({ type: "light" }) } catch (e) {}
  return ok
}

function triggerSlot(idOrSlot) {
  const payload = { action: "trigger_slot" }
  if (idOrSlot && typeof idOrSlot === "object" && idOrSlot.key) {
    payload.slot = idOrSlot
    payload.id = (idOrSlot.key && idOrSlot.key.id) ? String(idOrSlot.key.id) : ""
  } else {
    payload.id = String(idOrSlot || "")
  }
  const ok = send(payload)
  if (ok) try { uni.vibrateShort({ type: "light" }) } catch (e) {}
  return ok
}

// ============ V2 CRUD 封装 ============
function addSlot(layoutId, pageId, slot, cb) {
  return send({ action: "add_slot", layout_id: layoutId, page_id: pageId, slot: slot })
}
function updateSlot(layoutId, pageId, r, c, updates, cb) {
  return send({ action: "update_slot", layout_id: layoutId, page_id: pageId, r: r, c: c, updates: updates })
}
function deleteSlot(layoutId, pageId, r, c, cb) {
  return send({ action: "delete_slot", layout_id: layoutId, page_id: pageId, r: r, c: c })
}
function moveSlot(layoutId, pageId, srcR, srcC, dstR, dstC, cb) {
  return send({ action: "move_slot", layout_id: layoutId, page_id: pageId, src_r: srcR, src_c: srcC, dst_r: dstR, dst_c: dstC })
}
function addPage(layoutId, page, cb) {
  return send({ action: "add_page", layout_id: layoutId, page: page })
}
function renamePage(layoutId, pageId, name, icon, cb) {
  return send({ action: "rename_page", layout_id: layoutId, page_id: pageId, name: name, icon: icon })
}
function deletePage(layoutId, pageId, cb) {
  return send({ action: "delete_page", layout_id: layoutId, page_id: pageId })
}
function setActive(layoutId, pageId, cb) {
  return send({ action: "set_active", layout_id: layoutId, page_id: pageId })
}
function setGridCols(cols, cb) {
  return send({ action: "set_grid_cols", grid_cols: cols })
}
function installPreset(preset, layoutId, cb) {
  return send({ action: "install_preset", preset: preset, layout_id: layoutId })
}
function renameLayout(layoutId, name, icon, cb) {
  return send({ action: "rename_layout", layout_id: layoutId, name: name, icon: icon })
}
function deleteLayout(layoutId, cb) {
  return send({ action: "delete_layout", layout_id: layoutId })
}
function reloadLayouts(cb) {
  return send({ action: "reload_layouts" })
}
function listDevices(cb) {
  return send({ action: "list_devices" })
}
function getGamepadLayouts() { return send({ action: "get_gamepad_layouts" }) }
function saveGamepadLayouts(data) { return send({ action: "save_gamepad_layouts", data: data }) }
function setActiveGamepadLayout(layoutId) { return send({ action: "set_active_gamepad_layout", layout_id: layoutId }) }
function gamepadKey(keys, down) { return send({ action: "gamepad_key", keys: keys, down: !!down }) }
function gamepadMouseMove(dx, dy) { return send({ action: "gamepad_mouse_move", dx: dx, dy: dy }) }
// V1 兼容封装
function addCustomKey(spec, cb) {
  return send({ action: "add_custom_key", spec: spec })
}
function updateCustomKey(id, updates, cb) {
  return send({ action: "update_custom_key", id: id, updates: updates })
}
function deleteCustomKey(id, cb) {
  return send({ action: "delete_custom_key", id: id })
}

function close() {
  _manualClose = true
  _connecting = false
  _pendingConn = null
  if (_connectDelayTimer) { clearTimeout(_connectDelayTimer); _connectDelayTimer = null }
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  if (connect._timeoutId) { clearTimeout(connect._timeoutId); connect._timeoutId = null }
  if (socketTask) {
    try { socketTask.close({ code: 1000, reason: "client close" }) } catch (e) {}
    socketTask = null
  }
  _stopHeartbeat()
  connected = false
}

function isConnected() { return connected }
function getHello() { return _helloInfo }
function getLayouts() { return _layouts }
function getActiveLayoutId() { return (_layouts && _layouts.active_layout_id) || "default" }
function getActivePageId() { return (_layouts && _layouts.active_page_id) || null }

function onTargetChanged(cb) { _targetChangedCallbacks.push(cb) }
function clearTargetChanged() { _targetChangedCallbacks = [] }
function onStateChange(cb) { if (typeof cb === 'function' && _stateChangeCallbacks.indexOf(cb) < 0) _stateChangeCallbacks.push(cb) }
function offStateChange(cb) { _stateChangeCallbacks = _stateChangeCallbacks.filter(function(item) { return item !== cb }) }
function onHello(cb) { _helloCallbacks.push(cb) }
function onCustomKeys(cb) { _customKeysCallbacks.push(cb) }
function onGamepadLayouts(cb) { _gamepadLayoutsCallbacks.push(cb) }
function offGamepadLayouts(cb) { _gamepadLayoutsCallbacks = _gamepadLayoutsCallbacks.filter(function(item) { return item !== cb }) }
function onLayouts(cb) { if (typeof cb === 'function' && _layoutsCallbacks.indexOf(cb) < 0) _layoutsCallbacks.push(cb) }
function offLayouts(cb) { _layoutsCallbacks = _layoutsCallbacks.filter(function(item) { return item !== cb }) }
function onDevices(cb) { if (typeof cb === 'function' && _devicesCallbacks.indexOf(cb) < 0) _devicesCallbacks.push(cb) }
function offDevices(cb) { _devicesCallbacks = _devicesCallbacks.filter(function(item) { return item !== cb }) }
function onMessage(cb) { if (typeof cb === 'function' && _messageCallbacks.indexOf(cb) < 0) _messageCallbacks.push(cb) }
function offMessage(cb) { _messageCallbacks = _messageCallbacks.filter(function(item) { return item !== cb }) }
function _emitMessage(msg) {
  for (let i = 0; i < _messageCallbacks.length; i++) {
    try { _messageCallbacks[i](msg) } catch (e) {}
  }
}


function listCustomKeys(cb) {
  return send({ action: "list_custom_keys" })
}
function getCachedCustomKeys() { return _lastCustomKeys }
function getCachedGamepadLayouts() {
  if (_gamepadLayouts) return _gamepadLayouts
  try { return uni.getStorageSync("phonekb.gamepad_layouts") || null } catch (e) { return null }
}

export default {
  connect: connect, send: send, trigger: trigger, triggerSlot: triggerSlot,
  close: close, isConnected: isConnected,
  getHello: getHello, getLayouts: getLayouts,
  getActiveLayoutId: getActiveLayoutId, getActivePageId: getActivePageId,
  onTargetChanged: onTargetChanged, clearTargetChanged: clearTargetChanged,
  onStateChange: onStateChange, offStateChange: offStateChange, onHello: onHello,
  onLayouts: onLayouts, offLayouts: offLayouts, onDevices: onDevices, offDevices: offDevices, onMessage: onMessage, offMessage: offMessage,
  addSlot: addSlot, updateSlot: updateSlot, deleteSlot: deleteSlot, moveSlot: moveSlot,
  addPage: addPage, renamePage: renamePage, deletePage: deletePage,
  setActive: setActive, setGridCols: setGridCols,
  installPreset: installPreset, renameLayout: renameLayout, deleteLayout: deleteLayout,
  reloadLayouts: reloadLayouts, listDevices: listDevices,
  addCustomKey: addCustomKey, updateCustomKey: updateCustomKey, deleteCustomKey: deleteCustomKey,
  listCustomKeys: listCustomKeys, onCustomKeys: onCustomKeys, getCachedCustomKeys: getCachedCustomKeys,
  getGamepadLayouts: getGamepadLayouts, saveGamepadLayouts: saveGamepadLayouts, setActiveGamepadLayout: setActiveGamepadLayout,
  gamepadKey: gamepadKey, gamepadMouseMove: gamepadMouseMove, onGamepadLayouts: onGamepadLayouts, offGamepadLayouts: offGamepadLayouts, getCachedGamepadLayouts: getCachedGamepadLayouts,
}
