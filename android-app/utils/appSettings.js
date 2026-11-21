export const DEFAULT_SETTINGS = {
  autoReconnect: true,
  maxReconnect: 10,
  heartbeatSec: 25,
  vibrate: true,
  toast: true,
  theme: 'auto',
  gridCols: 4,
  touchpadSensitivity: 1.5,
  touchpadScrollSensitivity: 1,
  touchpadTapToClick: true,
  touchpadTapDrag: true,
  touchpadNaturalScroll: true,
  touchpadInertia: true,
}

export function loadSettings() {
  let cached = null
  try { cached = uni.getStorageSync('phonekb.settings') } catch (e) {}
  return Object.assign({}, DEFAULT_SETTINGS, cached && typeof cached === 'object' ? cached : {})
}

export function saveSettings(settings) {
  const next = Object.assign({}, DEFAULT_SETTINGS, settings || {})
  try {
    uni.setStorageSync('phonekb.settings', next)
    uni.setStorageSync('phonekb.tp_sens', next.touchpadSensitivity)
    return next
  } catch (e) {
    return next
  }
}

export function reconnectSettings() {
  const settings = loadSettings()
  return {
    enabled: settings.autoReconnect !== false,
    maxAttempts: Math.max(1, Number(settings.maxReconnect) || DEFAULT_SETTINGS.maxReconnect),
    heartbeatMs: Math.max(5000, (Number(settings.heartbeatSec) || DEFAULT_SETTINGS.heartbeatSec) * 1000),
  }
}

let feedbackInstalled = false

export function installFeedbackRuntime() {
  if (feedbackInstalled || typeof uni === 'undefined') return
  feedbackInstalled = true

  const vibrateShort = typeof uni.vibrateShort === 'function' ? uni.vibrateShort.bind(uni) : null
  const vibrateLong = typeof uni.vibrateLong === 'function' ? uni.vibrateLong.bind(uni) : null
  const showToast = typeof uni.showToast === 'function' ? uni.showToast.bind(uni) : null

  if (vibrateShort) {
    uni.vibrateShort = function(options) {
      if (loadSettings().vibrate === false) return
      return vibrateShort(options)
    }
  }
  if (vibrateLong) {
    uni.vibrateLong = function(options) {
      if (loadSettings().vibrate === false) return
      return vibrateLong(options)
    }
  }
  if (showToast) {
    uni.showToast = function(options) {
      if (loadSettings().toast === false) return
      return showToast(options)
    }
  }
}
