export const STORAGE_PREFIX = 'phonekb.jianying.workbench.v2.'
export const LEGACY_STORAGE_PREFIX = 'phonekb.jianying.workbench.v1.'
export const WORKBENCH_CONFIG_CHANGED_EVENT = 'phonekb:jianying-workbench-config-changed'
export const SHORTCUT_COUNT = 8
export const TIMELINE_BUTTON_COUNT = 4

export const JIANYING_SHORTCUT_PRESETS = [
  { id: 'split', label: '分割', mods: ['ctrl'], key: 'b' },
  { id: 'batch-split', label: '批量分割', mods: ['ctrl', 'shift'], key: 'b' },
  { id: 'enable-clip', label: '启用片段', mods: [], key: 'v' },
  { id: 'detach-audio', label: '分离音频', mods: ['ctrl', 'shift'], key: 's' },
  { id: 'add-marker', label: '添加标记', mods: [], key: 'm' },
  { id: 'add-color-marker', label: '异色标记', mods: ['alt'], key: 'm' },
  { id: 'trim-left', label: '向左裁剪', mods: [], key: 'q' },
  { id: 'trim-right', label: '向右裁剪', mods: [], key: 'w' },
  { id: 'select-mode', label: '鼠标选择', mods: [], key: 'a' },
  { id: 'split-mode', label: '鼠标分割', mods: [], key: 'b' },
  { id: 'select-left', label: '向左全选', mods: [], key: '[' },
  { id: 'select-right', label: '向右全选', mods: [], key: ']' },
  { id: 'main-magnet', label: '主轨磁吸', mods: [], key: 'p' },
  { id: 'snapping', label: '吸附开关', mods: [], key: 'n' },
  { id: 'preview-axis', label: '预览轴开关', mods: [], key: 's' },
  { id: 'track-grow', label: '轨道放大', mods: ['ctrl'], key: '=' },
  { id: 'track-shrink', label: '轨道缩小', mods: ['ctrl'], key: '-' },
  { id: 'previous-frame', label: '上一帧', mods: [], key: 'left' },
  { id: 'next-frame', label: '下一帧', mods: [], key: 'right' },
  { id: 'first-frame', label: '定位首帧', mods: [], key: 'home' },
  { id: 'last-frame', label: '定位尾帧', mods: [], key: 'end' },
  { id: 'region-in', label: '区域入点', mods: [], key: 'i' },
  { id: 'region-out', label: '区域出点', mods: [], key: 'o' },
  { id: 'select-clip-region', label: '选定片段区域', mods: ['shift'], key: 'x' },
  { id: 'cancel-region', label: '取消选定区域', mods: ['alt'], key: 'x' },
  { id: 'group', label: '创建组合', mods: ['ctrl'], key: 'g' },
  { id: 'ungroup', label: '解除组合', mods: ['ctrl', 'shift'], key: 'g' },
  { id: 'speed-panel', label: '变速面板', mods: ['ctrl'], key: 'r' },
]

export const JIANYING_TIMELINE_BUTTON_PRESETS = [
  { id: 'previous-frame', label: '上一帧', mods: [], key: 'left' },
  { id: 'next-frame', label: '下一帧', mods: [], key: 'right' },
  { id: 'first-frame', label: '定位首帧', mods: [], key: 'home' },
  { id: 'last-frame', label: '定位尾帧', mods: [], key: 'end' },
]

export const GESTURE_ACTIONS = {
  previous_frame: { id: 'previous_frame', label: '上一帧', type: 'shortcut', modifiers: [], key: 'left' },
  next_frame: { id: 'next_frame', label: '下一帧', type: 'shortcut', modifiers: [], key: 'right' },
  timeline_scroll_backward: { id: 'timeline_scroll_backward', label: '时间轴向前滚动', type: 'mouse_wheel', delta: 120 },
  timeline_scroll_forward: { id: 'timeline_scroll_forward', label: '时间轴向后滚动', type: 'mouse_wheel', delta: -120 },
  large_backward: { id: 'large_backward', label: '时间轴向前大幅移动', type: 'shortcut', modifiers: ['shift'], key: 'left' },
  large_forward: { id: 'large_forward', label: '时间轴向后大幅移动', type: 'shortcut', modifiers: ['shift'], key: 'right' },
  timeline_zoom_in: { id: 'timeline_zoom_in', label: '放大时间轴', type: 'mouse_zoom', delta: 120 },
  timeline_zoom_out: { id: 'timeline_zoom_out', label: '缩小时间轴', type: 'mouse_zoom', delta: -120 },
  track_zoom_in: { id: 'track_zoom_in', label: '放大轨道', type: 'shortcut', modifiers: ['ctrl'], key: '=' },
  track_zoom_out: { id: 'track_zoom_out', label: '缩小轨道', type: 'shortcut', modifiers: ['ctrl'], key: '-' },
  none: { id: 'none', label: '无操作', type: 'none' },
}

export const SWIPE_ACTION_IDS = ['timeline_scroll_backward', 'timeline_scroll_forward', 'previous_frame', 'next_frame', 'large_backward', 'large_forward', 'none']
export const PINCH_ACTION_IDS = ['timeline_zoom_in', 'timeline_zoom_out', 'track_zoom_in', 'track_zoom_out', 'none']

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

export function normalizeWorkbenchScope(scope) {
  let value = String(scope || 'default')
  for (let index = 0; index < 3; index++) {
    try {
      const decoded = decodeURIComponent(value)
      if (decoded === value) break
      value = decoded
    } catch (e) {
      break
    }
  }
  return value || 'default'
}

function shortcutFromPreset(preset, index, idPrefix = 'jy-shortcut') {
  return {
    id: idPrefix + '-' + (index + 1),
    label: preset.label,
    sub: formatShortcut(preset.mods, preset.key),
    icon: '',
    type: 'shortcut',
    feedback: { vibrate: true, sound: false, toast: false },
    shortcut: { modifiers: preset.mods.slice(), key: preset.key },
  }
}

export function formatShortcut(modifiers, key) {
  const labels = { ctrl: 'Ctrl', lctrl: 'LCtrl', rctrl: 'RCtrl', shift: 'Shift', lshift: 'LShift', rshift: 'RShift', alt: 'Alt', lalt: 'LAlt', ralt: 'RAlt', win: 'Win', left: '←', right: '→', up: '↑', down: '↓' }
  const parts = (modifiers || []).map(function(item) { return labels[item] || String(item) })
  const keyName = labels[key] || (String(key || '').length === 1 ? String(key).toUpperCase() : String(key || ''))
  if (keyName) parts.push(keyName)
  return parts.join(' + ')
}

function normalizeShortcut(input, index, presets = JIANYING_SHORTCUT_PRESETS, idPrefix = 'jy-shortcut') {
  const fallback = shortcutFromPreset(presets[index], index, idPrefix)
  const source = input && typeof input === 'object' ? input : fallback
  const shortcut = source.shortcut && typeof source.shortcut === 'object' ? source.shortcut : fallback.shortcut
  const modifiers = Array.isArray(shortcut.modifiers) ? shortcut.modifiers.map(function(item) { return String(item || '') }).filter(Boolean) : []
  const key = String(shortcut.key || '')
  return {
    id: String(source.id || fallback.id),
    label: String(source.label || fallback.label),
    sub: String(source.sub || formatShortcut(modifiers, key)),
    icon: String(source.icon || ''),
    type: 'shortcut',
    feedback: Object.assign({}, fallback.feedback, source.feedback || {}),
    shortcut: { modifiers: modifiers, key: key },
  }
}

function normalizeActionId(value, allowed, fallback) {
  const id = String(value || '')
  return allowed.indexOf(id) >= 0 ? id : fallback
}

export function defaultConfig() {
  return {
    version: 3,
    revision: 0,
    shortcuts: JIANYING_SHORTCUT_PRESETS.slice(0, SHORTCUT_COUNT).map(function(preset, index) { return shortcutFromPreset(preset, index) }),
    timelineButtons: JIANYING_TIMELINE_BUTTON_PRESETS.map(function(preset, index) { return shortcutFromPreset(preset, index, 'jy-timeline') }),
    timeline: {
      enabled: true,
      sensitivity: 'medium',
      swipeMultiplier: 1.4,
      pinchMultiplier: 1,
      swipeLeft: 'timeline_scroll_forward',
      swipeRight: 'timeline_scroll_backward',
      pinchOut: 'timeline_zoom_in',
      pinchIn: 'timeline_zoom_out',
    },
  }
}

export function normalizeConfig(input) {
  const source = input && typeof input === 'object' ? input : {}
  const defaults = defaultConfig()
  const sourceShortcuts = Array.isArray(source.shortcuts) ? source.shortcuts : []
  const shortcuts = []
  for (let index = 0; index < SHORTCUT_COUNT; index++) shortcuts.push(normalizeShortcut(sourceShortcuts[index], index))
  const sourceTimelineButtons = Array.isArray(source.timelineButtons) ? source.timelineButtons : []
  const timelineButtons = []
  for (let index = 0; index < TIMELINE_BUTTON_COUNT; index++) {
    timelineButtons.push(normalizeShortcut(sourceTimelineButtons[index], index, JIANYING_TIMELINE_BUTTON_PRESETS, 'jy-timeline'))
  }
  const timeline = source.timeline && typeof source.timeline === 'object' ? source.timeline : {}
  const sensitivity = ['stable', 'medium', 'sensitive'].indexOf(timeline.sensitivity) >= 0 ? timeline.sensitivity : defaults.timeline.sensitivity
  let swipeMultiplier = Math.max(0.5, Math.min(2.5, Number(timeline.swipeMultiplier) || defaults.timeline.swipeMultiplier))
  const pinchMultiplier = Math.max(0.5, Math.min(3, Number(timeline.pinchMultiplier) || defaults.timeline.pinchMultiplier))
  let swipeLeft = normalizeActionId(timeline.swipeLeft, SWIPE_ACTION_IDS, defaults.timeline.swipeLeft)
  let swipeRight = normalizeActionId(timeline.swipeRight, SWIPE_ACTION_IDS, defaults.timeline.swipeRight)
  if ((Number(source.version) || 0) < 3 && swipeLeft === 'next_frame' && swipeRight === 'previous_frame') {
    swipeLeft = defaults.timeline.swipeLeft
    swipeRight = defaults.timeline.swipeRight
    if (swipeMultiplier === 1) swipeMultiplier = defaults.timeline.swipeMultiplier
  }
  return {
    version: 3,
    revision: Math.max(0, Number(source.revision) || 0),
    shortcuts: shortcuts,
    timelineButtons: timelineButtons,
    timeline: {
      enabled: timeline.enabled !== false,
      sensitivity: sensitivity,
      swipeMultiplier: swipeMultiplier,
      pinchMultiplier: pinchMultiplier,
      swipeLeft: swipeLeft,
      swipeRight: swipeRight,
      pinchOut: normalizeActionId(timeline.pinchOut, PINCH_ACTION_IDS, defaults.timeline.pinchOut),
      pinchIn: normalizeActionId(timeline.pinchIn, PINCH_ACTION_IDS, defaults.timeline.pinchIn),
    },
  }
}

export function updateShortcut(config, index, key) {
  const next = normalizeConfig(config)
  if (index < 0 || index >= SHORTCUT_COUNT) return next
  next.shortcuts.splice(index, 1, normalizeShortcut(key, index))
  return next
}

export function updateTimelineButton(config, index, key) {
  const next = normalizeConfig(config)
  if (index < 0 || index >= TIMELINE_BUTTON_COUNT) return next
  next.timelineButtons.splice(index, 1, normalizeShortcut(key, index, JIANYING_TIMELINE_BUTTON_PRESETS, 'jy-timeline'))
  return next
}

export function moveShortcut(config, fromIndex, toIndex) {
  const next = normalizeConfig(config)
  if (fromIndex < 0 || fromIndex >= SHORTCUT_COUNT || toIndex < 0 || toIndex >= SHORTCUT_COUNT || fromIndex === toIndex) return next
  const moved = next.shortcuts.splice(fromIndex, 1)[0]
  next.shortcuts.splice(toIndex, 0, moved)
  return next
}

export function updateTimeline(config, updates) {
  const next = normalizeConfig(config)
  next.timeline = Object.assign({}, next.timeline, updates || {})
  return normalizeConfig(next)
}

export function getGestureAction(actionId) {
  return clone(GESTURE_ACTIONS[actionId] || GESTURE_ACTIONS.none)
}

function storageKey(prefix, scope) {
  return prefix + normalizeWorkbenchScope(scope)
}

function storedScopeVariants(scope) {
  const canonical = normalizeWorkbenchScope(scope)
  const variants = [canonical]
  let encoded = canonical
  for (let index = 0; index < 2; index++) {
    encoded = encodeURIComponent(encoded)
    if (variants.indexOf(encoded) < 0) variants.push(encoded)
  }
  const supplied = String(scope || '')
  if (supplied && variants.indexOf(supplied) < 0) variants.push(supplied)
  return variants
}

export function loadWorkbenchConfig(scope) {
  try {
    const canonicalKey = storageKey(STORAGE_PREFIX, scope)
    const variants = storedScopeVariants(scope)
    let selected = null
    let selectedKey = ''
    variants.forEach(function(variant) {
      const key = STORAGE_PREFIX + variant
      const cached = uni.getStorageSync(key)
      if (!cached) return
      const candidate = normalizeConfig(cached)
      if (!selected || candidate.revision > selected.revision) {
        selected = candidate
        selectedKey = key
      }
    })
    if (selected) {
      if (selectedKey !== canonicalKey) uni.setStorageSync(canonicalKey, selected)
      return selected
    }
    const legacy = uni.getStorageSync(storageKey(LEGACY_STORAGE_PREFIX, scope))
    return normalizeConfig(legacy)
  } catch (e) {
    return defaultConfig()
  }
}

export function saveWorkbenchConfig(scope, config) {
  const normalized = normalizeConfig(config)
  try {
    const current = loadWorkbenchConfig(scope)
    normalized.revision = Math.max(Date.now(), (Number(current.revision) || 0) + 1)
    const key = storageKey(STORAGE_PREFIX, scope)
    uni.setStorageSync(key, normalized)

    const verified = normalizeConfig(uni.getStorageSync(key))
    if (JSON.stringify(verified) !== JSON.stringify(normalized)) {
      throw new Error('saved config did not match the value read from storage')
    }
    if (uni && typeof uni.$emit === 'function') {
      uni.$emit(WORKBENCH_CONFIG_CHANGED_EVENT, {
        scope: normalizeWorkbenchScope(scope),
        revision: verified.revision,
        config: verified,
      })
    }
    return verified
  } catch (e) {
    console.warn('[jianyingWorkbenchConfig] save failed', e)
    return null
  }
}
