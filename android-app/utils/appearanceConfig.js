export const APPEARANCE_STORAGE_KEY = 'phonekb.appearance.v1'
export const APPEARANCE_UPDATED_EVENT = 'phonekb:appearance-updated'

export const PAGE_OPTIONS = [
  { id: 'panel', label: '控制面板', route: 'pages/panel/panel' },
  { id: 'layout', label: '布局', route: 'pages/layout/layout' },
  { id: 'edit-key', label: '按键编辑', route: 'pages/layout/edit-key' },
  { id: 'codex-micro-edit', label: 'Codex Micro 编辑', route: 'pages/codex-micro-edit/codex-micro-edit' },
  { id: 'layouts', label: '面板布局', route: 'pages/layouts/layouts' },
  { id: 'devices', label: '设备', route: 'pages/devices/devices' },
  { id: 'settings', label: '设置', route: 'pages/settings/settings' },
  { id: 'templates', label: '模板', route: 'pages/templates/templates' },
  { id: 'touchpad', label: '触摸板', route: 'pages/touchpad/touchpad' },
  { id: 'about', label: '关于', route: 'pages/about/about' },
  { id: 'profile', label: '我的', route: 'pages/profile/profile' },
  { id: 'widgets-manage', label: '组件管理', route: 'pages/widgets-manage/widgets-manage' },
  { id: 'widgets-edit', label: '组件编辑', route: 'pages/widgets-edit/widgets-edit' },
  { id: 'panel-scheme', label: '面板方案', route: 'pages/panel-scheme/panel-scheme' },
  { id: 'tab-config', label: 'Tab 配置', route: 'pages/tab-config/tab-config' },
  { id: 'bt-settings', label: '蓝牙设置', route: 'pages/bt-settings/bt-settings' },
]

export const BUILTIN_BACKGROUNDS = [
  {
    id: 'mist',
    label: '雾蓝',
    background: 'radial-gradient(90% 65% at 10% 0%, rgba(255,255,255,0.72) 0%, transparent 60%), linear-gradient(155deg, #8BB6D8 0%, #DCE9F0 54%, #7B9DB7 100%)',
  },
  {
    id: 'forest',
    label: '林雾',
    background: 'radial-gradient(80% 60% at 72% 16%, rgba(205,232,215,0.42) 0%, transparent 66%), linear-gradient(160deg, #274C3B 0%, #76947C 46%, #D7E1DA 100%)',
  },
  {
    id: 'graphite',
    label: '石墨',
    background: 'radial-gradient(70% 55% at 22% 0%, rgba(255,255,255,0.18) 0%, transparent 62%), linear-gradient(145deg, #202A31 0%, #56646D 52%, #A7B0B5 100%)',
  },
  {
    id: 'cloud',
    label: '云层',
    background: 'radial-gradient(65% 40% at 20% 24%, rgba(255,255,255,0.9) 0%, transparent 64%), radial-gradient(80% 55% at 78% 64%, rgba(255,255,255,0.65) 0%, transparent 68%), linear-gradient(180deg, #83B5DF 0%, #D6E6F3 100%)',
  },
]

export const COLOR_BACKGROUNDS = ['#F4F8FD', '#EEF2F3', '#E8F1EC', '#F3EEF5', '#20272C', '#101416']

const PAGE_IDS = PAGE_OPTIONS.reduce(function (out, page) {
  out[page.id] = true
  return out
}, {})

const ROUTE_TO_PAGE = PAGE_OPTIONS.reduce(function (out, page) {
  out[page.route] = page.id
  return out
}, {
  'pages/appearance/appearance': 'settings',
  'pages/gamepad/gamepad': 'gamepad-shell',
  'pages/full-keyboard/full-keyboard': 'panel',
  'pages/index/index': 'onboarding',
  'pages/activate/activate': 'onboarding',
})

export const DEFAULT_APPEARANCE = Object.freeze({
  version: 1,
  mode: 'light',
  pages: {},
})

const LIGHT_PALETTE = {
  background: '#F4F8FD',
  backgroundAlt: '#EDF3FA',
  surfaceRgb: '255,255,255',
  surfaceStrongRgb: '255,255,255',
  text: '#172033',
  textMid: '#607087',
  textLight: '#94A0B1',
  disabled: '#B7C0CC',
  border: '#DCE6F1',
  divider: 'rgba(89,113,141,0.12)',
  primary: '#2F78F6',
  primaryBg: '#EAF3FF',
  accent: '#8764B8',
  success: '#107C10',
  warning: '#CA5010',
  danger: '#D13438',
  successSurface: '#EFFAF5',
  warningSurface: '#FFF9E9',
  dangerSurface: '#FFF0F1',
}

const DARK_PALETTE = {
  background: '#101518',
  backgroundAlt: '#182025',
  surfaceRgb: '29,38,43',
  surfaceStrongRgb: '36,47,53',
  text: '#ECF2F4',
  textMid: '#B1BEC4',
  textLight: '#87969D',
  disabled: '#65747B',
  border: '#3A4950',
  divider: 'rgba(226,238,242,0.11)',
  primary: '#69B5F2',
  primaryBg: 'rgba(105,181,242,0.16)',
  accent: '#BBA3E5',
  success: '#6ADFA0',
  warning: '#FFC766',
  danger: '#FF7B83',
  successSurface: '#17362A',
  warningSurface: '#3D3219',
  dangerSurface: '#3B2023',
}

function clamp(value, min, max) {
  const number = Number(value)
  if (!Number.isFinite(number)) return min
  return Math.max(min, Math.min(max, number))
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function sanitizeHex(value) {
  const text = String(value || '').trim().toUpperCase()
  return /^#[0-9A-F]{6}$/.test(text) ? text : '#F4F8FD'
}

function sanitizeBackground(value) {
  const input = value && typeof value === 'object' ? value : {}
  const allowedTypes = ['default', 'color', 'builtin', 'image']
  const type = allowedTypes.indexOf(input.type) >= 0 ? input.type : 'default'
  const output = {
    type: type,
    fit: input.fit === 'contain' ? 'contain' : 'cover',
    position: ['top', 'center', 'bottom'].indexOf(input.position) >= 0 ? input.position : 'center',
    dim: Math.round(clamp(input.dim, 0, 0.6) * 100) / 100,
  }
  if (type === 'color') output.color = sanitizeHex(input.color)
  if (type === 'builtin') {
    const exists = BUILTIN_BACKGROUNDS.some(function (item) { return item.id === input.builtinId })
    output.builtinId = exists ? input.builtinId : BUILTIN_BACKGROUNDS[0].id
  }
  if (type === 'image') output.source = typeof input.source === 'string' ? input.source : ''
  return output
}

export function sanitizePageAppearance(value) {
  const input = value && typeof value === 'object' ? value : {}
  return {
    background: sanitizeBackground(input.background),
    surfaceOpacity: Math.round(clamp(input.surfaceOpacity, 0.65, 1) * 100) / 100,
  }
}

export function normalizeAppearance(value) {
  const input = value && typeof value === 'object' ? value : {}
  const output = {
    version: 1,
    mode: ['light', 'dark', 'system'].indexOf(input.mode) >= 0 ? input.mode : 'light',
    pages: {},
  }
  const pages = input.pages && typeof input.pages === 'object' ? input.pages : {}
  Object.keys(pages).forEach(function (pageId) {
    if (PAGE_IDS[pageId]) output.pages[pageId] = sanitizePageAppearance(pages[pageId])
  })
  return output
}

function runtimeStorage() {
  if (typeof uni === 'undefined') return null
  return {
    get: function (key) { return uni.getStorageSync(key) },
    set: function (key, value) { return uni.setStorageSync(key, value) },
    remove: function (key) { return uni.removeStorageSync(key) },
  }
}

export function loadAppearance(storage) {
  const store = storage || runtimeStorage()
  if (!store) return clone(DEFAULT_APPEARANCE)
  try {
    const value = typeof store.get === 'function' ? store.get(APPEARANCE_STORAGE_KEY) : null
    return normalizeAppearance(value)
  } catch (error) {
    console.warn('[appearance] load failed', error)
    return clone(DEFAULT_APPEARANCE)
  }
}

export function saveAppearance(value, storage) {
  const normalized = normalizeAppearance(value)
  const store = storage || runtimeStorage()
  if (!store) return normalized
  try {
    if (typeof store.set === 'function') store.set(APPEARANCE_STORAGE_KEY, normalized)
    if (typeof uni !== 'undefined' && uni.$emit) uni.$emit(APPEARANCE_UPDATED_EVENT, clone(normalized))
  } catch (error) {
    console.warn('[appearance] save failed', error)
  }
  return normalized
}

export function updateAppearanceMode(mode, storage) {
  const config = loadAppearance(storage)
  config.mode = ['light', 'dark', 'system'].indexOf(mode) >= 0 ? mode : 'light'
  return saveAppearance(config, storage)
}

export function updatePageAppearance(pageId, value, storage) {
  if (!PAGE_IDS[pageId]) return loadAppearance(storage)
  const config = loadAppearance(storage)
  config.pages[pageId] = sanitizePageAppearance(value)
  return saveAppearance(config, storage)
}

export function updatePageAppearances(pageIds, value, storage) {
  const ids = Array.isArray(pageIds) ? pageIds : []
  const config = loadAppearance(storage)
  const appearance = sanitizePageAppearance(value)
  let updated = false
  ids.forEach(function (pageId) {
    if (!PAGE_IDS[pageId]) return
    config.pages[pageId] = clone(appearance)
    updated = true
  })
  return updated ? saveAppearance(config, storage) : config
}

export function resetPageAppearance(pageId, storage) {
  const config = loadAppearance(storage)
  delete config.pages[pageId]
  return saveAppearance(config, storage)
}

export function resetPageAppearances(pageIds, storage) {
  const ids = Array.isArray(pageIds) ? pageIds : []
  const config = loadAppearance(storage)
  let updated = false
  ids.forEach(function (pageId) {
    if (!PAGE_IDS[pageId] || !config.pages[pageId]) return
    delete config.pages[pageId]
    updated = true
  })
  return updated ? saveAppearance(config, storage) : config
}

export function resetAllPageAppearances(storage) {
  const config = loadAppearance(storage)
  config.pages = {}
  return saveAppearance(config, storage)
}

export function routeToPageId(route) {
  return ROUTE_TO_PAGE[String(route || '').replace(/^\//, '')] || ''
}

export function resolveEffectiveMode(mode, systemTheme) {
  if (mode === 'dark') return 'dark'
  if (mode === 'system') return String(systemTheme || '').toLowerCase() === 'dark' ? 'dark' : 'light'
  return 'light'
}

export function getSystemTheme() {
  try {
    if (typeof uni !== 'undefined' && typeof uni.getAppBaseInfo === 'function') {
      const info = uni.getAppBaseInfo()
      if (info && info.theme) return info.theme
    }
  } catch (error) {}
  try {
    if (typeof plus !== 'undefined' && plus.navigator && typeof plus.navigator.getUIStyle === 'function') {
      return plus.navigator.getUIStyle()
    }
  } catch (error) {}
  try {
    if (typeof uni !== 'undefined') {
      const info = uni.getSystemInfoSync()
      if (info && info.theme) return info.theme
    }
  } catch (error) {}
  return 'light'
}

function localImageUrl(source) {
  let value = String(source || '')
  try {
    if (typeof plus !== 'undefined' && plus.io && typeof plus.io.convertLocalFileSystemURL === 'function') {
      value = plus.io.convertLocalFileSystemURL(value)
    }
  } catch (error) {}
  return value.replace(/\\/g, '/').replace(/"/g, '%22')
}

function backgroundStyle(background) {
  if (!background || background.type === 'default') {
    return { custom: false, color: '', image: '', size: 'cover', position: 'center' }
  }
  if (background.type === 'color') {
    return { custom: true, color: background.color, image: 'none', size: 'cover', position: 'center' }
  }
  if (background.type === 'builtin') {
    const preset = BUILTIN_BACKGROUNDS.find(function (item) { return item.id === background.builtinId }) || BUILTIN_BACKGROUNDS[0]
    return { custom: true, color: '#DCE6EC', image: preset.background, size: 'cover', position: 'center' }
  }
  if (background.type === 'image' && background.source) {
    return {
      custom: true,
      color: '#1C252A',
      image: 'linear-gradient(rgba(0,0,0,' + background.dim + '), rgba(0,0,0,' + background.dim + ')), url("' + localImageUrl(background.source) + '")',
      size: background.fit,
      position: background.position,
    }
  }
  return { custom: false, color: '', image: '', size: 'cover', position: 'center' }
}

export function buildAppearanceState(configValue, pageId, systemTheme) {
  const config = normalizeAppearance(configValue)
  const mode = resolveEffectiveMode(config.mode, systemTheme)
  const palette = mode === 'dark' ? DARK_PALETTE : LIGHT_PALETTE
  const hasOverride = !!config.pages[pageId]
  const page = hasOverride ? sanitizePageAppearance(config.pages[pageId]) : {
    background: sanitizeBackground({ type: 'default' }),
    surfaceOpacity: 1,
  }
  const background = backgroundStyle(page.background)
  const alpha = page.surfaceOpacity
  const strongAlpha = Math.max(0.9, alpha)
  return {
    mode: mode,
    hasOverride: hasOverride,
    hasCustomBackground: background.custom,
    page: page,
    variables: {
      '--app-page-bg-color': background.custom ? background.color : palette.background,
      '--app-page-bg-image': background.custom ? background.image : 'radial-gradient(90% 44% at 8% 0%, rgba(47,120,246,0.10) 0%, rgba(244,248,253,0) 72%)',
      '--app-page-bg-size': background.size,
      '--app-page-bg-position': background.position,
      '--app-surface': 'rgba(' + palette.surfaceRgb + ',' + alpha + ')',
      '--app-surface-strong': 'rgba(' + palette.surfaceStrongRgb + ',' + strongAlpha + ')',
      '--app-surface-alpha': String(alpha),
      '--app-color-bg': background.custom ? 'transparent' : palette.background,
      '--app-color-bg-alt': palette.backgroundAlt,
      '--app-color-card': 'rgba(' + palette.surfaceRgb + ',' + alpha + ')',
      '--app-color-text': palette.text,
      '--app-color-text-mid': palette.textMid,
      '--app-color-text-light': palette.textLight,
      '--app-color-disabled': palette.disabled,
      '--app-color-border': palette.border,
      '--app-color-divider': palette.divider,
      '--app-color-primary': palette.primary,
      '--app-color-primary-bg': palette.primaryBg,
      '--app-success-surface': palette.successSurface,
      '--app-warning-surface': palette.warningSurface,
      '--app-danger-surface': palette.dangerSurface,
      '--color-primary': palette.primary,
      '--color-primary-bg': palette.primaryBg,
      '--color-accent': palette.accent,
      '--color-success': palette.success,
      '--color-warning': palette.warning,
      '--color-danger': palette.danger,
      '--color-text': palette.text,
      '--color-text-mid': palette.textMid,
      '--color-text-light': palette.textLight,
      '--color-text-disabled': palette.disabled,
      '--color-bg': background.custom ? 'transparent' : palette.background,
      '--color-bg-alt': palette.backgroundAlt,
      '--color-card': 'rgba(' + palette.surfaceRgb + ',' + alpha + ')',
      '--color-card-acrylic': 'rgba(' + palette.surfaceRgb + ',' + alpha + ')',
      '--color-card-mica': 'rgba(' + palette.surfaceStrongRgb + ',' + strongAlpha + ')',
      '--color-divider': palette.divider,
      '--color-divider-strong': palette.divider,
      '--color-border': palette.border,
      '--fluent-acrylic-strong': 'rgba(' + palette.surfaceStrongRgb + ',' + strongAlpha + ')',
      '--fluent-acrylic-thin': 'rgba(' + palette.surfaceRgb + ',' + alpha + ')',
      '--fluent-mica-deep': 'rgba(' + palette.surfaceStrongRgb + ',' + strongAlpha + ')',
      '--fluent-hairline': palette.divider,
    },
  }
}

function setDocumentClass(root, name, enabled) {
  if (!root || !root.classList) return
  if (enabled) root.classList.add(name)
  else root.classList.remove(name)
}

export function applyAppearance(pageId, configValue) {
  const config = configValue ? normalizeAppearance(configValue) : loadAppearance()
  const state = buildAppearanceState(config, pageId, getSystemTheme())
  try {
    if (typeof document !== 'undefined' && document.documentElement) {
      const root = document.documentElement
      Object.keys(state.variables).forEach(function (key) {
        root.style.setProperty(key, state.variables[key])
      })
      setDocumentClass(root, 'app-dark', state.mode === 'dark')
      setDocumentClass(root, 'app-light', state.mode !== 'dark')
      setDocumentClass(root, 'app-appearance-active', state.mode === 'dark' || state.hasOverride)
      setDocumentClass(root, 'app-has-custom-background', state.hasCustomBackground)
    }
  } catch (error) {
    console.warn('[appearance] apply document failed', error)
  }
  try {
    if (typeof plus !== 'undefined' && plus.navigator) {
      if (typeof plus.navigator.setStatusBarStyle === 'function') plus.navigator.setStatusBarStyle(state.mode === 'dark' ? 'light' : 'dark')
      if (typeof plus.navigator.setStatusBarBackground === 'function') plus.navigator.setStatusBarBackground(state.hasCustomBackground ? 'rgba(0,0,0,0)' : state.variables['--app-page-bg-color'])
    }
  } catch (error) {}
  return state
}

export function currentPageId() {
  try {
    if (typeof getCurrentPages === 'function') {
      const pages = getCurrentPages()
      const current = pages && pages[pages.length - 1]
      return routeToPageId(current && current.route)
    }
  } catch (error) {}
  return ''
}

export function applyCurrentPageAppearance() {
  const pageId = currentPageId()
  return applyAppearance(pageId || 'onboarding')
}

export function installAppearanceRuntime() {
  try {
    if (typeof uni !== 'undefined' && uni.$on) {
      uni.$off && uni.$off(APPEARANCE_UPDATED_EVENT)
      uni.$on(APPEARANCE_UPDATED_EVENT, function () { applyCurrentPageAppearance() })
    }
    if (typeof uni !== 'undefined' && typeof uni.onThemeChange === 'function') {
      uni.onThemeChange(function () {
        if (loadAppearance().mode === 'system') applyCurrentPageAppearance()
      })
    }
  } catch (error) {}
  setTimeout(function () { applyCurrentPageAppearance() }, 0)
}

export function persistBackgroundImage(tempPath) {
  return new Promise(function (resolve, reject) {
    if (typeof uni === 'undefined' || typeof uni.saveFile !== 'function') {
      reject(new Error('当前平台不支持保存背景图'))
      return
    }
    uni.saveFile({
      tempFilePath: tempPath,
      success: function (result) { resolve(result.savedFilePath || tempPath) },
      fail: function (error) { reject(error || new Error('保存背景图失败')) },
    })
  })
}

export function removePersistedBackground(filePath) {
  if (!filePath || typeof uni === 'undefined' || typeof uni.removeSavedFile !== 'function') return
  try { uni.removeSavedFile({ filePath: filePath }) } catch (error) {}
}
