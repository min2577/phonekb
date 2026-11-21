const LAYOUTS_KEY = 'phonekb.gamepad_layouts'
const PENDING_KEY = 'phonekb.gamepad_layouts_pending'
const PRESETS_KEY = 'phonekb.gamepad_button_presets.v1'

const SKINS = ['fluent', 'matte', 'arcade', 'glass', 'keycap', 'hud', 'skill', 'pixel', 'switch', 'outline', 'neon', 'contrast']
const SHAPES = ['round', 'pill', 'square', 'diamond']
const BEHAVIORS = ['hold', 'tap', 'toggle']

function clone(value) {
  return JSON.parse(JSON.stringify(value == null ? null : value))
}

function uid(prefix) {
  return String(prefix || 'item') + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7)
}

function number(value, low, high, fallback) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(low, Math.min(high, parsed))
}

function binding(raw, fallback) {
  raw = raw && typeof raw === 'object' ? raw : {}
  const key = String(raw.key || fallback || 'space').trim().toLowerCase().slice(0, 32) || 'space'
  const modifiers = []
  ;(raw.modifiers || []).forEach(function(value) {
    const item = String(value || '').trim().toLowerCase()
    if (['ctrl', 'shift', 'alt', 'win'].includes(item) && !modifiers.includes(item)) modifiers.push(item)
  })
  return modifiers.length
    ? { type: 'shortcut', modifiers: modifiers, key: key }
    : { type: 'key', key: key }
}

function appearance(raw) {
  raw = raw && typeof raw === 'object' ? raw : {}
  const result = {
    skin: SKINS.includes(raw.skin) ? raw.skin : 'fluent',
    shape: SHAPES.includes(raw.shape) ? raw.shape : 'round',
    labelMode: ['label', 'key', 'both'].includes(raw.labelMode) ? raw.labelMode : 'label',
    pressEffect: ['sink', 'scale', 'glow', 'none'].includes(raw.pressEffect) ? raw.pressEffect : 'sink',
  }
  ;['fill', 'border', 'text'].forEach(function(field) {
    const value = String(raw[field] || '')
    if (/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(value)) result[field] = value
  })
  return result
}

function normalizeControl(raw, index) {
  raw = raw && typeof raw === 'object' ? raw : {}
  const type = ['leftStick', 'rightStick', 'dpad', 'abxy', 'shoulder', 'key', 'mouse', 'macro'].includes(raw.type) ? raw.type : 'key'
  const bindings = {}
  Object.keys(raw.bindings || {}).forEach(function(slot) { bindings[slot] = binding(raw.bindings[slot]) })
  if (!Object.keys(bindings).length && ['key', 'shoulder', 'macro'].includes(type)) bindings.press = binding(null, 'space')
  return {
    id: String(raw.id || uid('control')).slice(0, 64),
    type: type,
    label: String(raw.label || ('按钮 ' + (index + 1))).slice(0, 32),
    x: number(raw.x, 2, 98, 50),
    y: number(raw.y, 3, 97, 50),
    size: number(raw.size, 50, 220, 100),
    opacity: number(raw.opacity, 10, 100, 100),
    visible: raw.visible !== false,
    locked: !!raw.locked,
    behavior: BEHAVIORS.includes(raw.behavior) ? raw.behavior : 'hold',
    bindings: bindings,
    appearance: appearance(raw.appearance),
    ...(raw.variant === 'wide' ? { variant: 'wide' } : {}),
    ...(['rightStick', 'mouse'].includes(type) ? { sensitivity: number(raw.sensitivity, 1, 100, 55), reticle: raw.reticle !== false } : {}),
  }
}

function normalizeLayouts(raw) {
  raw = raw && typeof raw === 'object' ? raw : {}
  const layouts = (Array.isArray(raw.layouts) ? raw.layouts : []).slice(0, 30).map(function(layout, index) {
    layout = layout && typeof layout === 'object' ? layout : {}
    return {
      id: String(layout.id || uid('layout')).slice(0, 64),
      name: String(layout.name || ('自定义布局 ' + (index + 1))).slice(0, 48),
      icon: String(layout.icon || '◉').slice(0, 8),
      controls: (Array.isArray(layout.controls) ? layout.controls : []).slice(0, 80).map(normalizeControl),
      background: clone(layout.background || { id: 'mobile-light' }),
      canvas: {
        width: number(layout.canvas && layout.canvas.width, 640, 7680, 2400),
        height: number(layout.canvas && layout.canvas.height, 360, 4320, 1080),
      },
    }
  })
  const active = layouts.some(function(item) { return item.id === raw.activeLayoutId }) ? raw.activeLayoutId : (layouts[0] && layouts[0].id || '')
  return { version: 3, activeLayoutId: active, layouts: layouts }
}

function builtInPresets() {
  const specs = [
    ['jump', '跳跃', 'Space', 'space', 'keycap', 'square'],
    ['attack', '攻击', 'A', 'j', 'arcade', 'round'],
    ['skill', '技能', 'Q', 'q', 'skill', 'round'],
    ['reload', '装填', 'R', 'r', 'keycap', 'square'],
    ['interact', '交互', 'F', 'f', 'fluent', 'square'],
    ['escape', '菜单', 'Esc', 'esc', 'matte', 'pill'],
    ['map', '地图', 'M', 'm', 'hud', 'square'],
    ['sprint', '冲刺', 'Shift', 'shift', 'contrast', 'pill'],
    ['crouch', '蹲伏', 'Ctrl', 'ctrl', 'matte', 'pill'],
    ['inventory', '背包', 'Tab', 'tab', 'glass', 'square'],
    ['weapon', '切换武器', 'E', 'e', 'switch', 'round'],
    ['heal', '治疗', 'H', 'h', 'skill', 'round'],
    ['dodge', '闪避', 'Alt', 'alt', 'neon', 'round'],
    ['target', '锁定目标', 'T', 't', 'outline', 'diamond'],
    ['confirm', '确认', 'Enter', 'enter', 'fluent', 'pill'],
    ['cancel', '取消', 'Esc', 'esc', 'outline', 'pill'],
    ['pause', '暂停', 'P', 'p', 'pixel', 'square'],
    ['voice', '语音', 'V', 'v', 'hud', 'square'],
    ['quick-save', '快速保存', 'F5', 'f5', 'keycap', 'square'],
    ['quick-load', '快速读取', 'F9', 'f9', 'contrast', 'square'],
  ]
  return specs.map(function(spec) {
    return {
      id: 'builtin-' + spec[0], builtIn: true, name: spec[1], keyLabel: spec[2],
      control: normalizeControl({
        id: 'preset-' + spec[0], type: 'key', label: spec[1], size: spec[3] === 'space' ? 118 : 100,
        bindings: { press: binding(null, spec[3]) }, appearance: { skin: spec[4], shape: spec[5], labelMode: 'both', pressEffect: 'sink' },
      }, 0),
    }
  })
}

function loadLayouts() {
  try { return normalizeLayouts(uni.getStorageSync(LAYOUTS_KEY) || {}) } catch (e) { return normalizeLayouts({}) }
}

function saveLayouts(data, options) {
  const normalized = normalizeLayouts(data)
  try {
    uni.setStorageSync(LAYOUTS_KEY, normalized)
    if (!options || options.pending !== false) uni.setStorageSync(PENDING_KEY, normalized)
  } catch (e) {}
  return normalized
}

function pendingLayouts() {
  try {
    const value = uni.getStorageSync(PENDING_KEY)
    return value && Array.isArray(value.layouts) ? normalizeLayouts(value) : null
  } catch (e) { return null }
}

function clearPendingLayouts() {
  try { uni.removeStorageSync(PENDING_KEY) } catch (e) {}
}

function loadPresets() {
  let custom = []
  try {
    const value = uni.getStorageSync(PRESETS_KEY)
    custom = value && Array.isArray(value.presets) ? value.presets : []
  } catch (e) {}
  const normalized = custom.slice(0, 40).map(function(item, index) {
    return { id: String(item.id || uid('preset')), name: String(item.name || '我的按钮'), builtIn: false, control: normalizeControl(item.control, index) }
  })
  return builtInPresets().concat(normalized)
}

function savePreset(name, control) {
  const presets = loadPresets().filter(function(item) { return !item.builtIn })
  const item = { id: uid('preset'), name: String(name || control.label || '我的按钮').slice(0, 32), control: normalizeControl(clone(control), 0) }
  item.control.id = 'preset-control'
  presets.unshift(item)
  try { uni.setStorageSync(PRESETS_KEY, { version: 1, presets: presets.slice(0, 40) }) } catch (e) {}
  return clone(item)
}

function controlFromPreset(preset, position) {
  const control = normalizeControl(clone(preset && preset.control), 0)
  control.id = uid('control')
  control.x = number(position && position.x, 2, 98, 50)
  control.y = number(position && position.y, 3, 97, 50)
  return control
}

function createLayout(data, name, sourceLayout) {
  const normalized = normalizeLayouts(data)
  const source = sourceLayout || normalized.layouts.find(function(item) { return item.id === normalized.activeLayoutId })
  const layout = source ? clone(source) : { controls: [], background: { id: 'mobile-light' }, canvas: { width: 2400, height: 1080 } }
  layout.id = uid('layout')
  layout.name = String(name || '自定义布局').slice(0, 48)
  layout.controls = (layout.controls || []).map(function(item, index) { const control = normalizeControl(item, index); control.id = uid('control'); return control })
  normalized.layouts.push(layout)
  normalized.activeLayoutId = layout.id
  return normalized
}

export {
  SKINS, SHAPES, BEHAVIORS, clone, normalizeControl, normalizeLayouts,
  loadLayouts, saveLayouts, pendingLayouts, clearPendingLayouts,
  loadPresets, savePreset, controlFromPreset, createLayout,
}
