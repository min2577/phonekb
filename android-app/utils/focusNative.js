import {
  startFocus as nativeStartFocus,
  stopFocus as nativeStopFocus,
  getFocusState as nativeGetFocusState,
  isAccessibilityEnabled as nativeIsAccessibilityEnabled,
  openAccessibilitySettings as nativeOpenAccessibilitySettings,
  isOverlayEnabled as nativeIsOverlayEnabled,
  openOverlaySettings as nativeOpenOverlaySettings,
  openAppDetails as nativeOpenAppDetails,
} from '@/uni_modules/phonekb-focus'

function isAndroidRuntime() {
  return typeof plus !== 'undefined' && !!plus.android
}

export function isAccessibilityEnabled() {
  if (!isAndroidRuntime()) return false
  try { return !!nativeIsAccessibilityEnabled() } catch (e) { return false }
}

export function openAccessibilitySettings() {
  if (!isAndroidRuntime()) return false
  try {
    if (nativeOpenAccessibilitySettings()) return true
  } catch (e) {
    console.warn('[focusNative] UTS accessibility settings launch failed', e)
  }
  // 某些厂商 ROM 对 Application Context 启动设置页限制更严,用当前 Activity 兜底。
  try {
    const Intent = plus.android.importClass('android.content.Intent')
    const Settings = plus.android.importClass('android.provider.Settings')
    const activity = plus.android.runtimeMainActivity()
    const intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
    activity.startActivity(intent)
    return true
  } catch (e) {
    console.warn('[focusNative] fallback accessibility settings launch failed', e)
    return false
  }
}

export function isOverlayEnabled() {
  if (!isAndroidRuntime()) return false
  try { return !!nativeIsOverlayEnabled() } catch (e) { return false }
}

export function openOverlaySettings() {
  if (!isAndroidRuntime()) return false
  try {
    if (nativeOpenOverlaySettings()) return true
  } catch (e) {
    console.warn('[focusNative] UTS overlay settings launch failed', e)
  }
  try {
    const Intent = plus.android.importClass('android.content.Intent')
    const Settings = plus.android.importClass('android.provider.Settings')
    const Uri = plus.android.importClass('android.net.Uri')
    const activity = plus.android.runtimeMainActivity()
    const intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
    intent.setData(Uri.parse('package:' + activity.getPackageName()))
    activity.startActivity(intent)
    return true
  } catch (e) {
    console.warn('[focusNative] fallback overlay settings launch failed', e)
    return false
  }
}

export function openAppDetails() {
  if (!isAndroidRuntime()) return false
  try { return !!nativeOpenAppDetails() } catch (e) { return false }
}

export function startFocus(durationSec, whitelist) {
  if (!isAndroidRuntime()) return false
  try { return !!nativeStartFocus(Number(durationSec) || 0, Array.isArray(whitelist) ? whitelist : []) } catch (e) {
    console.warn('[focusNative] start failed', e)
    return false
  }
}

export function stopFocus() {
  if (!isAndroidRuntime()) return true
  try { return !!nativeStopFocus() } catch (e) { return false }
}

export function getFocusState() {
  if (!isAndroidRuntime()) return { active: false, endAt: 0, whitelist: [] }
  try {
    const state = nativeGetFocusState()
    return state && typeof state === 'object' ? state : { active: false, endAt: 0, whitelist: [] }
  } catch (e) { return { active: false, endAt: 0, whitelist: [] } }
}
