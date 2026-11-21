/**
 * tabConfig.js - 底部 Tab 栏的"加载 + 清理 + 保存"工具
 *
 * 历史教训:
 *   CustomTabBar 和 tab-config.vue 都依赖 phonekb.tab.config 这个存储。
 *   如果只在 tab-config.vue 里做 dedup / 修正,首页(用 CustomTabBar)
 *   就会显示原始脏数据(id 重复 / label-icon-page 错乱)。
 *   把读 / 写 / 清理都集中到这里,两边共用同一份逻辑。
 */

export const TAB_STORAGE_KEY = 'phonekb.tab.config'
export const TAB_UPDATED_EVENT = 'phonekb.tab.updated' // uni.$emit 广播
const DEVICE_TAB_MIGRATION_KEY = 'phonekb.tab.device_auto_removed.v1'

export const MAX_TABS = 6

export const DEFAULT_TABS = [
  { id: 'p-panel',   page: 'panel',   label: '\u9762\u677f',     icon: '\uD83C\uDF9B', enabled: true, order: 0, built_in: false },
  { id: 'p-layout',  page: 'layout',  label: '\u5E03\u5C40',     icon: '\uD83D\uDCCF', enabled: true, order: 1, built_in: false },
  { id: 'p-profile', page: 'profile', label: '\u6211\u7684',     icon: '\uD83D\uDC64', enabled: true, order: 2, built_in: true  },
]

export const ALL_OPTIONS = [
  { key: 'w-key-grid',      group: 'app',   title: '\u5FEB\u6377\u952E',   icon: '\u26A1', description: '4\u00D74 \u6309\u952E\u7F51\u683C',    page: 'panel', widgetType: 'key-grid' },
  { key: 'w-text-input',    group: 'app',   title: '\u6587\u5B57\u8F93\u5165', icon: '\u2328', description: '\u8F93\u5165\u6846 + \u53D1\u9001',    page: 'panel', widgetType: 'text-input' },
  { key: 'w-mouse-control', group: 'app',   title: '\u9F20\u6807\u63A7\u5236', icon: '\uD83D\uDDB1', description: '\u89E6\u6478\u677F + \u64CD\u4F5C',    page: 'panel', widgetType: 'mouse-control' },
  { key: 'w-volume',        group: 'app',   title: '\u97F3\u91CF\u63A7\u5236', icon: '\uD83D\uDD0A', description: '\u97F3\u91CF\u589E\u51CF + \u9759\u97F3',  page: 'panel', widgetType: 'volume-control' },
  { key: 'p-panel',         group: 'other', title: '\u9762\u677f',     icon: '\uD83C\uDF9B', description: '\u7EC4\u4EF6\u5316\u63A7\u5236\u9762\u677f',   page: 'panel',   built_in: false },
  { key: 'p-layout',        group: 'other', title: '\u5E03\u5C40',     icon: '\uD83D\uDCCF', description: '\u952E\u4F4D\u7F51\u683C\u7F16\u8F91',     page: 'layout',  built_in: false },
  { key: 'p-profile',       group: 'other', title: '\u6211\u7684',     icon: '\uD83D\uDC64', description: '\u4E2A\u4EBA\u4E2D\u5FC3',         page: 'profile', built_in: true  },
  { key: 'p-devices',       group: 'other', title: '\u6211\u7684\u8BBE\u5907', icon: '\uD83D\uDCF1', description: '\u5DF2\u8FDE\u63A5\u8BBE\u5907\u7BA1\u7406',   page: 'devices' },
]

/**
 * \u8BFB\u53D6\u5E76\u6E05\u7406 storage \u91CC\u7684 tab \u914D\u7F6E\u3002
 * \r
 * \u6E05\u7406\u9879:\r
 *   1) dedup \u2014\u2014 \u540C id \u53EA\u4FDD\u7559\u7B2C\u4E00\u6761(\u9632\u6B62\u5E95\u90E8 tab \u51FA\u73B0\u4E24\u4E2A\u4E00\u6837\u7684\u201C\u6211\u7684\u8BBE\u5907\u201D)\r
 *   2) p-profile \u8FC1\u79FB \u2014\u2014 \u4EFB\u4F55 id === 'p-profile' \u7684\u6761\u76EE\u5F3A\u5236 label/icon/page \u4E3A\u6B63\u786E\u503C\r
 *      (\u4E0D\u8986\u76D6 built_in,\u5C0A\u91CD DEFAULT_TABS / ALL_OPTIONS \u91CC\u7684\u8BBE\u7F6E)\r
 */
export function loadTabs() {
  let cached = null
  let removeLegacyDeviceTab = false
  try {
    cached = uni.getStorageSync(TAB_STORAGE_KEY)
    removeLegacyDeviceTab = !uni.getStorageSync(DEVICE_TAB_MIGRATION_KEY)
  } catch (e) {}

  if (!Array.isArray(cached) || cached.length === 0) {
    try { uni.setStorageSync(DEVICE_TAB_MIGRATION_KEY, true) } catch (e) {}
    return DEFAULT_TABS.map(function (t) { return Object.assign({}, t) })
  }

  const optMap = {}
  ALL_OPTIONS.forEach(function (o) { optMap[o.key] = o })

  const seen = {}
  const out = []
  for (let i = 0; i < cached.length; i++) {
    const t = cached[i]
    const id = t && t.id
    if (!id || seen[id]) continue
    if (removeLegacyDeviceTab && id === 'p-devices') continue
    seen[id] = true
    const opt = optMap[id]
    out.push({
      id: id,
      page: (t && t.page) || 'panel',
      label: (t && t.label) || '',
      icon: (t && t.icon) || '\u25C7',
      enabled: !t || t.enabled !== false,
      order: typeof (t && t.order) === 'number' ? t.order : out.length,
      built_in: !!(opt && opt.built_in),
      widgetType: (t && t.widgetType) || (opt && opt.widgetType) || '',
      layoutId: (t && t.layoutId) || '',
    })
  }

  // p-profile \u8FC1\u79FB:label/icon/page \u5F3A\u5236\u6B63\u786E\r
  for (let k = 0; k < out.length; k++) {
    if (out[k].id === 'p-profile') {
      out[k].label = '\u6211\u7684'
      out[k].icon = '\uD83D\uDC64'
      out[k].page = 'profile'
    }
  }

  if (removeLegacyDeviceTab) {
    try {
      uni.setStorageSync(TAB_STORAGE_KEY, out)
      uni.setStorageSync(DEVICE_TAB_MIGRATION_KEY, true)
    } catch (e) {}
  }

  return out
}

/** \u5199\u5165 storage + \u5E7F\u64AD\u901A\u77E5(\u8BA9 CustomTabBar \u7B49\u7BA1\u8005\u5373\u65F6\u5237\u65B0) */
export function saveTabs(tabs) {
  try {
    uni.setStorageSync(TAB_STORAGE_KEY, tabs)
    // \u7528 JSON \u6DF1\u62F7\u8D1D\u540E\u518D emit\uFF0C\u907F\u514D Vue \u54CD\u5E94\u5F0F proxy \u8DE8\u7EC4\u4EF6\u4F20\u9012\u540E\u88AB\u56DE\u6536/\u5931\u6548\r
    // \uFF08\u539F\u8C03\u7528\u8005\u9875\u9762\u88AB\u9500\u6BC1\u540E\uFF0C\u539F\u6570\u636E proxy \u53EF\u80FD\u88AB\u91CA\u653E\uFF0CCustomTabBar \u8BBE\u4E0A\u53BB\u7684\u662F\u201C\u5783\u573E\u201D\uFF09
    try {
      const plain = JSON.parse(JSON.stringify(tabs || []))
      uni.$emit && uni.$emit(TAB_UPDATED_EVENT, plain)
    } catch (e) {
      try { uni.$emit && uni.$emit(TAB_UPDATED_EVENT, tabs) } catch (e2) {}
    }
    return true
  } catch (e) {
    return false
  }
}

/** \u67E5\u627E\u9009\u9879(\u7ED9\u201C\u6DFB\u52A0\u9009\u9879\u5361\u201D\u7528) */
export function findOption(key) {
  for (let i = 0; i < ALL_OPTIONS.length; i++) {
    if (ALL_OPTIONS[i].key === key) return ALL_OPTIONS[i]
  }
  return null
}

/** \u5DF2\u542F\u7528\u7684 tabs(\u8FC7\u6EE4 enabled,\u6309 order \u6392\u5E8F) */
export function enabledTabs(tabs) {
  return (tabs || [])
    .filter(function (t) { return t && t.enabled !== false })
    .slice()
    .sort(function (a, b) { return (a.order || 0) - (b.order || 0) })
}

/** 同步绑定到具体面板的 Tab：跟随重命名，并清理已删除面板的入口。 */
export function syncLayoutTabs(tabs, layouts) {
  const layoutMap = {}
  ;(layouts || []).forEach(function (layout) {
    if (layout && layout.id) layoutMap[layout.id] = layout
  })
  return (tabs || []).filter(function (tab) {
    return !tab || !tab.layoutId || !!layoutMap[tab.layoutId]
  }).map(function (tab) {
    if (!tab || !tab.layoutId) return tab
    const layout = layoutMap[tab.layoutId]
    return Object.assign({}, tab, { label: layout.name, icon: '▣' })
  })
}

/** \u52A0\u5165\u9009\u9879\u5230 tabs(\u4FDD\u8BC1\u4E0D\u91CD\u590D) */
export function pickAddOption(tabs, opt) {
  if (!opt || !opt.key) return { tabs: tabs, added: 0 }
  const arr = (tabs || []).slice()
  // \u68C0\u67E5\u662F\u5426\u5DF2\u5B58\u5728(\r
  const exists = arr.some(function (t) { return t && t.id === opt.key && t.enabled !== false })
  if (exists) return { tabs: tabs, added: 0 }
  const maxOrder = arr.reduce(function (m, t) { return Math.max(m, (t && t.order) || 0) }, -1)
  arr.push({
    id: opt.key,
    page: opt.page || 'panel',
    label: opt.title || '',
    icon: opt.icon || '\u25C7',
    enabled: true,
    order: maxOrder + 1,
    built_in: !!opt.built_in,
    widgetType: opt.widgetType || '',
    layoutId: opt.layoutId || '',
  })
  return { tabs: arr, added: 1 }
}

/** \u5220\u9664/\u9690\u85CF\u4E00\u4E2A tab(\u8BBE enabled=false,\u4FDD\u7559\u5728\u6570\u7EC4\u4E2D\u4EE5\u4FDD\u7559 order \u4FE1\u606F) */
export function removeTab(tabs, id) {
  return (tabs || []).map(function (t) {
    if (t && t.id === id) return Object.assign({}, t, { enabled: false })
    return t
  })
}

/** \u91CD\u6392\u5E8F: \u7ED9\u51FA\u65B0\u987A\u5E8F\u7684 id \u6570\u7EC4,\u91CD\u65B0\u5199 order \u5B57\u6BB5 */
export function reorderTabs(tabs, orderedIds) {
  const map = {}
  orderedIds.forEach(function (id, i) { map[id] = i })
  return (tabs || []).map(function (t) {
    if (t && map.hasOwnProperty(t.id)) {
      return Object.assign({}, t, { order: map[t.id], enabled: true })
    }
    return t
  })
}

/** \u91CD\u7F6E\u4E3A\u9ED8\u8BA4 3 tab(\u9762\u677F / \u5E03\u5C40 / \u6211\u7684) */
export function resetTabsToDefault() {
  return DEFAULT_TABS.map(function (t) { return Object.assign({}, t) })
}

/** \u8BA1\u7B97 sheet \u5361\u7247\u5C3A\u5BF8(\u6BCF\u9694\u591A\u5C11\u770B\u5230\u591A\u5C11\u4E2A) */
const SCREEN_RPX = 750
const SHEET_HORIZ_PADDING_RPX = 48
const CARD_GAP_RPX = 16
export function calcCardSize(count) {
  const avail = SCREEN_RPX - SHEET_HORIZ_PADDING_RPX
  const fit5 = Math.floor((avail - CARD_GAP_RPX * 4) / 5)
  const fit6 = Math.floor((avail - CARD_GAP_RPX * 5) / 6)
  if (count <= 5) return Math.max(108, Math.min(fit5, 168))
  if (count === 6) return Math.max(96, fit6)
  return Math.max(96, fit5)
}
export const SHEET_GAP_RPX = CARD_GAP_RPX
export const CARD_WIDTH_RPX = 120 // \u8FC7\u6E21\u4F7F\u7528,\u52A8\u6001\u8BA1\u7B97\u4F18\u5148\r

/** \u5C06 built_in \u503C\u4ECE \u201C\u4EFB\u4F55\u6765\u6E90\u201D \u540C\u6B65\u5230 \u5F53\u524D tab \u5BF9\u8C61(\u9632\u6B62\u5386\u53F2\u5B58\u50A8\u4E2D built_in \u4E0E\u5F53\u524D\u4EE3\u7801\u4E0D\u4E00\u81F4) */
export function syncBuiltIn(tabs) {
  const optMap = {}
  ALL_OPTIONS.forEach(function (o) { optMap[o.key] = o })
  return (tabs || []).map(function (t) {
    if (!t || !t.id) return t
    const opt = optMap[t.id]
    return Object.assign({}, t, { built_in: !!(opt && opt.built_in) })
  })
}
