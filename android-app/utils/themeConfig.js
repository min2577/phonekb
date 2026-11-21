/**
 * themeConfig.js - 主题(皮肤)系统
 *
 * 8 套主题,每套调性独立:
 *   1. fluent    Microsoft Fluent 蓝(默认)
 *   2. sunset    暖黄昏 / 落日橙
 *   3. forest    森林 / 自然深绿
 *   4. midnight  深紫 / 神秘暗调
 *   5. mono      极简黑白灰
 *   6. dark      深色模式 / 暗光护眼
 *   7. matcha    抹茶 / 浅黄绿清新
 *   8. ocean     海洋 / 深青蓝科技
 *
 * 存储:
 *   key = phonekb.theme.current
 *   value = theme id (string)
 *
 * 字段约定(每个 theme):
 *   id        string  唯一 id
 *   name      string  显示名
 *   emoji     string  装饰图标
 *   style     string  调性描述
 *   vars      object  CSS 变量覆盖(键名同 App.vue 中的变量名)
 */

export const THEME_STORAGE_KEY = 'phonekb.theme.current'

export const DEFAULT_THEME_ID = 'fluent'

export const THEMES = [
  {
    id: 'fluent',
    name: 'Fluent',
    emoji: '🅵',
    style: '微软 Fluent 蓝 / 默认',
    vars: {
      '--color-primary':         '#2F78F6',
      '--color-primary-hover':   '#2469DC',
      '--color-primary-press':   '#1E58BD',
      '--color-primary-bg':      '#EAF3FF',
      '--color-primary-subtle':  '#DCEBFF',
      '--color-primary-light':   '#60A5FA',
      '--color-primary-dark':    '#2563EB',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#8764B8',
      '--color-accent-bg':       '#F3F0FA',
      '--color-success':         '#107C10',
      '--color-success-bg':      '#DFF6DD',
      '--color-warning':         '#CA5010',
      '--color-warning-bg':      '#FFF4CE',
      '--color-danger':          '#D13438',
      '--color-danger-bg':       '#FDE7E9',
      '--color-text':            '#172033',
      '--color-text-mid':        '#607087',
      '--color-text-light':      '#94A0B1',
      '--color-text-disabled':   '#B7C0CC',
      '--color-bg':              '#F4F8FD',
      '--color-bg-alt':          '#EDF3FA',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(255,255,255,0.88)',
      '--color-card-mica':       '#F8FAFD',
      '--color-divider':         'rgba(89,113,141,0.10)',
      '--color-divider-strong':  'rgba(89,113,141,0.16)',
      '--color-border':          '#DCE6F1',
    },
  },

  {
    id: 'sunset',
    name: '暖黄昏',
    emoji: '🌅',
    style: '落日橙 / 暖意',
    vars: {
      '--color-primary':         '#E85D04',
      '--color-primary-hover':   '#DC4D04',
      '--color-primary-press':   '#B53600',
      '--color-primary-bg':      '#FFEDD8',
      '--color-primary-subtle':  '#FFE2C2',
      '--color-primary-light':   '#F48C06',
      '--color-primary-dark':    '#9D0208',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#F48C06',
      '--color-accent-bg':       '#FFF1DD',
      '--color-success':         '#2A9D8F',
      '--color-success-bg':      '#D8F3EC',
      '--color-warning':         '#F77F00',
      '--color-warning-bg':      '#FFEBC4',
      '--color-danger':          '#D62828',
      '--color-danger-bg':       '#FDE0E0',
      '--color-text':            '#2D1B0E',
      '--color-text-mid':        '#6B4423',
      '--color-text-light':      '#A0826D',
      '--color-text-disabled':   '#C9B8A8',
      '--color-bg':              '#FFF8F3',
      '--color-bg-alt':          '#FBEFE2',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(255,250,245,0.7)',
      '--color-card-mica':       '#FAEEDD',
      '--color-divider':         'rgba(232,93,4,0.08)',
      '--color-divider-strong':  'rgba(232,93,4,0.12)',
      '--color-border':          '#F2D6BA',
    },
  },

  {
    id: 'forest',
    name: '森林',
    emoji: '🌲',
    style: '自然深绿 / 清新',
    vars: {
      '--color-primary':         '#2D6A4F',
      '--color-primary-hover':   '#1B4332',
      '--color-primary-press':   '#0E2A1E',
      '--color-primary-bg':      '#D8F3DC',
      '--color-primary-subtle':  '#B7E4C7',
      '--color-primary-light':   '#52B788',
      '--color-primary-dark':    '#1B4332',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#95D5B2',
      '--color-accent-bg':       '#E6F4EA',
      '--color-success':         '#2D6A4F',
      '--color-success-bg':      '#D8F3DC',
      '--color-warning':         '#CA8A04',
      '--color-warning-bg':      '#FEF3C7',
      '--color-danger':          '#9F1239',
      '--color-danger-bg':       '#FFE4E6',
      '--color-text':            '#1B2E25',
      '--color-text-mid':        '#3A5A40',
      '--color-text-light':      '#7A8B7F',
      '--color-text-disabled':   '#A8B5AE',
      '--color-bg':              '#F5FBF7',
      '--color-bg-alt':          '#E9F4EC',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(245,251,247,0.7)',
      '--color-card-mica':       '#E9F4EC',
      '--color-divider':         'rgba(45,106,79,0.08)',
      '--color-divider-strong':  'rgba(45,106,79,0.12)',
      '--color-border':          '#C7DFD0',
    },
  },

  {
    id: 'midnight',
    name: '深紫',
    emoji: '🌌',
    style: '紫罗兰 / 神秘',
    vars: {
      '--color-primary':         '#7B2CBF',
      '--color-primary-hover':   '#5A189A',
      '--color-primary-press':   '#3C096C',
      '--color-primary-bg':      '#F3E8FF',
      '--color-primary-subtle':  '#E0C3FC',
      '--color-primary-light':   '#C77DFF',
      '--color-primary-dark':    '#5A189A',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#C77DFF',
      '--color-accent-bg':       '#F3E8FF',
      '--color-success':         '#06D6A0',
      '--color-success-bg':      '#D0F4E6',
      '--color-warning':         '#FFB703',
      '--color-warning-bg':      '#FFF1CC',
      '--color-danger':          '#E63946',
      '--color-danger-bg':       '#FFE0E3',
      '--color-text':            '#240046',
      '--color-text-mid':        '#5A189A',
      '--color-text-light':      '#9D8BB0',
      '--color-text-disabled':   '#C0B0CC',
      '--color-bg':              '#FAF6FF',
      '--color-bg-alt':          '#F0E7FA',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(250,246,255,0.7)',
      '--color-card-mica':       '#F0E7FA',
      '--color-divider':         'rgba(123,44,191,0.08)',
      '--color-divider-strong':  'rgba(123,44,191,0.12)',
      '--color-border':          '#E0C3FC',
    },
  },

  {
    id: 'mono',
    name: '极简',
    emoji: '◾',
    style: '黑白灰 / 极简',
    vars: {
      '--color-primary':         '#1C1C1C',
      '--color-primary-hover':   '#0A0A0A',
      '--color-primary-press':   '#000000',
      '--color-primary-bg':      '#F5F5F5',
      '--color-primary-subtle':  '#E8E8E8',
      '--color-primary-light':   '#888888',
      '--color-primary-dark':    '#000000',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#616161',
      '--color-accent-bg':       '#EEEEEE',
      '--color-success':         '#2E7D32',
      '--color-success-bg':      '#E8F5E9',
      '--color-warning':         '#ED6C02',
      '--color-warning-bg':      '#FFF7E6',
      '--color-danger':          '#D32F2F',
      '--color-danger-bg':       '#FFEBEE',
      '--color-text':            '#0A0A0A',
      '--color-text-mid':        '#424242',
      '--color-text-light':      '#757575',
      '--color-text-disabled':   '#BDBDBD',
      '--color-bg':              '#FFFFFF',
      '--color-bg-alt':          '#FAFAFA',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(255,255,255,0.85)',
      '--color-card-mica':       '#FAFAFA',
      '--color-divider':         'rgba(0,0,0,0.08)',
      '--color-divider-strong':  'rgba(0,0,0,0.12)',
      '--color-border':          '#E0E0E0',
    },
  },

  {
    id: 'dark',
    name: '深色',
    emoji: '🌙',
    style: '暗色模式 / 护眼',
    vars: {
      '--color-primary':         '#60A5FA',
      '--color-primary-hover':   '#93C5FD',
      '--color-primary-press':   '#3B82F6',
      '--color-primary-bg':      'rgba(96,165,250,0.12)',
      '--color-primary-subtle':  'rgba(96,165,250,0.08)',
      '--color-primary-light':   '#93C5FD',
      '--color-primary-dark':    '#2563EB',
      '--color-primary-on':      '#0B1220',
      '--color-accent':          '#A78BFA',
      '--color-accent-bg':       'rgba(167,139,250,0.14)',
      '--color-success':         '#34D399',
      '--color-success-bg':      'rgba(52,211,153,0.14)',
      '--color-warning':         '#FBBF24',
      '--color-warning-bg':      'rgba(251,191,36,0.14)',
      '--color-danger':          '#F87171',
      '--color-danger-bg':       'rgba(248,113,113,0.14)',
      '--color-text':            '#E5E7EB',
      '--color-text-mid':        '#9CA3AF',
      '--color-text-light':      '#6B7280',
      '--color-text-disabled':   '#4B5563',
      '--color-bg':              '#121212',
      '--color-bg-alt':          '#1A1A1A',
      '--color-card':            '#1E1E1E',
      '--color-card-acrylic':    'rgba(30,30,30,0.7)',
      '--color-card-mica':       '#1A1A1A',
      '--color-divider':         'rgba(255,255,255,0.06)',
      '--color-divider-strong':  'rgba(255,255,255,0.1)',
      '--color-border':          '#2A2A2A',
    },
  },

  {
    id: 'matcha',
    name: '抹茶',
    emoji: '🍵',
    style: '浅黄绿 / 清新',
    vars: {
      '--color-primary':         '#588157',
      '--color-primary-hover':   '#3A5A40',
      '--color-primary-press':   '#344E41',
      '--color-primary-bg':      '#E9F5DB',
      '--color-primary-subtle':  '#D8E5C5',
      '--color-primary-light':   '#A3B18A',
      '--color-primary-dark':    '#3A5A40',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#A3B18A',
      '--color-accent-bg':       '#E9F0DA',
      '--color-success':         '#588157',
      '--color-success-bg':      '#E9F5DB',
      '--color-warning':         '#DDA15E',
      '--color-warning-bg':      '#FAEDCD',
      '--color-danger':          '#BC4749',
      '--color-danger-bg':       '#F2D1D1',
      '--color-text':            '#283618',
      '--color-text-mid':        '#606C38',
      '--color-text-light':      '#8E9A6B',
      '--color-text-disabled':   '#B5BFA0',
      '--color-bg':              '#FEFAE0',
      '--color-bg-alt':          '#FAEDCD',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(254,250,224,0.7)',
      '--color-card-mica':       '#FAEDCD',
      '--color-divider':         'rgba(88,129,87,0.1)',
      '--color-divider-strong':  'rgba(88,129,87,0.15)',
      '--color-border':          '#DCD7B5',
    },
  },

  {
    id: 'ocean',
    name: '海洋',
    emoji: '🌊',
    style: '深青蓝 / 科技',
    vars: {
      '--color-primary':         '#0077B6',
      '--color-primary-hover':   '#023E8A',
      '--color-primary-press':   '#03045E',
      '--color-primary-bg':      '#CAF0F8',
      '--color-primary-subtle':  '#ADE8F4',
      '--color-primary-light':   '#00B4D8',
      '--color-primary-dark':    '#023E8A',
      '--color-primary-on':      '#FFFFFF',
      '--color-accent':          '#00B4D8',
      '--color-accent-bg':       '#CAF0F8',
      '--color-success':         '#06A77D',
      '--color-success-bg':      '#D0F4E6',
      '--color-warning':         '#FFB703',
      '--color-warning-bg':      '#FFF3CC',
      '--color-danger':          '#D62828',
      '--color-danger-bg':       '#FDE0E0',
      '--color-text':            '#03045E',
      '--color-text-mid':        '#023E8A',
      '--color-text-light':      '#5C7C92',
      '--color-text-disabled':   '#9BB1C2',
      '--color-bg':              '#F0F8FF',
      '--color-bg-alt':          '#E1F1FB',
      '--color-card':            '#FFFFFF',
      '--color-card-acrylic':    'rgba(240,248,255,0.7)',
      '--color-card-mica':       '#E1F1FB',
      '--color-divider':         'rgba(0,119,182,0.08)',
      '--color-divider-strong':  'rgba(0,119,182,0.12)',
      '--color-border':          '#B6DDEE',
    },
  },
]

// ===== CRUD =====

export function listThemes() {
  return THEMES.slice()
}

export function getTheme(id) {
  return THEMES.find(function (t) { return t.id === id }) || THEMES[0]
}

export function loadThemeId() {
  try {
    const id = uni.getStorageSync(THEME_STORAGE_KEY)
    if (id && typeof id === 'string' && getTheme(id)) return id
  } catch (e) {}
  return DEFAULT_THEME_ID
}

export function saveThemeId(id) {
  if (!getTheme(id)) return false
  try {
    uni.setStorageSync(THEME_STORAGE_KEY, id)
    return true
  } catch (e) {
    return false
  }
}

// ===== 应用到 DOM =====
// 把主题的 vars 应用到 rootElement(默认是 document.documentElement,在 nvue 下退化到 body)
// 同时返回 inline style 字符串,方便在 <view :style="..."> 上直接使用
export function applyTheme(theme, rootElement) {
  const vars = (theme && theme.vars) || {}
  // 应用到 rootElement(若提供)
  if (rootElement && rootElement.style && typeof rootElement.style.setProperty === 'function') {
    Object.keys(vars).forEach(function (k) {
      try { rootElement.style.setProperty(k, vars[k]) } catch (e) {}
    })
  }
  // 返回 inline style 对象(供 Vue :style 绑定)
  return vars
}

// 应用到当前 documentElement + 返回 inline style
export function applyThemeToDocument(theme) {
  let root = null
  try {
    if (typeof document !== 'undefined' && document && document.documentElement) {
      root = document.documentElement
    } else if (typeof document !== 'undefined' && document && document.body) {
      root = document.body
    }
  } catch (e) {}
  return applyTheme(theme, root)
}

// 清除已应用的主题(还原到默认)
export function clearAppliedTheme(theme, rootElement) {
  if (rootElement && rootElement.style && typeof rootElement.style.removeProperty === 'function') {
    const vars = (theme && theme.vars) || {}
    Object.keys(vars).forEach(function (k) {
      try { rootElement.style.removeProperty(k) } catch (e) {}
    })
  }
}
