var path = require('path')
var url = require('url')

var storage = {}
var vibrations = 0
var toasts = 0

global.uni = {
  getStorageSync: function(key) { return storage[key] },
  setStorageSync: function(key, value) { storage[key] = value },
  vibrateShort: function() { vibrations++ },
  vibrateLong: function() { vibrations++ },
  showToast: function() { toasts++ },
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
  console.log('  PASS ' + message)
}

(async function() {
  var settingsPath = path.resolve(__dirname, '../utils/appSettings.js')
  var settings = await import(url.pathToFileURL(settingsPath).href)

  assert(settings.loadSettings().autoReconnect === true, 'default settings load')
  assert(settings.loadSettings().touchpadTapDrag === true, 'tap-drag is enabled by default')
  assert(settings.loadSettings().touchpadNaturalScroll === true, 'natural scrolling is enabled by default')
  settings.saveSettings({ touchpadSensitivity: 2.1, maxReconnect: 3 })
  assert(storage['phonekb.tp_sens'] === 2.1, 'touchpad sensitivity stays in sync')
  assert(settings.reconnectSettings().maxAttempts === 3, 'reconnect limit is applied')

  settings.installFeedbackRuntime()
  uni.vibrateShort()
  uni.showToast({ title: 'test' })
  assert(vibrations === 1 && toasts === 1, 'feedback is enabled by default')

  settings.saveSettings({ vibrate: false, toast: false })
  uni.vibrateShort()
  uni.vibrateLong()
  uni.showToast({ title: 'hidden' })
  assert(vibrations === 1 && toasts === 1, 'disabled feedback is suppressed')
})().catch(function(error) {
  console.error('[test] ERROR:', error)
  process.exit(1)
})
